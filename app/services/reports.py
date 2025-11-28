"""
Módulo de geração de relatórios tabulares (Excel/CSV) a partir dos dados
consolidados da auditoria. Usa pandas para montar DataFrames e salvar os
arquivos em uma pasta padrão (./relatorios/).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import (
    CompetenciaPGDAS,
    Empresa,
    ItemNota,
    NCMMonofasico,
    NotaFiscal,
    ResultadoAuditoria,
)
from app.services.rules_engine import competencia_from_date

# Pasta padrão onde os relatórios serão salvos.
PASTA_RELATORIOS = Path("relatorios")


def _garantir_pasta_saida(caminho: Path) -> None:
    """
    Cria a pasta de saída (e pais) caso ainda não exista.
    """

    caminho.parent.mkdir(parents=True, exist_ok=True)


def gerar_relatorio_resumo_competencias(
    db: Session, empresa: Empresa, caminho_saida: Optional[str] = None
) -> str:
    """
    Gera um relatório resumido por competência já auditada.

    Colunas:
    - CNPJ
    - ano_mes
    - anexo
    - receita_bruta_total
    - receita_monofasica_xml (base_monofasica_xml)
    - receita_monofasica_pgdas (base_monofasica_pgdas)
    - diferenca_base
    - pis_indev
    - cofins_indev
    - total_indev

    Retorna o caminho do arquivo salvo (Excel por padrão).
    """

    resultados: List[ResultadoAuditoria] = (
        db.query(ResultadoAuditoria)
        .filter(ResultadoAuditoria.empresa_id == empresa.id)
        .all()
    )

    linhas = []
    for resultado in resultados:
        competencia: Optional[CompetenciaPGDAS] = resultado.competencia
        if not competencia:
            continue

        linhas.append(
            {
                "cnpj": empresa.cnpj,
                "ano_mes": competencia.ano_mes,
                "anexo": competencia.anexo,
                "receita_bruta_total": float(competencia.receita_bruta_total or 0),
                "receita_monofasica_xml": float(resultado.base_monofasica_xml or 0),
                "receita_monofasica_pgdas": float(resultado.base_monofasica_pgdas or 0),
                "diferenca_base": float(resultado.diferenca_base or 0),
                "pis_indev": float(resultado.pis_indev) if resultado.pis_indev is not None else None,
                "cofins_indev": float(resultado.cofins_indev) if resultado.cofins_indev is not None else None,
                "total_indev": float(resultado.total_indev) if resultado.total_indev is not None else None,
            }
        )

    df = pd.DataFrame(linhas)

    if caminho_saida is None:
        caminho_saida = PASTA_RELATORIOS / f"resumo_competencias_{empresa.cnpj}.xlsx"
    else:
        caminho_saida = Path(caminho_saida)

    _garantir_pasta_saida(caminho_saida)
    df.to_excel(caminho_saida, index=False)
    return str(caminho_saida)


def gerar_relatorio_detalhe_ncm(
    db: Session,
    empresa: Empresa,
    ano_mes_inicial: str,
    ano_mes_final: str,
    caminho_saida: Optional[str] = None,
) -> str:
    """
    Gera um relatório detalhado por NCM dentro de um intervalo de competências.

    Considera apenas itens marcados como monofásicos (eh_monofasico = True) e
    cuja competência (derivada da data de emissão da nota) esteja entre
    ano_mes_inicial e ano_mes_final (comparação de strings AAAA-MM).
    """

    # Pré-carrega descrições de NCM para enriquecer o relatório.
    descricoes_ncm: Dict[str, str] = {ref.ncm: ref.descricao for ref in db.query(NCMMonofasico).all()}

    itens = (
        db.query(ItemNota)
        .join(NotaFiscal, ItemNota.nota_id == NotaFiscal.id)
        .filter(NotaFiscal.empresa_id == empresa.id, ItemNota.eh_monofasico.is_(True))
        .all()
    )

    agregados: Dict[tuple, Dict[str, object]] = {}
    for item in itens:
        nota = item.nota
        if not nota or not nota.data_emissao:
            continue

        competencia = competencia_from_date(nota.data_emissao)
        if competencia < ano_mes_inicial or competencia > ano_mes_final:
            continue

        chave = (competencia, item.ncm)
        if chave not in agregados:
            agregados[chave] = {
                "cnpj": empresa.cnpj,
                "ano_mes": competencia,
                "ncm": item.ncm,
                "descricao_ncm": descricoes_ncm.get(item.ncm),
                "valor_total_monofasico": 0.0,
                "quantidade_itens": 0,
            }

        agregados[chave]["valor_total_monofasico"] += float(item.valor_total or 0)
        agregados[chave]["quantidade_itens"] += 1

    df = pd.DataFrame(list(agregados.values()))

    if caminho_saida is None:
        caminho_saida = PASTA_RELATORIOS / f"detalhe_ncm_{empresa.cnpj}.xlsx"
    else:
        caminho_saida = Path(caminho_saida)

    _garantir_pasta_saida(caminho_saida)
    df.to_excel(caminho_saida, index=False)
    return str(caminho_saida)


def gerar_relatorio_inconsistencias(db: Session, empresa: Empresa, caminho_saida: Optional[str] = None) -> str:
    """
    Lista todos os itens marcados como inconsistentes (CST x NCM) para a empresa.

    Colunas:
    - CNPJ
    - ano_mes (derivado da data de emissão)
    - chave da nota
    - NCM
    - CFOP
    - CST_PIS
    - CST_COFINS
    - valor_total
    """

    itens_inconsistentes: List[ItemNota] = (
        db.query(ItemNota)
        .join(NotaFiscal, ItemNota.nota_id == NotaFiscal.id)
        .filter(NotaFiscal.empresa_id == empresa.id, ItemNota.eh_inconsistente.is_(True))
        .all()
    )

    linhas = []
    for item in itens_inconsistentes:
        nota = item.nota
        if not nota:
            continue
        ano_mes = competencia_from_date(nota.data_emissao) if nota.data_emissao else None
        linhas.append(
            {
                "cnpj": empresa.cnpj,
                "ano_mes": ano_mes,
                "chave_nfe": nota.chave,
                "ncm": item.ncm,
                "cfop": item.cfop,
                "cst_pis": item.cst_pis,
                "cst_cofins": item.cst_cofins,
                "valor_total": float(item.valor_total or 0),
            }
        )

    df = pd.DataFrame(linhas)

    if caminho_saida is None:
        caminho_saida = PASTA_RELATORIOS / f"inconsistencias_{empresa.cnpj}.xlsx"
    else:
        caminho_saida = Path(caminho_saida)

    _garantir_pasta_saida(caminho_saida)
    df.to_excel(caminho_saida, index=False)
    return str(caminho_saida)


def gerar_todos_relatorios(db: Session, empresa: Empresa, ano_mes_inicial: str, ano_mes_final: str) -> Dict[str, str]:
    """
    Gera os três relatórios principais de uma vez e devolve os caminhos gerados.
    """

    caminhos = {
        "resumo": gerar_relatorio_resumo_competencias(db, empresa),
        "detalhe_ncm": gerar_relatorio_detalhe_ncm(db, empresa, ano_mes_inicial, ano_mes_final),
        "inconsistencias": gerar_relatorio_inconsistencias(db, empresa),
    }
    return caminhos


def demo_gerar_relatorios_exemplo() -> None:
    """
    Demonstração simples: gera os três relatórios para a primeira empresa
    cadastrada, considerando o intervalo 2024-01 a 2024-12.
    """

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        empresa = db.query(Empresa).first()
        if not empresa:
            print("Nenhuma empresa encontrada. Cadastre antes de rodar o demo.")
            return

        caminhos = gerar_todos_relatorios(db, empresa, "2024-01", "2024-12")
        print("Relatórios gerados:")
        for nome, caminho in caminhos.items():
            print(f"- {nome}: {caminho}")
    finally:
        db.close()


if __name__ == "__main__":
    # Permite rodar o demo diretamente: python app/services/reports.py
    demo_gerar_relatorios_exemplo()
