import json
import time
from src.data.database import connect

class Queue:
    def __init__(self,path,lease_seconds=600,max_attempts=3):self.path=path;self.lease_seconds=lease_seconds;self.max_attempts=max_attempts
    def enqueue_many(self,messages):
        count=0
        with connect(self.path) as c:
            for m in messages:
                r=c.execute('INSERT OR IGNORE INTO queue(message_id,session_id,sender,body,inbound_at,kind) VALUES (?,?,?,?,?,?)',tuple(m[k] for k in ['message_id','session_id','sender','body','inbound_at','kind']))
                count+=r.rowcount
        return count
    def claim(self,now=None):
        now=time.time() if now is None else now
        with connect(self.path) as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute("UPDATE queue SET status=CASE WHEN attempts>=? THEN 'failed' ELSE 'pending' END,lease_until=NULL,error='lease_expired' WHERE status='processing' AND lease_until<?",(self.max_attempts,now))
            # Sending is never blindly retried after a crash: outcome may be uncertain.
            c.execute("UPDATE queue SET status='uncertain',error='delivery_outcome_unknown' WHERE status='sending' AND lease_until<?",(now,))
            r=c.execute("""SELECT q.* FROM queue q WHERE q.status='pending' AND q.available_at<=? AND q.attempts<?
            AND NOT EXISTS(SELECT 1 FROM queue p WHERE p.session_id=q.session_id AND p.id<q.id AND p.status IN ('pending','processing','sending','uncertain','failed'))
            ORDER BY q.id LIMIT 1""",(now,self.max_attempts)).fetchone()
            if r is None:return None
            c.execute("UPDATE queue SET status='processing',attempts=attempts+1,lease_until=? WHERE id=?",(now+self.lease_seconds,r['id']))
            d=dict(r);d['attempts']+=1;return d
    def update(self,id,status,reply=None,outbound=None,error=None):
        with connect(self.path) as c:c.execute('UPDATE queue SET status=?,reply=COALESCE(?,reply),outbound_json=COALESCE(?,outbound_json),error=?,lease_until=? WHERE id=?',(status,reply,json.dumps(outbound) if outbound is not None else None,error,time.time()+self.lease_seconds if status in {'processing','sending'} else None,id))
    def retry(self,job,error):
        status='failed' if job['attempts']>=self.max_attempts else 'pending'
        with connect(self.path) as c:c.execute('UPDATE queue SET status=?,error=?,available_at=?,lease_until=NULL WHERE id=?',(status,error,time.time()+min(60,2**job['attempts']),job['id']))
