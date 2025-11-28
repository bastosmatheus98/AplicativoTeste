"""Aplicação FastAPI com templates para rodar a auditoria de PGDAS-D x XML.

Esta versão monta rotas básicas para upload de arquivos, execução da auditoria
simplificada e exibição de resultados. Para iniciar localmente:

    uvicorn app.main:app --reload

"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import create_all_tables
from app.routers import audits, uploads

# Cria a aplicação FastAPI.
app = FastAPI(title="Auditoria Monofásico - PGDAS x XML")

# Configura os templates Jinja2, apontando para a pasta app/templates.
templates = Jinja2Templates(directory="app/templates")

# Garante que as tabelas existam ao subir a aplicação.
create_all_tables()

# Inclui as rotas principais (upload/processamento e futuras rotas de auditoria).
app.include_router(uploads.router)
app.include_router(audits.router)

# Exposição de arquivos estáticos (CSS, imagens, relatórios) se necessário.
# A pasta app/static pode conter um CSS simples ou assets adicionais.
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Pastas geradas pelos relatórios e peça espelho, para download direto.
app.mount("/relatorios", StaticFiles(directory="relatorios"), name="relatorios")
app.mount("/pecas", StaticFiles(directory="pecas"), name="pecas")


@app.get("/health")
def healthcheck():
    """Rota simples para testar se o servidor está no ar."""
    return {"status": "ok"}


# Observação: para iniciar o servidor localmente use o comando
# uvicorn app.main:app --reload
