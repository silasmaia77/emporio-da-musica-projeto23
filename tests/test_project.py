import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import httpx
import pytest
from fastapi.testclient import TestClient
from src.config import Settings
from src.data.importer import import_data,read_source
from src.data.database import connect
from src.data.repositories import StoreRepository
from src.services.pricing import quote,local_shipping
from src.services.sessions import Sessions
from src.services.message_queue import Queue
from src.policies.retriever import Policies,load_chunks
from src.agent.tools import Tools
from src.agent.engine import Agent
from src.channels.meta_security import signature,valid_signature
from src.channels.meta_webhook import parse_messages
from src.channels.meta_client import MetaClient,WindowClosed,DeliveryError,UncertainDelivery,RetryableDelivery
from src.api import create_app
from src.worker import process_once
from tests.helpers import ScriptedClient,message,payload

def test_01_environment():
    import sys
    assert sys.version_info>=(3,10)

def test_02_configuration():
    with pytest.raises(ValueError):Settings(openai_api_key='',openai_model='').require_llm()
    assert Settings(meta_dry_run=True).meta_dry_run

def test_03_sources(settings):
    assert settings.source_path.is_file() and settings.policy_path.is_file()
    assert len(read_source(settings.source_path))==10

def test_04_import_all(settings):
    counts=import_data(settings)
    assert counts['produtos']==65 and counts['clientes']==50 and counts['pedidos']==20
    with connect(settings.database_path) as c:
        assert c.execute('SELECT count(DISTINCT sheet) FROM source_aux').fetchone()[0]==10

def test_05_integrity(settings):
    with connect(settings.database_path) as c:
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        with pytest.raises(sqlite3.IntegrityError):c.execute('INSERT INTO order_items VALUES (999,999,999,1)')

def test_06_reimport(settings):
    sess=Sessions(settings.database_path);sess.save('preserved','Oi','Olá')
    before=import_data(settings);after=import_data(settings)
    assert before==after and len(sess.history('preserved'))==2
    with connect(settings.database_path) as c:assert c.execute('SELECT count(*) FROM products').fetchone()[0]==65

@pytest.mark.parametrize('query',['yamaha','YAMAHA','C40','violão','violao'])
def test_07_search(settings,query):
    rows=StoreRepository(settings.database_path).search(query,max_price_brl=1000)
    assert rows and all(p['price_cents']<=100000 and p['can_offer'] for p in rows)

def test_07_no_results_and_injection(settings):
    r=StoreRepository(settings.database_path)
    assert r.search("' OR 1=1 --")==[]
    assert r.search('inexistente')==[]
    with pytest.raises(ValueError):r.search(max_price_brl=-1)

def test_08_stock(settings):
    repo=StoreRepository(settings.database_path)
    assert repo.product(96)['can_offer']==0
    assert repo.product(113)['status']=='discontinued' and repo.product(113)['can_offer']==0
    assert repo.product(130)['status']=='coming_soon' and repo.product(130)['can_offer']==0
    assert repo.product(135)['specs']=={}
    # A source update is visible immediately through the derived SQL view.
    with connect(settings.database_path) as c:c.execute('UPDATE products SET stock_quantity=0 WHERE product_id=81')
    assert repo.product(81)['can_offer']==0

def test_09_promotions(settings):
    repo=StoreRepository(settings.database_path)
    assert len(repo.promotions())==4
    p=repo.product(127)
    assert p['discount_percent']==10
    assert p['pix_quote']['total_cents']==32310
    assert p['credit_quote']['total_cents']==32310
    assert repo.product(81)['pix_quote']['total_cents']==56991
    assert repo.product(93)['discount_percent']==0

@pytest.mark.parametrize('parts,total',[(1,59990),(3,59990),(6,60000),(12,120000)])
def test_10_money(parts,total):
    q=quote(total,0,'credit',parts)
    assert q['status']=='ok' and sum(q['installment_cents'])==total
    assert max(q['installment_cents'])-min(q['installment_cents'])<=1

def test_10_limits():
    assert quote(4999,0,'credit',3)['status']=='needs_confirmation'
    assert quote(30000,0,'credit',6)['status']=='not_allowed'
    assert local_shipping(50000)['status']=='needs_confirmation'
    assert local_shipping(50001)['shipping_cents']==0
    assert local_shipping(49999)['shipping_cents']==3500
    with pytest.raises(ValueError):quote(10000,0,'pix',3)

@pytest.mark.parametrize('query,expected',[('horário funcionamento','09:00'),('Pix pagamento','5%'),('arrependimento devolução','7'),('endereço rua','3200')])
def test_11_policies(settings,query,expected):
    rows=Policies(settings.policy_path).search(query,6)
    assert rows and any(expected in r['text'] for r in rows)
    assert all(r['page']>=1 and r['section'] for r in rows)

