import re
import time
import math

def parse_messages(payload,settings):
    if not isinstance(payload,dict) or payload.get('object')!='whatsapp_business_account':raise ValueError('Invalid object')
    result=[]
    for entry in payload.get('entry',[]):
        if not isinstance(entry,dict):continue
        if settings.meta_waba_id and str(entry.get('id'))!=settings.meta_waba_id:continue
        for change in entry.get('changes',[]):
            if not isinstance(change,dict) or change.get('field')!='messages':continue
            v=change.get('value') or {}
            if not isinstance(v,dict):continue
            if str((v.get('metadata') or {}).get('phone_number_id',''))!=settings.meta_phone_number_id:continue
            for m in v.get('messages',[]):
                if not isinstance(m,dict):continue
                sender=m.get('from','');mid=m.get('id','');kind=m.get('type','unknown')
                if not isinstance(sender,str) or not re.fullmatch(r'\d{7,15}',sender) or not isinstance(mid,str) or not mid:continue
                try:ts=float(m['timestamp'])
                except (KeyError,ValueError,TypeError):continue
                if not math.isfinite(ts) or ts<=0 or ts>time.time()+300:continue
                text=(m.get('text') or {}).get('body','') if kind=='text' else ''
                if not isinstance(text,str) or len(text)>4000:kind='unsupported';text=''
                result.append({'message_id':mid,'session_id':f'meta:{settings.meta_phone_number_id}:{sender}','sender':sender,'body':text,'inbound_at':ts,'kind':kind})
    return result
