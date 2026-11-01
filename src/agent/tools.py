import json
from pydantic import BaseModel, ConfigDict, Field
from src.data.database import connect
from src.data.repositories import StoreRepository
from src.policies.retriever import Policies
from src.services.pricing import quote
from src.services.sessions import Sessions

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')
class Search(Input):
    query:str=Field(default='',max_length=200)
    category:str=Field(default='',max_length=100)
    max_price_brl:float|None=Field(default=None,ge=0,le=10000000)
    available_only:bool=True
    limit:int=Field(default=5,ge=1,le=10)
class Product(Input):product_id:int=Field(gt=0)
class Promotions(Input):product_id:int|None=Field(default=None,gt=0)
class Payment(Product):
    payment:str=Field(default='credit',pattern='^(credit|pix|debit|boleto)$')
    installments:int=Field(default=1,ge=1,le=12)
class Order(Input):order_id:int=Field(gt=0)
class Policy(Input):query:str=Field(min_length=1,max_length=400)
class Support(Input):summary:str=Field(min_length=5,max_length=1000)

MODELS={'search_products':Search,'get_product_details':Product,'get_active_promotions':Promotions,'calculate_payment_options':Payment,'get_order_status':Order,'search_store_policies':Policy,'create_support_request':Support}
DESCRIPTIONS={'search_products':'Busca catálogo por nome, categoria e orçamento em reais. Não inclui dados de clientes.','get_product_details':'Consulta produto e disponibilidade atual no banco local.','get_active_promotions':'Lista promoções ativas no sistema.','calculate_payment_options':'Calcula preço e parcelas do produto com política de Pix e promoção.','get_order_status':'Consulta apenas pedido pertencente ao cliente autorizado da sessão; não recebe customer_id.','search_store_policies':'Recupera políticas, horários, contatos, garantia, devoluções, frete e formas de pagamento.','create_support_request':'Registra solicitação local, sem encaminhamento externo.'}

def definitions():
    return [{'type':'function','function':{'name':name,'description':DESCRIPTIONS[name],'parameters':model.model_json_schema()}} for name,model in MODELS.items()]

class Tools:
    def __init__(self,settings,session_id):
        self.settings=settings;self.session_id=session_id;self.repo=StoreRepository(settings.database_path)
    def call(self,name,args):
        if name not in MODELS:return {'status':'invalid_tool'}
        try:
            a=MODELS[name].model_validate(args).model_dump()
            if name=='search_products':return {'status':'ok','products':self.repo.search(**a)}
            if name=='get_product_details':
                p=self.repo.product(**a);return {'status':'ok' if p else 'not_found','product':p}
            if name=='get_active_promotions':return {'status':'ok','promotions':self.repo.promotions(**a)}
            if name=='calculate_payment_options':
                p=self.repo.product(a.pop('product_id'))
                if not p:return {'status':'not_found'}
                if p['pricing_status']!='ok':return {'status':'needs_confirmation'}
                return dict(quote(p['price_cents'],p['discount_percent'],**a),can_offer=p['can_offer'])
            if name=='get_order_status':return self.repo.order(a['order_id'],Sessions(self.settings.database_path).customer(self.session_id))
            if name=='search_store_policies':return {'status':'ok','sources':Policies(self.settings.policy_path).search(a['query'])}
            if name=='create_support_request':
                Sessions(self.settings.database_path).ensure(self.session_id)
                with connect(self.settings.database_path) as c:r=c.execute('INSERT INTO support(session_id,summary) VALUES (?,?)',(self.session_id,a['summary']))
                return {'status':'recorded_locally','ticket_id':r.lastrowid,'forwarded':False}
        except (ValueError,TypeError):return {'status':'invalid_arguments'}
