import re
import time
import httpx

class DeliveryError(Exception):pass
class UncertainDelivery(DeliveryError):pass
class RetryableDelivery(DeliveryError):pass
class WindowClosed(DeliveryError):pass

class MetaClient:
    def __init__(self,settings,http=None):
        self.settings=settings;self.http=http
    def _post(self,payload):
        s=self.settings
        if s.meta_dry_run:return {'dry_run':True,'payload_type':payload['type']}
        if not s.meta_access_token or not s.meta_phone_number_id or not re.fullmatch(r'v\d+\.\d+',s.meta_graph_api_version):raise DeliveryError('missing_meta_configuration')
        url=f'https://graph.facebook.com/{s.meta_graph_api_version}/{s.meta_phone_number_id}/messages'
        if self.http is None:self.http=httpx.Client(timeout=15)
        try:r=self.http.post(url,headers={'Authorization':'Bearer '+s.meta_access_token},json=payload)
        except httpx.RequestError as exc:raise UncertainDelivery('network_outcome_unknown') from exc
        if r.status_code==429:raise RetryableDelivery('rate_limited')
        if r.status_code>=500:raise UncertainDelivery('server_outcome_unknown')
        if r.status_code>=400:raise DeliveryError(f'meta_http_{r.status_code}')
        try:mid=r.json()['messages'][0]['id']
        except (ValueError,KeyError,IndexError,TypeError) as exc:raise UncertainDelivery('missing_message_id') from exc
        return {'message_id':mid}
    def send_text(self,to,text,last_inbound_at,now=None):
        if not re.fullmatch(r'\d{7,15}',to):raise DeliveryError('invalid_recipient')
        now=time.time() if now is None else now
        if not 0<=now-last_inbound_at<86400:raise WindowClosed('outside_customer_service_window')
        results=[]
        for start in range(0,len(text),4000):
            try:results.append(self._post({'messaging_product':'whatsapp','recipient_type':'individual','to':to,'type':'text','text':{'preview_url':False,'body':text[start:start+4000]}}))
            except DeliveryError as exc:
                if results:raise UncertainDelivery('partial_multi_message_delivery') from exc
                raise
        return results
    def send_template(self,to,name,language,approved=False):
        if not approved or not name or not re.fullmatch(r'\d{7,15}',to):raise DeliveryError('explicit_approved_template_required')
        return self._post({'messaging_product':'whatsapp','to':to,'type':'template','template':{'name':name,'language':{'code':language}}})
