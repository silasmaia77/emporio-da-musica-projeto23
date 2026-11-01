from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.config import Settings
from src.data.importer import import_data
from src.data.repositories import StoreRepository
from src.agent.engine import Agent
from src.services.sessions import Sessions
from tests.helpers import ScriptedClient,message

def brl(cents):return ('R$ '+f'{cents/100:,.2f}').replace(',','X').replace('.',',').replace('X','.')
def main():
    with tempfile.TemporaryDirectory() as tmp:
        s=Settings(database_path=Path(tmp)/'examples.sqlite',openai_model='SCRIPTED-MOCK');import_data(s)
        catalog=StoreRepository(s.database_path).search('violão',max_price_brl=1000,limit=3)
        options='\n'.join(f"- {p['name']}: {brl(p['price_cents'])}." for p in catalog)
        cases=[
          ('01_catalog',None,[('Quais violões disponíveis até R$ 1000?','search_products',{'query':'violão','max_price_brl':1000,'limit':3},'Oi! Sou a Mel, assistente virtual da Empório da Música 🎵 Separei estas opções disponíveis:\n'+options+'\nVocê prefere cordas de nylon ou aço?')]),
          ('02_price_pix',None,[('Quanto custa o Yamaha C40?','get_product_details',{'product_id':81},'O Yamaha C40 Nylon Natural está disponível por R$ 599,90.'),('E no Pix?','calculate_payment_options',{'product_id':81,'payment':'pix'},'No Pix, ele fica por R$ 569,91, com 5% de desconto sobre R$ 599,90.')]),
          ('03_store_policies',None,[('Qual o endereço e o horário?','search_store_policies',{'query':'endereço horário funcionamento'},'Ficamos na Rua 14 de Maio, 3200, Centro, Campo Grande/MS. Atendemos de segunda a sexta, das 9h às 18h, e sábado, das 9h às 13h. Domingos e feriados, fechado.')]),
          ('04_order',18,[('Como está meu pedido 15?','get_order_status',{'order_id':15},'Seu pedido 15 está pendente. Ele inclui um Yamaha C70 e um Taylor 214ce. O total registrado é R$ 8.348,00. Ainda não há código de rastreamento informado.')]),
          ('05_returns_scope',None,[('Me arrependi da compra. Posso devolver?','search_store_policies',{'query':'arrependimento compras online devolução'},'Se foi uma compra online, o manual prevê solicitar a devolução em até 7 dias corridos após o recebimento. Você comprou online e em que dia recebeu o instrumento?'),('Vocês vendem cabos também?','search_store_policies',{'query':'acessórios cabos escopo'},'A gente trabalha somente com instrumentos musicais e não vende cabos. Posso te ajudar a escolher um instrumento?')])]
        for name,customer,turns in cases:
            responses=[]
            for _,tool,args,answer in turns:responses.extend([message(calls=[(tool,args)]),message(answer)])
            agent=Agent(s,ScriptedClient(responses))
            if customer:Sessions(s.database_path).bind_demo(name,customer)
            text=f'# {name}\n\nMode: scripted model simulation, local channel. Real tool/database execution; no live LLM or WhatsApp.\n\n'
            for user,_,_,_ in turns:
                r=agent.chat(name,user);assert r['mode']=='llm'
                text+=f"**Customer:** {user}\n\n**Mel:** {r['answer']}\n\nTools: {r['trace']}\n\n"
            (ROOT/'examples'/f'{name}.md').write_text(text,encoding='utf8')
    print('Five simulated transcripts generated with actual tool execution.')
if __name__=='__main__':main()
