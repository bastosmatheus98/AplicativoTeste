"""Rotas principais para a interface web de upload e processamento da auditoria.

Aqui temos:
- GET "/" para exibir o formulário inicial.
- POST "/processar" para receber os arquivos, rodar a auditoria completa e
  renderizar uma página de resultados.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Empresa, ResultadoAuditoria
from app.services import calculator, comparison, pgdas_importer, petition_generator, reports, rules_engine, xml_parser

# Instância de templates (apontando para a mesma pasta configurada em main.py).
templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


def _gerar_intervalo_competencias(competencia_inicial: str, competencia_final: str) -> List[str]:
    """Gera uma lista de competências AAAA-MM entre os limites informados."""

    competencias: List[str] = []
    atual = datetime.strptime(competencia_inicial, "%Y-%m")
    fim = datetime.strptime(competencia_final, "%Y-%m")

    while atual <= fim:
        competencias.append(atual.strftime("%Y-%m"))
        if atual.month == 12:
            atual = atual.replace(year=atual.year + 1, month=1)
        else:
            atual = atual.replace(month=atual.month + 1)
    return competencias


def _get_or_create_empresa(db: Session, cnpj: str, razao_social: Optional[str] = None) -> Empresa:
    """Busca a empresa pelo CNPJ ou cria um novo registro."""

    empresa: Optional[Empresa] = db.query(Empresa).filter(Empresa.cnpj == cnpj).first()
    if empresa:
        # Atualiza razão social se veio preenchida agora.
        if razao_social and not empresa.razao_social:
            empresa.razao_social = razao_social
            db.commit()
            db.refresh(empresa)
        return empresa

    nova = Empresa(cnpj=cnpj, razao_social=razao_social)
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova


async def _salvar_uploads(arquivos: List[UploadFile], pasta_destino: Path) -> List[Path]:
    """Salva os UploadFile recebidos em disco e retorna a lista de caminhos."""

    caminhos: List[Path] = []
    pasta_destino.mkdir(parents=True, exist_ok=True)
    for arquivo in arquivos:
        if not arquivo.filename:
            continue
        destino = pasta_destino / arquivo.filename
        conteudo = await arquivo.read()
        destino.write_bytes(conteudo)
        caminhos.append(destino)
    return caminhos


@router.get("/", response_class=HTMLResponse)
async def pagina_inicial(request: Request):
    """Exibe o formulário de upload e parâmetros da auditoria."""

    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/processar", response_class=HTMLResponse)
async def processar_auditoria(
    request: Request,
    cnpj: str = Form(...),
    razao_social: Optional[str] = Form(None),
    competencia_inicial: str = Form(...),
    competencia_final: str = Form(...),
    xml_files: Optional[List[UploadFile]] = File(None),
    pgdas_files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    """
    Recebe os arquivos e parâmetros do formulário, roda a auditoria completa e
    mostra um resumo com links para download dos relatórios e peça espelho.
    """

    empresa = _get_or_create_empresa(db, cnpj=cnpj, razao_social=razao_social)

    # Salva os uploads em pastas separadas.
    xml_paths = await _salvar_uploads(xml_files or [], Path("uploads/xmls"))
    pgdas_paths = await _salvar_uploads(pgdas_files or [], Path("uploads/pgdas"))

    # Importa XMLs de NF-e.
    for caminho in xml_paths:
        xml_parser.importar_xml_nfe(str(caminho), db, empresa)

    # Importa arquivos PGDAS (CSV).
    for caminho in pgdas_paths:
        pgdas_importer.importar_pgdas_csv(str(caminho), db, empresa)

    # Gera lista de competências a processar.
    competencias = _gerar_intervalo_competencias(competencia_inicial, competencia_final)

    # Classifica itens, cruza bases e calcula indevidos para cada competência.
    for comp in competencias:
        rules_engine.classificar_itens_empresa_competencia(db, empresa, comp)
        comparison.cruzar_competencia(db, empresa, comp)
        calculator.calcular_indev_para_competencia(db, empresa, comp)

    # Gera relatórios e peça espelho para o intervalo.
    paths_relatorios = reports.gerar_todos_relatorios(db, empresa, competencia_inicial, competencia_final)
    path_peca = petition_generator.gerar_peca_espelho_por_intervalo(
        db, empresa, competencia_inicial, competencia_final
    )

    # Monta lista de competências para exibição.
    competencias_resumo = []
    for comp in competencias:
        resultado: Optional[ResultadoAuditoria] = (
            db.query(ResultadoAuditoria)
            .join(ResultadoAuditoria.competencia)
            .filter(
                ResultadoAuditoria.empresa_id == empresa.id,
                ResultadoAuditoria.competencia.has(ano_mes=comp),
            )
            .first()
        )
        if not resultado:
            continue
        competencias_resumo.append(
            {
                "ano_mes": comp,
                "base_xml": float(resultado.base_monofasica_xml or 0),
                "base_pgdas": float(resultado.base_monofasica_pgdas or 0),
                "diferenca_base": float(resultado.diferenca_base or 0),
                "pis_indev": float(resultado.pis_indev) if resultado.pis_indev is not None else None,
                "cofins_indev": float(resultado.cofins_indev) if resultado.cofins_indev is not None else None,
                "total_indev": float(resultado.total_indev) if resultado.total_indev is not None else None,
            }
        )

    contexto = {
        "request": request,
        "empresa": empresa,
        "competencias": competencias_resumo,
        "paths_relatorios": paths_relatorios,
        "path_peca": path_peca,
    }
    return templates.TemplateResponse("audit_result.html", contexto)
