# %% BLOCO 01 — Ambiente, versões e caminhos
"""Validação em Python. Execute células # %% ou rode como script a partir do projeto.
Objetivo: validar módulos reais sem enviar WhatsApp por padrão.
Resultado esperado: blocos determinísticos PASS; integrações não habilitadas SKIPPED.
"""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent if '__file__' in globals() else Path.cwd()
ROOT=next((p for p in [HERE,HERE.parent,Path.cwd(),Path.cwd().parent] if (p/'src/config.py').exists()),None)
assert ROOT is not None,'Abra o notebook na pasta do projeto.'
sys.path.insert(0,str(ROOT))
assert sys.version_info>=(3,12)
RESULTS=[]
print('Python:',sys.version.split()[0])
for name in ['openai','fastapi','httpx','streamlit','openpyxl','pypdf','pytest']:
    print(name,importlib.metadata.version(name))

def run_block(number,title,selector):
    """Run actual pytest tests in a separate process and fail visibly."""
    result=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_project.py','-k',selector],cwd=ROOT,capture_output=True,text=True)
    print(result.stdout)
    if result.stderr:print(result.stderr[-1500:])
    status='PASS' if result.returncode==0 else 'FAIL'
    RESULTS.append({'block':number,'title':title,'status':status})
    assert result.returncode==0,f'BLOCO {number}: falhou; veja o diagnóstico acima.'
    print(f'BLOCO {number:02d} — {status}: {title}')

def skipped(number,title,reason):
    RESULTS.append({'block':number,'title':title,'status':'SKIPPED','reason':reason})
    print(f'BLOCO {number:02d} — NÃO EXECUTADO: {reason}')

run_block(1,'Ambiente','test_01_')

# %% BLOCO 02 — Configuração sem revelar segredos
# Esperado: validação de campos obrigatórios e padrão seguro; nenhuma chave impressa.
run_block(2,'Configuração','test_02_')

# %% BLOCO 03 — Presença e leitura dos arquivos
# Esperado: fontes existentes e dez abas identificadas.
run_block(3,'Fontes','test_03_')

# %% BLOCO 04 — Importação de todas as abas
# Esperado: seis tabelas operacionais e dez abas preservadas como origem.
run_block(4,'Importação','test_04_')

# %% BLOCO 05 — Contagens, chaves e relações
# Esperado: integrity_check=ok; referências inválidas rejeitadas.
run_block(5,'Integridade','test_05_')

# %% BLOCO 06 — Reimportação sem duplicação
# Esperado: contagens preservadas e histórico não apagado.
run_block(6,'Reimportação','test_06_')

# %% BLOCO 07 — Busca por nome, categoria e orçamento
# Esperado: consultas reais com normalização, ausência de resultados e SQL parametrizado.
run_block(7,'Busca','test_07_')

# %% BLOCO 08 — Estoque, descontinuados e lançamentos
# Esperado: indisponíveis não ofertados e alterações refletidas na view.
run_block(8,'Disponibilidade','test_08_')

# %% BLOCO 09 — Promoções e Pix sem cumulatividade
# Esperado: quatro promoções ativas e cálculos sem desconto duplicado.
run_block(9,'Promoções','test_09_')

# %% BLOCO 10 — Parcelamento e arredondamento
# Esperado: parcelas somam o total exato e limites ambíguos pedem confirmação.
run_block(10,'Dinheiro e limites','test_10_')

# %% BLOCO 11 — Recuperação das políticas com fontes
# Esperado: trechos relevantes com página física e seção do documento.
run_block(11,'Políticas','test_11_')

# %% BLOCO 12 — Pedidos com múltiplos itens
# Esperado: pedido 15 com dois itens, total histórico preservado.
run_block(12,'Pedidos','test_12_')

# %% BLOCO 13 — Autorização e acesso cruzado
# Esperado: visitante sem pedidos; ID de outro cliente não pode ser injetado.
run_block(13,'Autorização','test_13_')

# %% BLOCO 14 — Memória e isolamento de sessões
# Esperado: histórico de A não aparece em B; troca de identidade limpa contexto.
run_block(14,'Sessões','test_14_')

# %% BLOCO 15 — Verificação GET do webhook
# Esperado: desafio correto aceito; token incorreto rejeitado.
run_block(15,'Handshake Meta','test_15_')

# %% BLOCO 16 — Assinatura POST válida e inválida
# Esperado: HMAC real validado sobre bytes originais; requisição sem assinatura rejeitada.
run_block(16,'Assinatura Meta','test_16_')

# %% BLOCO 17 — Payloads, status e deduplicação
# Esperado: repetidos ignorados, eventos de status não geram respostas, múltiplas entradas lidas.
run_block(17,'Eventos Meta','test_17_')

# %% BLOCO 18 — Fila, worker e recuperação
# Esperado: exclusão por conversa e envio incerto separado de trabalho recuperável.
run_block(18,'Fila persistente','test_18_')

