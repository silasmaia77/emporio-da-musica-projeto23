import logging
import time
from src.config import Settings
from src.data.database import initialize
from src.agent.engine import Agent
from src.channels.meta_client import MetaClient,UncertainDelivery,RetryableDelivery,WindowClosed,DeliveryError
from src.services.message_queue import Queue
from src.services.sessions import Sessions

def process_once(settings,agent,client):
    queue=Queue(settings.database_path,settings.lease_seconds,settings.max_attempts)
    job=queue.claim()
    if job is None:return False
    try:
        Sessions(settings.database_path).bind_verified_sender(job['session_id'],job['sender'])
        answer=job['reply']
        if not answer:
            if job['kind']!='text':answer='Por enquanto consigo ler mensagens de texto. Pode escrever como posso te ajudar?'
            else:
                result=agent.chat(job['session_id'],job['body'])
                if result['mode']=='error':raise RuntimeError('agent_unavailable')
                answer=result['answer']
            queue.update(job['id'],'processing',reply=answer)
        queue.update(job['id'],'sending')
        result=client.send_text(job['sender'],answer,job['inbound_at'])
        queue.update(job['id'],'simulated' if settings.meta_dry_run else 'sent',outbound=result)
    except WindowClosed:queue.update(job['id'],'blocked',error='window_closed_no_approved_template_configured')
    except UncertainDelivery:queue.update(job['id'],'uncertain',error='delivery_outcome_unknown_manual_review_required')
    except RetryableDelivery:queue.retry(job,'rate_limited')
    except DeliveryError:queue.update(job['id'],'failed',error='delivery_failed_check_configuration')
    except Exception as exc:
        logging.getLogger(__name__).warning('job_failure id=%s type=%s',job['id'],type(exc).__name__)
        queue.retry(job,'processing_failed')
    return True

def main():
    s=Settings();initialize(s.database_path);agent=Agent(s);client=MetaClient(s)
    while True:
        if not process_once(s,agent,client):time.sleep(1)

if __name__=='__main__':main()
