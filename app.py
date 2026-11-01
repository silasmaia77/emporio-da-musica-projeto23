import uuid
import streamlit as st
from src.config import Settings
from src.data.importer import import_data
from src.data.database import connect
from src.agent.engine import Agent
from src.services.sessions import Sessions

st.set_page_config(page_title='Empório da Música | Mel',page_icon='🎵',layout='centered')
s=Settings()
@st.cache_resource
def bootstrap(path):
    import_data(s)
    return True
bootstrap(str(s.database_path))
st.title('🎵 Empório da Música')
st.caption('Projeto 23 • Sua música começa aqui. • Assistente virtual Mel')
st.info('Demonstração local com dados fictícios. Este chat não envia mensagens ao WhatsApp.')
if 'session_id' not in st.session_state:st.session_state.session_id='ui:'+str(uuid.uuid4())
sid=st.session_state.session_id
with st.sidebar:
    st.header('Demonstração')
    with connect(s.database_path) as c:customers=c.execute('SELECT customer_id,name FROM customers ORDER BY customer_id').fetchall()
    options={0:'Visitante (sem acesso a pedidos)',**{r['customer_id']:f"Cliente fictício {r['customer_id']} — {r['name']}" for r in customers}}
    selected=st.selectbox('Identidade simulada do cliente',list(options),format_func=options.get)
    st.caption('Seleção exclusiva de teste; não é autenticação de produção. Execute a UI somente em ambiente local.')
    Sessions(s.database_path).bind_demo(sid,selected or None)
    if st.button('Nova conversa'):
        st.session_state.session_id='ui:'+str(uuid.uuid4());st.rerun()
    st.caption('Meta: simulada' if s.meta_dry_run else 'Meta: envio real habilitado no worker')
for turn in Sessions(s.database_path).history(sid):
    with st.chat_message(turn['role']):st.write(turn['content'])
if not s.openai_api_key or not s.openai_model:
    st.warning('Configure OPENAI_API_KEY e OPENAI_MODEL no arquivo .env para conversar com o LLM.')
else:
    if text:=st.chat_input('Pergunte sobre instrumentos, pedidos ou políticas',max_chars=4000):
        with st.chat_message('user'):st.write(text)
        with st.chat_message('assistant'):
            with st.spinner('Consultando…'):result=Agent(s).chat(sid,text)
            st.write(result['answer'])
            with st.expander('Fontes e diagnóstico técnico'):
                st.json({'ferramentas':result['trace'],'fontes':result['sources'],'segundos':result['latency_seconds'],'modo':result['mode']})