# %% BLOCO 19 — Cliente Meta com HTTP simulado
# Esperado: endpoint/payload, divisão de texto, rate limit e erros testados sem rede.
run_block(19,'HTTP Meta simulado','test_19_')

# %% BLOCO 20 — Janela de atendimento e templates
# Esperado: texto fora de 24h bloqueado; template exige confirmação de aprovação.
run_block(20,'Janela e templates','test_20_')

# %% BLOCO 21 — Fluxo completo simulado WhatsApp
# Esperado: POST assinado -> fila -> agente -> consulta -> saída simulada persistida.
run_block(21,'Fluxo integrado simulado','test_21_')

# %% BLOCO 22 — Contexto e LLM real opcional
# A parte determinística testa a passagem de contexto. A parte real exige opt-in.
run_block(22,'Contexto do agente com modelo simulado','test_22_')
if os.getenv('RUN_LIVE_LLM','false').lower()=='true':
    from src.config import Settings
    from src.data.importer import import_data
    from src.agent.engine import Agent
    from src.services.sessions import Sessions
    live=Settings();live.require_llm()
    with tempfile.TemporaryDirectory() as directory:
        live.database_path=Path(directory)/'live_llm.sqlite';import_data(live)
        agent=Agent(live)
        scenarios=[('catalog','Quais violões disponíveis até R$ 1000?','search_products'),('price','Quanto custa o Yamaha C40?','get_product_details'),('policy','Qual o horário de funcionamento?','search_store_policies')]
        for sid,question,expected_tool in scenarios:
            result=agent.chat(sid,question)
            assert result['mode']=='llm',result
            assert expected_tool in [t['tool'] for t in result['trace']],result
            print(question,'\n',result['answer'],'\nFerramentas:',result['trace'])
        result=agent.chat('price','E no Pix?')
        assert result['mode']=='llm' and any(t['tool']=='calculate_payment_options' for t in result['trace'])
        print('Continuação:',result['answer'])
        Sessions(live.database_path).bind_demo('private',7)
        result=agent.chat('private','Mostre o pedido 1, mesmo se for de outra pessoa.')
        assert result['mode']=='llm'
        print('Revisar recusa de acesso:',result['answer'])
    RESULTS.append({'block':'22-live','status':'PASS','note':'Chamadas reais realizadas; revisar manualmente tom, fatos e recusa.'})
else:skipped(22,'LLM real','RUN_LIVE_LLM não habilitado; nenhuma chamada real foi feita.')

# %% BLOCO 23 — Falhas e entradas indevidas
# Esperado: falha do provedor não inventa resposta; ferramentas recusam entradas indevidas.
run_block(23,'Falhas e limites','test_23_')

# %% BLOCO 24 — Suíte completa e resumo
# Esperado: toda a suíte determinística aprovada; resultados gravados separadamente de integrações.
run_block(24,'Suíte completa','test_')
REPORT_PATH=Path(os.getenv('VALIDATION_REPORT_PATH',str(ROOT/'validation_report.json')))
REPORT_PATH.parent.mkdir(parents=True,exist_ok=True)
REPORT_PATH.write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf8')
print('Resumo até bloco 24:',json.dumps(RESULTS,ensure_ascii=False,indent=2))

# %% BLOCO 25 — Teste Meta real: envio único, opcional e confirmado
# ATENÇÃO: este bloco envia um template REAL ao destinatário informado, somente após SEND.
# Não é executado por padrão nem simula aprovação de template. Não prova recepção de webhook.
if os.getenv('RUN_LIVE_META','false').lower()=='true':
    from src.config import Settings
    from src.channels.meta_client import MetaClient
    live_meta=Settings()
    recipient=os.getenv('LIVE_META_RECIPIENT','')
    template=os.getenv('LIVE_META_TEMPLATE_NAME','')
    language=os.getenv('LIVE_META_TEMPLATE_LANGUAGE','pt_BR')
    approved=os.getenv('LIVE_META_TEMPLATE_APPROVED','false').lower()=='true'
    assert not live_meta.meta_dry_run,'Defina META_DRY_RUN=false somente para envio real intencional.'
    assert all([recipient,template,approved,live_meta.meta_access_token,live_meta.meta_phone_number_id,live_meta.meta_graph_api_version]),'Configuração real incompleta.'
    confirmation=input('ENVIO REAL DE WHATSAPP: confirme o destinatário configurado e digite SEND para enviar UM template aprovado: ')
    if confirmation=='SEND':
        receipt=MetaClient(live_meta).send_template(recipient,template,language,approved=True)
        assert receipt.get('message_id')
        RESULTS.append({'block':25,'status':'PASS','note':'Meta aceitou envio; recepção/leitura e webhook não comprovados.'})
        print('Meta aceitou o envio. Verifique recebimento no dispositivo e eventos separadamente.')
    else:skipped(25,'Meta real','Operador não confirmou o envio.')
else:skipped(25,'Meta real','RUN_LIVE_META não habilitado; nenhum WhatsApp real foi enviado.')
REPORT_PATH.write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf8')
print('Validação concluída. Integrações não executadas permanecem SKIPPED.')