def test_12_order_items(settings):
    r=StoreRepository(settings.database_path).order(15,18)
    assert r['status']=='ok' and len(r['items'])==2
    assert r['order']['total_cents']==834800
    assert r['actual_delivery_date'] is None

def test_13_authorization(settings):
    t=Tools(settings,'anonymous')
    assert t.call('get_order_status',{'order_id':1})['status']=='unauthorized'
    Sessions(settings.database_path).bind_demo('anonymous',7)
    assert t.call('get_order_status',{'order_id':1})['status']=='not_found'
    assert t.call('get_order_status',{'order_id':1,'customer_id':3})['status']=='invalid_arguments'
    Sessions(settings.database_path).bind_verified_sender('meta','5567999990000')
    assert Sessions(settings.database_path).customer('meta') is None

def test_14_sessions(settings):
    s=Sessions(settings.database_path);s.save('a','Yamaha','C40');s.save('b','Olá','Oi')
    assert s.history('a')[0]['content']=='Yamaha' and 'Yamaha' not in str(s.history('b'))
    s.bind_demo('a',3);assert not s.history('a')

def test_14_verified_binding_change(settings):
    s=Sessions(settings.database_path)
    with connect(settings.database_path) as c:c.execute('INSERT INTO identity_bindings(sender,customer_id) VALUES (?,?)',('sender',3))
    s.bind_verified_sender('whatsapp','sender');s.save('whatsapp','Pedido','Resposta privada')
    with connect(settings.database_path) as c:c.execute('UPDATE identity_bindings SET customer_id=7 WHERE sender=?',('sender',))
    s.bind_verified_sender('whatsapp','sender')
    assert s.customer('whatsapp')==7 and not s.history('whatsapp')

def test_09_multiple_promotions(settings):
    with connect(settings.database_path) as c:c.execute("INSERT INTO promotions VALUES (999,127,20,'Test duplicate',1)")
    assert Tools(settings,'x').call('calculate_payment_options',{'product_id':127})['status']=='needs_confirmation'

def test_21_unsupported_and_window(settings):
    q=Queue(settings.database_path)
    q.enqueue_many(parse_messages(payload(kind='image'),settings))
    agent=Agent(settings,ScriptedClient([]))
    assert process_once(settings,agent,MetaClient(settings))
    with connect(settings.database_path) as c:
        r=c.execute('SELECT status,reply FROM queue').fetchone()
        assert r['status']=='simulated' and 'texto' in r['reply']
    q.enqueue_many(parse_messages(payload('old',timestamp=time.time()-90000),settings))
    agent=Agent(settings,ScriptedClient([message('Oi!')]))
    process_once(settings,agent,MetaClient(settings))
    with connect(settings.database_path) as c:assert c.execute("SELECT status FROM queue WHERE message_id='old'").fetchone()[0]=='blocked'

def test_15_get_webhook(settings):
    with TestClient(create_app(settings)) as c:
        r=c.get('/webhook',params={'hub.mode':'subscribe','hub.verify_token':'test-verify','hub.challenge':'123'})
        assert r.status_code==200 and r.text=='123'
        assert c.get('/webhook',params={'hub.mode':'subscribe','hub.verify_token':'bad'}).status_code==403

def signed_post(c,s,p):
    raw=json.dumps(p).encode()
    return c.post('/webhook',content=raw,headers={'x-hub-signature-256':signature(s.meta_app_secret,raw),'Content-Type':'application/json'})

def test_16_signature(settings):
    raw=b'{"test":1}'
    assert valid_signature('a',raw,signature('a',raw))
    assert not valid_signature('b',raw,signature('a',raw))
    with TestClient(create_app(settings)) as c:
        assert c.post('/webhook',json=payload()).status_code==403
        assert signed_post(c,settings,payload()).status_code==200

def test_17_payloads(settings):
    with TestClient(create_app(settings)) as c:
        assert signed_post(c,settings,payload()).json()['accepted']==1
        assert signed_post(c,settings,payload()).json()['accepted']==0
        p=payload('status');v=p['entry'][0]['changes'][0]['value'];v.pop('messages');v['statuses']=[{'id':'out','status':'delivered'}]
        assert signed_post(c,settings,p).json()['accepted']==0
        assert signed_post(c,settings,{'object':'bad'}).status_code==400
        assert signed_post(c,settings,payload('foreign',phone='other')).json()['accepted']==0
    p=payload('multi');p['entry'].append(payload('second')['entry'][0]);assert len(parse_messages(p,settings))==2
    assert parse_messages(payload('image',kind='image'),settings)[0]['kind']=='image'

