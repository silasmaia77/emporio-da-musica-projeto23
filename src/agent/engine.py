import json
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from openai import OpenAI
from src.agent.prompts import SYSTEM
from src.agent.tools import Tools, definitions
from src.services.sessions import Sessions

log=logging.getLogger(__name__)

class Agent:
    def __init__(self,settings,client=None):
        self.settings=settings
        if client is None:
            settings.require_llm()
            kwargs={'api_key':settings.openai_api_key,'timeout':settings.request_timeout,'max_retries':1}
            if settings.openai_base_url:kwargs['base_url']=settings.openai_base_url
            client=OpenAI(**kwargs)
        self.client=client

    def chat(self,session_id,text):
        if not isinstance(text,str) or not text.strip() or len(text)>4000:raise ValueError('Mensagem deve conter de 1 a 4000 caracteres.')
        started=time.monotonic();sessions=Sessions(self.settings.database_path);sessions.ensure(session_id)
        history=sessions.history(session_id)
        system=SYSTEM.format(name=self.settings.assistant_name)+'\nData/hora local: '+datetime.now(ZoneInfo('America/Campo_Grande')).isoformat()
        messages=[{'role':'system','content':system},*history,{'role':'user','content':text}]
        tools=Tools(self.settings,session_id);trace=[];sources=[];calls=0
        try:
            for _ in range(self.settings.max_tool_calls+1):
                response=self.client.chat.completions.create(model=self.settings.openai_model,messages=messages,tools=definitions(),parallel_tool_calls=False)
                m=response.choices[0].message
                tool_calls=m.tool_calls or []
                if not tool_calls:
                    answer=m.content or 'Pode reformular sua pergunta para eu te ajudar?'
                    sessions.save(session_id,text,answer)
                    return {'answer':answer,'trace':trace,'sources':sources,'latency_seconds':round(time.monotonic()-started,3),'mode':'llm'}
                messages.append(m.model_dump(exclude_none=True))
                for call in tool_calls:
                    calls+=1
                    if calls>self.settings.max_tool_calls:raise RuntimeError('tool_limit')
                    try:args=json.loads(call.function.arguments)
                    except (ValueError,TypeError):args={}
                    result=tools.call(call.function.name,args)
                    # No raw personal arguments/results in logs or technical panel.
                    trace.append({'tool':call.function.name,'status':result.get('status')})
                    sources.extend([{'page':s['page'],'section':s['section']} for s in result.get('sources',[])])
                    messages.append({'role':'tool','tool_call_id':call.id,'content':json.dumps(result,ensure_ascii=False)})
            raise RuntimeError('tool_limit')
        except Exception as exc:
            log.warning('agent_failure type=%s',type(exc).__name__)
            return {'answer':'Estou com uma dificuldade para consultar o sistema agora. Pode tentar novamente em instantes?','trace':trace,'sources':sources,'latency_seconds':round(time.monotonic()-started,3),'mode':'error'}
