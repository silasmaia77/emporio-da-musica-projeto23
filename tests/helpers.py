import json
import time
from types import SimpleNamespace

def message(content=None,calls=None):
    payload={'role':'assistant','content':content}
    if calls:payload['tool_calls']=[{'id':f'call_{i}','type':'function','function':{'name':name,'arguments':json.dumps(args)}} for i,(name,args) in enumerate(calls)]
    class Message:
        def __init__(self):
            self.content=content
            self.tool_calls=[SimpleNamespace(id=c['id'],function=SimpleNamespace(**c['function'])) for c in payload.get('tool_calls',[])]
        def model_dump(self,**kwargs):return payload
    return SimpleNamespace(choices=[SimpleNamespace(message=Message())])

class ScriptedClient:
    """LLM test double. It never claims to be a real generative model."""
    def __init__(self,responses):
        self.responses=list(responses);self.requests=[]
        self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
    def create(self,**kwargs):
        self.requests.append(kwargs)
        r=self.responses.pop(0)
        if isinstance(r,Exception):raise r
        return r

def payload(mid='wamid.test',text='Olá',sender='5567999990000',phone='phone-test',kind='text',timestamp=None):
    return {'object':'whatsapp_business_account','entry':[{'id':'waba-test','changes':[{'field':'messages','value':{'messaging_product':'whatsapp','metadata':{'phone_number_id':phone},'messages':[{'id':mid,'from':sender,'timestamp':str(int(time.time() if timestamp is None else timestamp)),'type':kind,'text':{'body':text}}]}}]}]}
