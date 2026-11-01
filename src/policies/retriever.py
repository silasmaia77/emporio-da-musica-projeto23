import re
from functools import lru_cache
from pypdf import PdfReader
from src.data.database import normalize

ALIASES={'pix':'pagamento desconto cumulatividade','parcelas':'parcelamento pagamento','vezes':'parcelamento','devolver':'devolucao arrependimento','devolucao':'arrependimento troca','endereco':'dados empresa rua','aberto':'horario funcionamento','abre':'horario funcionamento','telefone':'whatsapp contato','corda':'acessorios escopo','defeito':'garantia trocas','entrega':'frete prazo','promocao':'promocoes cumulatividade'}
STOP={'a','o','de','da','do','e','em','que','qual','como','para','um','uma','os','as','eu','meu','minha','na','no','tem','loja','por'}

@lru_cache(maxsize=4)
def load_chunks(path):
    chunks=[]
    for number,page in enumerate(PdfReader(path).pages,1):
        text=page.extract_text() or ''
        parts=re.split(r'(?m)(?=^\s*\d+(?:\.\d+)?\.?\s+[A-ZÀ-Ú])',text)
        for part in parts:
            part=part.strip()
            if len(part)<50:continue
            for start in range(0,len(part),1400):
                body=part[start:start+1600]
                chunks.append({'page':number,'section':part.splitlines()[0].strip(),'text':body})
    return chunks

class Policies:
    def __init__(self,path):self.path=str(path)
    def search(self,query,limit=4):
        words=set(normalize(query).split())-STOP
        expanded=set(words)
        for word in words:expanded.update(ALIASES.get(word,'').split())
        scored=[]
        for ch in load_chunks(self.path):
            body=normalize(ch['text']);heading=normalize(ch['section'])
            score=sum((3 if w in heading else 1) for w in expanded if w and w in body)
            if score:scored.append((score,ch))
        return [dict(c,source='políticas_da_loja.pdf') for _,c in sorted(scored,key=lambda x:-x[0])[:max(1,min(limit,6))]]