def test_18_queue(settings):
    q=Queue(settings.database_path,lease_seconds=1);msgs=parse_messages(payload('one'),settings)+parse_messages(payload('two'),settings)
    q.enqueue_many(msgs)
    with ThreadPoolExecutor(2) as pool:claims=list(pool.map(lambda _:q.claim(),range(2)))
    assert sum(j is not None for j in claims)==1
    job=next(j for j in claims if j);q.update(job['id'],'sent');assert q.claim()['message_id']=='two'

def test_18_recovery(settings):
    q=Queue(settings.database_path,lease_seconds=1);q.enqueue_many(parse_messages(payload(),settings));j=q.claim(now=10)
    assert q.claim(now=12)['message_id']==j['message_id']
    with connect(settings.database_path) as c:c.execute("UPDATE queue SET status='sending',lease_until=1")
    assert q.claim(now=20) is None
    with connect(settings.database_path) as c:assert c.execute('SELECT status FROM queue').fetchone()[0]=='uncertain'

def test_19_meta_http(settings):
    settings.meta_dry_run=False;settings.meta_access_token='test';settings.meta_graph_api_version='v99.0'
    sent=[]
    def handler(req):sent.append(json.loads(req.content));return httpx.Response(200,json={'messages':[{'id':'out.test'}]})
    m=MetaClient(settings,httpx.Client(transport=httpx.MockTransport(handler)))
    assert len(m.send_text('5567999990000','a'*5000,time.time()))==2
    assert len(sent[0]['text']['body'])==4000 and sent[0]['to']=='5567999990000'
    # v99.0 is only a mock URL, never a production default.

@pytest.mark.parametrize('code,error',[(400,DeliveryError),(429,RetryableDelivery),(500,UncertainDelivery)])
def test_19_http_errors(settings,code,error):
    settings.meta_dry_run=False;settings.meta_access_token='test';settings.meta_graph_api_version='v99.0'
    m=MetaClient(settings,httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(code,json={}))))
    with pytest.raises(error):m.send_text('5567999990000','Oi',time.time())

def test_20_window(settings):
    m=MetaClient(settings)
    with pytest.raises(WindowClosed):m.send_text('5567999990000','Oi',1,now=86401)
    with pytest.raises(DeliveryError):m.send_template('5567999990000','hello','pt_BR')
    assert m.send_template('5567999990000','configured','pt_BR',approved=True)['dry_run']

def test_21_end_to_end(settings):
    client=ScriptedClient([message(calls=[('get_product_details',{'product_id':81})]),message('O Yamaha C40 está disponível por R$ 599,90.')])
    agent=Agent(settings,client)
    with TestClient(create_app(settings)) as api:assert signed_post(api,settings,payload(text='Preço do Yamaha C40?')).status_code==200
    assert process_once(settings,agent,MetaClient(settings))
    with connect(settings.database_path) as c:
        row=c.execute('SELECT * FROM queue').fetchone();assert row['status']=='simulated'
        assert '599,90' in row['reply']
    assert client.requests[1]['messages'][-1]['role']=='tool'

def test_22_context_tool_loop(settings):
    cl=ScriptedClient([message('Oi! Sou a Mel.'),message(calls=[('calculate_payment_options',{'product_id':81,'payment':'pix'})]),message('No Pix fica R$ 569,91.')])
    a=Agent(settings,cl);a.chat('ctx','Yamaha C40');result=a.chat('ctx','E no Pix?')
    assert result['trace'][0]['tool']=='calculate_payment_options'
    assert any(m.get('content')=='Yamaha C40' for m in cl.requests[-1]['messages'])

def test_23_provider_failure(settings):
    result=Agent(settings,ScriptedClient([TimeoutError()])).chat('s','Olá')
    assert result['mode']=='error' and 'dificuldade' in result['answer']

def test_23_tool_guardrails(settings):
    t=Tools(settings,'x')
    assert t.call('get_order_status',{'order_id':1,'customer_id':3})['status']=='invalid_arguments'
    assert t.call('delete_database',{})['status']=='invalid_tool'
    assert t.call('calculate_payment_options',{'product_id':81,'payment':'credit','installments':0})['status']=='invalid_arguments'
    assert t.call('create_support_request',{'summary':'Preciso de ajuda com minha compra'})['forwarded'] is False

def test_23_tool_limit(settings):
    settings.max_tool_calls=2
    result=Agent(settings,ScriptedClient([message(calls=[('search_products',{})])]*3)).chat('loop','Oi')
    assert result['mode']=='error'

def test_23_missing_database(settings):
    settings.database_path=settings.database_path.parent/'absent.sqlite'
    with pytest.raises(sqlite3.OperationalError):StoreRepository(settings.database_path).search()

def test_23_support_and_invalid_args(settings):
    t=Tools(settings,'support');r=t.call('create_support_request',{'summary':'Gostaria de registrar uma reclamação.'})
    assert r['status']=='recorded_locally' and r['ticket_id']>0
    assert t.call('search_products',{'max_price_brl':-1})['status']=='invalid_arguments'
