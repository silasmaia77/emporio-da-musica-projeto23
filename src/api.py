import hmac
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from src.config import Settings
from src.data.database import initialize
from src.channels.meta_security import valid_signature
from src.channels.meta_webhook import parse_messages
from src.services.message_queue import Queue

def create_app(settings=None):
    s=settings or Settings()
    @asynccontextmanager
    async def lifespan(app):
        initialize(s.database_path)
        yield
    app=FastAPI(title='Empório da Música - Meta webhook',lifespan=lifespan)
    @app.get('/health')
    def health():return {'status':'ok','meta_dry_run':s.meta_dry_run}
    @app.get('/webhook',response_class=PlainTextResponse)
    def verify(request:Request):
        q=request.query_params
        if not s.meta_verify_token:raise HTTPException(503,'Webhook not configured')
        if q.get('hub.mode')!='subscribe' or not hmac.compare_digest(q.get('hub.verify_token',''),s.meta_verify_token):raise HTTPException(403,'Verification failed')
        challenge=q.get('hub.challenge')
        if not challenge:raise HTTPException(400,'Missing challenge')
        return challenge
    @app.post('/webhook')
    async def receive(request:Request):
        raw=await request.body()
        if len(raw)>1024*1024:raise HTTPException(413,'Payload too large')
        if not s.meta_app_secret or not s.meta_phone_number_id:raise HTTPException(503,'Webhook not configured')
        if not valid_signature(s.meta_app_secret,raw,request.headers.get('x-hub-signature-256')):raise HTTPException(403,'Invalid signature')
        try:messages=parse_messages(json.loads(raw),s)
        except (ValueError,TypeError,AttributeError):raise HTTPException(400,'Invalid payload')
        # Durable insertion before acknowledgement. No LLM or outbound HTTP here.
        inserted=Queue(s.database_path).enqueue_many(messages)
        return {'accepted':inserted}
    return app

app=create_app()
