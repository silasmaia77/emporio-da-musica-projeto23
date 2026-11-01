import argparse
import uuid
from src.config import Settings
from src.agent.engine import Agent
from src.data.importer import import_data
from src.services.sessions import Sessions

def main():
    p=argparse.ArgumentParser();p.add_argument('--demo-customer',type=int);args=p.parse_args()
    s=Settings();import_data(s);agent=Agent(s);sid='cli:'+str(uuid.uuid4())
    if args.demo_customer:
        Sessions(s.database_path).bind_demo(sid,args.demo_customer);print('DEMONSTRAÇÃO: identidade fictícia selecionada pelo operador.')
    print('Empório da Música. Digite /sair para encerrar.')
    while True:
        text=input('Você: ')
        if text.strip()=='/sair':break
        print('Mel:',agent.chat(sid,text)['answer'])
if __name__=='__main__':main()
