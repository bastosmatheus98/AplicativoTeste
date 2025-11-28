"""Router reservado para rotas de auditoria adicionais.

Nesta versão inicial deixamos apenas uma rota exemplo/placeholder. O fluxo
principal está no POST /processar do router uploads.py.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("/ping")
def ping():
    """Endpoint simples para validar o namespace de auditoria."""

    return {"status": "auditoria ok"}
