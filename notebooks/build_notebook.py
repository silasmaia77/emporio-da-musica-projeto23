"""Build an equivalent notebook from readable # %% Python cells."""
from pathlib import Path
import re
import nbformat

def build():
    here=Path(__file__).resolve().parent
    source=(here/'01_validacao_completa.py').read_text(encoding='utf8')
    chunks=re.split(r'^# %% ',source,flags=re.MULTILINE)[1:]
    notebook=nbformat.v4.new_notebook()
    notebook.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.10'}}
    notebook.cells=[nbformat.v4.new_markdown_cell('# Validação completa — Empório da Música\n\n25 blocos numerados. Células Python. Por padrão, sem chamadas reais ao LLM ou à Meta. Execute em ordem; resultados externos ausentes são marcados como não executados.')]
    for chunk in chunks:
        title,code=chunk.split('\n',1)
        notebook.cells.extend([nbformat.v4.new_markdown_cell('## '+title),nbformat.v4.new_code_cell(code)])
    nbformat.validate(notebook)
    nbformat.write(notebook,here/'01_validacao_completa.ipynb')
    print(f'Notebook gerado: {len(chunks)} blocos Python.')
if __name__=='__main__':build()
