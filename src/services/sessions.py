import time
from src.data.database import connect

class Sessions:
    def __init__(self,path):self.path=path
    def ensure(self,session_id):
        with connect(self.path) as c:c.execute('INSERT OR IGNORE INTO sessions(session_id) VALUES (?)',(session_id,))
    def bind_demo(self,session_id,customer_id):
        self.ensure(session_id)
        with connect(self.path) as c:
            old=c.execute('SELECT customer_id FROM sessions WHERE session_id=?',(session_id,)).fetchone()[0]
            if old!=customer_id:c.execute('DELETE FROM turns WHERE session_id=?',(session_id,))
            c.execute("UPDATE sessions SET customer_id=?,auth_source='demo' WHERE session_id=?",(customer_id,session_id))
    def bind_verified_sender(self,session_id,sender):
        self.ensure(session_id)
        with connect(self.path) as c:
            r=c.execute('SELECT customer_id FROM identity_bindings WHERE sender=?',(sender,)).fetchone()
            old=c.execute('SELECT customer_id FROM sessions WHERE session_id=?',(session_id,)).fetchone()[0]
            if old!=(r[0] if r else None):c.execute('DELETE FROM turns WHERE session_id=?',(session_id,))
            # Only operator-established verification is accepted, never phone-text matching.
            c.execute("UPDATE sessions SET customer_id=?,auth_source=? WHERE session_id=?",(r[0] if r else None,'verified_binding' if r else 'anonymous',session_id))
    def customer(self,session_id):
        with connect(self.path) as c:r=c.execute('SELECT customer_id FROM sessions WHERE session_id=?',(session_id,)).fetchone()
        return r[0] if r else None
    def history(self,session_id):
        with connect(self.path) as c:rows=c.execute('SELECT role,content FROM (SELECT id,role,content FROM turns WHERE session_id=? ORDER BY id DESC LIMIT 24) ORDER BY id',(session_id,)).fetchall()
        return [dict(r) for r in rows]
    def save(self,session_id,user,answer):
        self.ensure(session_id)
        with connect(self.path) as c:c.executemany('INSERT INTO turns(session_id,role,content,created_at) VALUES (?,?,?,?)',[(session_id,'user',user,time.time()),(session_id,'assistant',answer,time.time())])
