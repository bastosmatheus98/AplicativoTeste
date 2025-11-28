"""
Motor de regras simples para classificar itens de NF-e e calcular a base
monofásica encontrada nos XML, por competência e por empresa.

Regras implementadas (versão inicial):
- Usa a tabela parametrizável de NCM monofásicos (NCMMonofasico) para
  decidir se um produto pode ser monofásico em uma data específica.
- Interpreta CST 04 como indicativo de monofásico em revenda.
- Marca itens como monofásicos ou inconsistentes conforme combinação de
  NCM e CST.
- Soma o valor total dos itens monofásicos para obter a base dos XML.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import Empresa, ItemNota, NCMMonofasico, NotaFiscal


def competencia_from_date(data: date | datetime) -> str:
    """Retorna a competência no formato "AAAA-MM" a partir de uma data."""

    # Aceita tanto date quanto datetime. Sempre pega ano e mês em quatro e dois dígitos.
    return f"{data.year:04d}-{data.month:02d}"


def _ncm_esta_em_vigencia(
    db_sessao: Session, ncm: str, data_referencia: date
) -> bool:
    """
    Verifica se existe um registro de NCM monofásico vigente para o NCM informado
    na data de referência. Considera flag_monofasico = True.
    """

    # Procura NCM igual, com início de vigência até a data e fim nulo ou após a data.
    existe = (
        db_sessao.query(NCMMonofasico)
        .filter(
            NCMMonofasico.ncm == ncm,
            NCMMonofasico.flag_monofasico.is_(True),
            NCMMonofasico.data_inicio_vigencia <= data_referencia,
            or_(
                NCMMonofasico.data_fim_vigencia.is_(None),
                NCMMonofasico.data_fim_vigencia >= data_referencia,
            ),
        )
        .first()
    )
    return existe is not None


def classificar_item(item: ItemNota, ncm_monofasico: bool) -> None:
    """
    Classifica um ItemNota ajustando flags eh_monofasico e eh_inconsistente.

    Regras (versão simplificada):
    - NCM monofásico + CST 04 em PIS ou COFINS -> monofásico.
    - NCM monofásico + CST diferente de 04 -> inconsistente.
    - NCM não monofásico + CST 04 -> inconsistente.
    - Caso contrário -> não monofásico.
    """

    cst_pis = (item.cst_pis or "").strip()
    cst_cofins = (item.cst_cofins or "").strip()
    possui_cst_04 = cst_pis == "04" or cst_cofins == "04"

    # Reset básico antes de classificar.
    item.eh_monofasico = False
    item.eh_inconsistente = False

    if ncm_monofasico and possui_cst_04:
        # Caso ideal: NCM vigente como monofásico e CST 04 confirma revenda monofásica.
        item.eh_monofasico = True
    elif ncm_monofasico and not possui_cst_04:
        # NCM sugere monofásico, mas CST não indica isso -> potencial erro de classificação.
        item.eh_inconsistente = True
    elif not ncm_monofasico and possui_cst_04:
        # CST diz monofásico, mas NCM não consta na tabela -> inconsistente.
        item.eh_inconsistente = True
    # Demais casos permanecem como não monofásico e não inconsistente.


def _intervalo_datas_competencia(ano_mes: str) -> Tuple[datetime, datetime]:
    """
    Calcula o primeiro dia e o primeiro dia do mês seguinte para filtrar por competência.
    """

    ano, mes = map(int, ano_mes.split("-"))
    inicio = datetime(ano, mes, 1)
    if mes == 12:
        fim = datetime(ano + 1, 1, 1)
    else:
        fim = datetime(ano, mes + 1, 1)
    return inicio, fim


def classificar_itens_empresa_competencia(
    db_sessao: Session, empresa: Empresa, ano_mes: str
) -> int:
    """
    Percorre todos os itens das notas de uma empresa na competência informada
    e aplica a classificação monofásico / inconsistente / não monofásico.

    Retorna a quantidade de itens processados.
    """

    data_inicio, data_fim = _intervalo_datas_competencia(ano_mes)

    # Busca notas da empresa emitidas dentro do intervalo da competência.
    notas = (
        db_sessao.query(NotaFiscal)
        .filter(
            NotaFiscal.empresa_id == empresa.id,
            NotaFiscal.data_emissao >= data_inicio,
            NotaFiscal.data_emissao < data_fim,
        )
        .all()
    )

    itens_processados = 0

    for nota in notas:
        # Para cada item, verificamos se o NCM está em vigência como monofásico.
        data_ref = nota.data_emissao.date()
        for item in nota.itens:
            ncm_vigente = _ncm_esta_em_vigencia(db_sessao, item.ncm, data_ref)
            classificar_item(item, ncm_vigente)
            itens_processados += 1

    # Persistimos as mudanças de flags no banco.
    db_sessao.commit()
    return itens_processados


def calcular_base_monofasica_xml(
    db_sessao: Session, empresa: Empresa, ano_mes: str
) -> Decimal:
    """
    Soma o valor_total dos itens classificados como monofásicos para a competência.

    Retorna um Decimal com a base encontrada nos XML.
    """

    data_inicio, data_fim = _intervalo_datas_competencia(ano_mes)

    soma = (
        db_sessao.query(func.coalesce(func.sum(ItemNota.valor_total), 0))
        .join(NotaFiscal, ItemNota.nota_id == NotaFiscal.id)
        .filter(
            NotaFiscal.empresa_id == empresa.id,
            NotaFiscal.data_emissao >= data_inicio,
            NotaFiscal.data_emissao < data_fim,
            ItemNota.eh_monofasico.is_(True),
        )
        .scalar()
    )

    # Garantimos que retornará Decimal para evitar perda de precisão.
    return Decimal(soma)


def rodar_regras_para_competencia(
    db_sessao: Session, empresa: Empresa, ano_mes: str
) -> Dict[str, object]:
    """
    Executa a classificação dos itens e calcula a base monofásica dos XML
    para uma competência específica de uma empresa.

    Retorna um dicionário resumindo o que foi processado.
    """

    itens_classificados = classificar_itens_empresa_competencia(
        db_sessao, empresa, ano_mes
    )
    base_monofasica_xml = calcular_base_monofasica_xml(db_sessao, empresa, ano_mes)

    return {
        "empresa_id": empresa.id,
        "ano_mes": ano_mes,
        "base_monofasica_xml": float(base_monofasica_xml),
        "itens_classificados": itens_classificados,
    }


def demo_rodar_regras_exemplo() -> None:
    """
    Demonstração simples: abre uma sessão, pega a primeira empresa cadastrada,
    roda as regras para a competência 2024-01 e imprime o resultado.
    """

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        empresa = db.query(Empresa).first()
        if not empresa:
            print("Nenhuma empresa encontrada. Cadastre antes de rodar o demo.")
            return

        resultado = rodar_regras_para_competencia(db, empresa, "2024-01")
        print("Resultado da classificação:", resultado)
    finally:
        db.close()


if __name__ == "__main__":
    # Permite rodar o demo diretamente: python app/services/rules_engine.py
    demo_rodar_regras_exemplo()
