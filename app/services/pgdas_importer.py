"""
Importador de dados do PGDAS-D a partir de arquivos CSV simples.
Usamos a biblioteca `csv` padrão para ler linha a linha e gravamos
em `CompetenciaPGDAS`, relacionando com a empresa informada.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Optional

from app.models import CompetenciaPGDAS, Empresa


def _parse_decimal(valor: Optional[str]) -> Optional[float]:
    """
    Converte uma string numérica em float.
    Retorna None quando o valor está vazio ou é None.
    """

    if valor is None:
        return None
    texto = valor.strip()
    if texto == "":
        return None
    return float(texto)


def upsert_competencia_pgdas(dados: Dict[str, str], db_sessao, empresa: Empresa) -> CompetenciaPGDAS:
    """
    Cria ou atualiza um registro de CompetenciaPGDAS para a empresa informada.

    - Recebe um dicionário com campos como ano_mes, anexo, receitas e alíquotas.
    - Se já existir um registro para a mesma empresa + ano_mes, ele é atualizado.
    - Caso contrário, um novo registro é criado e associado à empresa.
    """

    ano_mes = dados.get("ano_mes")
    if not ano_mes:
        raise ValueError("Campo 'ano_mes' é obrigatório no CSV do PGDAS-D")

    # Procura se já existe competência para a empresa + ano_mes
    competencia = (
        db_sessao.query(CompetenciaPGDAS)
        .filter(CompetenciaPGDAS.empresa_id == empresa.id)
        .filter(CompetenciaPGDAS.ano_mes == ano_mes)
        .first()
    )

    if competencia is None:
        competencia = CompetenciaPGDAS(empresa_id=empresa.id, ano_mes=ano_mes)
        db_sessao.add(competencia)

    # Atualiza/atribui campos numéricos e de anexo
    competencia.anexo = dados.get("anexo") or competencia.anexo
    competencia.receita_bruta_total = _parse_decimal(dados.get("receita_bruta_total")) or 0.0
    competencia.receita_monofasica_declarada = _parse_decimal(
        dados.get("receita_monofasica_declarada")
    ) or 0.0
    competencia.receita_substituicao_tributaria = _parse_decimal(
        dados.get("receita_substituicao_tributaria")
    )
    competencia.receita_outras_exclusoes = _parse_decimal(
        dados.get("receita_outras_exclusoes")
    )
    competencia.receita_bruta_12m = _parse_decimal(dados.get("receita_bruta_12m")) or 0.0
    competencia.aliquota_nominal = _parse_decimal(dados.get("aliquota_nominal"))
    competencia.parcela_a_deduzir = _parse_decimal(dados.get("parcela_a_deduzir"))
    competencia.aliquota_efetiva = _parse_decimal(dados.get("aliquota_efetiva"))

    return competencia


def importar_pgdas_csv(caminho_arquivo: str, db_sessao, empresa: Empresa) -> None:
    """
    Lê um arquivo CSV exportado do PGDAS-D e grava/atualiza as competências
    daquela empresa no banco de dados.

    Espera um cabeçalho com colunas como:
    ano_mes,anexo,receita_bruta_total,receita_monofasica_declarada,
    receita_substituicao_tributaria,receita_outras_exclusoes,receita_bruta_12m,
    aliquota_nominal,parcela_a_deduzir,aliquota_efetiva

    - `caminho_arquivo`: caminho para o CSV.
    - `db_sessao`: sessão do SQLAlchemy já aberta.
    - `empresa`: instância da Empresa à qual as competências pertencem.
    """

    caminho = Path(caminho_arquivo)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {caminho_arquivo}")

    with caminho.open(mode="r", encoding="utf-8", newline="") as csvfile:
        leitor = csv.DictReader(csvfile)

        for linha in leitor:
            # Para cada linha, fazemos o upsert na tabela de competências.
            upsert_competencia_pgdas(linha, db_sessao, empresa)

        # Após percorrer todas as linhas, confirmamos as alterações.
        db_sessao.commit()


def demo_importar_pgdas_exemplo() -> None:
    """
    Demonstração rápida de como importar um CSV do PGDAS-D para uma empresa.

    - Abre uma sessão do banco via SessionLocal.
    - Busca a primeira empresa cadastrada.
    - Chama `importar_pgdas_csv` apontando para um arquivo de exemplo.
    """

    from app.database import SessionLocal  # Import local para evitar ciclos
    from app.models import Empresa

    db = SessionLocal()

    try:
        empresa = db.query(Empresa).first()
        if empresa is None:
            print("Nenhuma empresa encontrada. Cadastre uma antes de importar o PGDAS.")
            return

        importar_pgdas_csv("./dados_pgdas.csv", db, empresa)
        print("Importação concluída com sucesso!")
    finally:
        db.close()
