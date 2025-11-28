"""
Rotinas para cruzar a base monofásica encontrada nos XML com o que foi
informado no PGDAS-D e registrar o resultado na tabela ResultadoAuditoria.

A ideia é simples:
- Ler a base monofásica calculada pelo motor de regras (rules_engine).
- Ler a base monofásica declarada na PGDAS-D.
- Calcular a diferença e guardar em ResultadoAuditoria, que servirá de base
  para o cálculo dos valores pagos a maior (em calculator.py).
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import CompetenciaPGDAS, Empresa, ResultadoAuditoria
from app.services import rules_engine


def get_or_create_resultado_auditoria(
    db: Session, empresa: Empresa, competencia: CompetenciaPGDAS
) -> ResultadoAuditoria:
    """
    Recupera um ResultadoAuditoria existente para a empresa + competência
    ou cria um novo caso não exista.

    - Se já houver registro, apenas o retorna para ser atualizado.
    - Se não houver, cria um novo vinculado à empresa e à competência,
      adiciona na sessão e faz um flush (sem necessariamente dar commit ainda).
    """

    existente: Optional[ResultadoAuditoria] = (
        db.query(ResultadoAuditoria)
        .filter(
            ResultadoAuditoria.empresa_id == empresa.id,
            ResultadoAuditoria.competencia_id == competencia.id,
        )
        .first()
    )
    if existente:
        return existente

    novo = ResultadoAuditoria(
        empresa_id=empresa.id,
        competencia_id=competencia.id,
        base_monofasica_xml=Decimal(0),
        base_monofasica_pgdas=Decimal(0),
        diferenca_base=Decimal(0),
    )
    db.add(novo)
    db.flush()  # Garante que o ID é gerado antes de retornarmos.
    return novo


def cruzar_competencia(
    db: Session, empresa: Empresa, ano_mes: str
) -> Optional[ResultadoAuditoria]:
    """
    Cruza os valores da competência informada:
    - base_monofasica_xml: soma dos itens classificados como monofásicos nos XML.
    - base_monofasica_pgdas: valor declarado na PGDAS-D.
    - diferenca_base: xml - pgdas.

    Se a competência não existir na tabela CompetenciaPGDAS para a empresa
    informada, retorna None (documentamos para o usuário completar os dados
    antes de rodar o cruzamento).
    """

    competencia: Optional[CompetenciaPGDAS] = (
        db.query(CompetenciaPGDAS)
        .filter(
            CompetenciaPGDAS.empresa_id == empresa.id,
            CompetenciaPGDAS.ano_mes == ano_mes,
        )
        .first()
    )

    if not competencia:
        # Sem dados de PGDAS não conseguimos comparar; retornamos None.
        return None

    base_monofasica_xml = rules_engine.calcular_base_monofasica_xml(
        db, empresa, ano_mes
    )
    base_pgdas_decimal = Decimal(competencia.receita_monofasica_declarada or 0)
    diferenca_base = base_monofasica_xml - base_pgdas_decimal

    resultado = get_or_create_resultado_auditoria(db, empresa, competencia)
    resultado.base_monofasica_xml = base_monofasica_xml
    resultado.base_monofasica_pgdas = base_pgdas_decimal
    resultado.diferenca_base = diferenca_base

    # Neste módulo não calculamos pis_indev/cofins_indev; isso fica no calculator.py.
    db.commit()
    db.refresh(resultado)
    return resultado


def cruzar_intervalo(
    db: Session, empresa: Empresa, ano_mes_inicial: str, ano_mes_final: str
) -> List[ResultadoAuditoria]:
    """
    Executa o cruzamento para todas as competências da empresa dentro do
    intervalo fornecido (inclusive limites).

    Usa comparação de strings no formato AAAA-MM, que funciona para ordenar meses.
    """

    competencias = (
        db.query(CompetenciaPGDAS)
        .filter(
            CompetenciaPGDAS.empresa_id == empresa.id,
            CompetenciaPGDAS.ano_mes >= ano_mes_inicial,
            CompetenciaPGDAS.ano_mes <= ano_mes_final,
        )
        .all()
    )

    resultados: List[ResultadoAuditoria] = []
    for competencia in competencias:
        resultado = cruzar_competencia(db, empresa, competencia.ano_mes)
        if resultado:
            resultados.append(resultado)
    return resultados


def demo_cruzar_competencia_exemplo() -> None:
    """
    Demonstração simples: abre uma sessão, pega a primeira empresa cadastrada,
    cruza os dados da competência 2024-01 e imprime o resumo.

    Mostra:
    - base_monofasica_xml: o que encontramos nos XML.
    - base_monofasica_pgdas: o que foi declarado na PGDAS-D.
    - diferenca_base: se positiva, indica possível pagamento a maior; se
      negativa, indica que pode ter declarado mais monofásico do que consta nos XML.
    """

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        empresa = db.query(Empresa).first()
        if not empresa:
            print("Nenhuma empresa encontrada. Cadastre antes de rodar o demo.")
            return

        resultado = cruzar_competencia(db, empresa, "2024-01")
        if not resultado:
            print("Competência 2024-01 não encontrada na PGDAS para esta empresa.")
            return

        competencia = (
            db.query(CompetenciaPGDAS)
            .filter(CompetenciaPGDAS.id == resultado.competencia_id)
            .first()
        )
        print(
            {
                "empresa_id": resultado.empresa_id,
                "ano_mes": competencia.ano_mes if competencia else "desconhecido",
                "base_monofasica_xml": float(resultado.base_monofasica_xml),
                "base_monofasica_pgdas": float(resultado.base_monofasica_pgdas),
                "diferenca_base": float(resultado.diferenca_base),
            }
        )
    finally:
        db.close()


if __name__ == "__main__":
    # Permite rodar o demo diretamente: python app/services/comparison.py
    demo_cruzar_competencia_exemplo()
