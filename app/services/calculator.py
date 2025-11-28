"""
Módulo responsável por calcular os valores estimados de PIS/COFINS pagos a
maior, a partir do ResultadoAuditoria e das informações de alíquota da
competência.

Fluxo principal:
1) Garantir que a competência tenha a alíquota efetiva preenchida.
2) Descobrir, na tabela AnexoAliquota, qual a partilha PIS/COFINS aplicável
   para a receita bruta acumulada em 12 meses (faixa).
3) Aplicar a partilha sobre a alíquota efetiva para chegar nas alíquotas
   efetivas de PIS e COFINS.
4) Multiplicar pela diferença de base (quando positiva) para estimar o valor
   pago indevidamente.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import AnexoAliquota, CompetenciaPGDAS, Empresa, ResultadoAuditoria


def obter_anexo_aliquota_para_competencia(
    db: Session, competencia: CompetenciaPGDAS
) -> Optional[AnexoAliquota]:
    """
    Busca na tabela AnexoAliquota a linha correspondente ao anexo e à faixa
    (intervalo de receita bruta acumulada em 12 meses) da competência.

    Retorna None se não houver configuração para aquele intervalo, indicando
    que a tabela precisa ser preenchida/ajustada pelo usuário.
    """

    receita_12m = Decimal(competencia.receita_bruta_12m or 0)
    return (
        db.query(AnexoAliquota)
        .filter(
            AnexoAliquota.anexo == competencia.anexo,
            AnexoAliquota.receita_bruta_min <= receita_12m,
            AnexoAliquota.receita_bruta_max >= receita_12m,
        )
        .first()
    )


def garantir_aliquota_efetiva(db: Session, competencia: CompetenciaPGDAS) -> Decimal:
    """
    Garante que a competência tenha aliquota_efetiva preenchida.

    Se já houver valor, apenas o retorna. Caso contrário, calcula usando:
    aliquota_efetiva = (receita_bruta_12m * aliquota_nominal - parcela_a_deduzir) / receita_bruta_12m

    Observação: se a receita_bruta_12m for zero, retornamos Decimal(0) para evitar
    divisão por zero e deixamos o campo aliquota_efetiva como 0.
    """

    if competencia.aliquota_efetiva is not None:
        return Decimal(competencia.aliquota_efetiva)

    receita_12m = Decimal(competencia.receita_bruta_12m or 0)
    if receita_12m == 0:
        competencia.aliquota_efetiva = Decimal(0)
        db.commit()
        return Decimal(0)

    aliquota_nominal = Decimal(competencia.aliquota_nominal or 0)
    parcela_deduzir = Decimal(competencia.parcela_a_deduzir or 0)

    aliquota_efetiva = (receita_12m * aliquota_nominal - parcela_deduzir) / receita_12m
    competencia.aliquota_efetiva = aliquota_efetiva
    db.commit()
    return aliquota_efetiva


def calcular_indev_para_resultado(
    db: Session, resultado: ResultadoAuditoria
) -> ResultadoAuditoria:
    """
    Calcula PIS/COFINS indevidos para um ResultadoAuditoria específico.

    Passos:
    - Carrega a competência vinculada.
    - Garante a alíquota efetiva (calcula se estiver vazia).
    - Busca a partilha PIS/COFINS na tabela AnexoAliquota.
    - Se diferenca_base <= 0, entendemos que não houve pagamento a maior
      (mantemos valores 0) e retornamos.
    - Caso contrário, aplica as alíquotas efetivas sobre a diferença.

    Obs.: Se não houver AnexoAliquota configurada para a faixa, deixamos os
    valores como None para indicar falta de parametrização.
    """

    competencia = resultado.competencia
    if not competencia:
        return resultado

    diferenca_base = Decimal(resultado.diferenca_base or 0)
    if diferenca_base <= 0:
        # Sem base positiva, assumimos que não houve pagamento a maior.
        resultado.pis_indev = Decimal(0)
        resultado.cofins_indev = Decimal(0)
        resultado.total_indev = Decimal(0)
        db.commit()
        db.refresh(resultado)
        return resultado

    aliquota_efetiva = garantir_aliquota_efetiva(db, competencia)
    anexo_faixa = obter_anexo_aliquota_para_competencia(db, competencia)

    if not anexo_faixa:
        # Sem partilha configurada, não conseguimos calcular; mantemos None.
        resultado.pis_indev = None
        resultado.cofins_indev = None
        resultado.total_indev = None
        db.commit()
        db.refresh(resultado)
        return resultado

    aliquota_pis_efetiva = aliquota_efetiva * Decimal(anexo_faixa.percentual_pis or 0)
    aliquota_cofins_efetiva = aliquota_efetiva * Decimal(
        anexo_faixa.percentual_cofins or 0
    )

    pis_indev = diferenca_base * aliquota_pis_efetiva
    cofins_indev = diferenca_base * aliquota_cofins_efetiva
    total_indev = pis_indev + cofins_indev

    resultado.pis_indev = pis_indev
    resultado.cofins_indev = cofins_indev
    resultado.total_indev = total_indev

    db.commit()
    db.refresh(resultado)
    return resultado


def calcular_indev_para_competencia(
    db: Session, empresa: Empresa, ano_mes: str
) -> Optional[ResultadoAuditoria]:
    """
    Calcula valores indevidos para a competência informada (empresa + ano_mes).

    Busca o ResultadoAuditoria correspondente e, se existir, chama
    calcular_indev_para_resultado.
    """

    resultado: Optional[ResultadoAuditoria] = (
        db.query(ResultadoAuditoria)
        .join(CompetenciaPGDAS, ResultadoAuditoria.competencia_id == CompetenciaPGDAS.id)
        .filter(
            ResultadoAuditoria.empresa_id == empresa.id,
            CompetenciaPGDAS.ano_mes == ano_mes,
        )
        .first()
    )

    if not resultado:
        return None

    return calcular_indev_para_resultado(db, resultado)


def calcular_indev_para_todas_competencias(
    db: Session, empresa: Empresa
) -> List[ResultadoAuditoria]:
    """
    Percorre todos os resultados de auditoria da empresa e calcula os valores
    indevidos de PIS/COFINS para cada um.
    """

    resultados = (
        db.query(ResultadoAuditoria)
        .filter(ResultadoAuditoria.empresa_id == empresa.id)
        .all()
    )

    calculados: List[ResultadoAuditoria] = []
    for resultado in resultados:
        calculados.append(calcular_indev_para_resultado(db, resultado))
    return calculados


def demo_calcular_indev_exemplo() -> None:
    """
    Demonstração: abre uma sessão, pega a primeira empresa cadastrada e
    calcula os valores indevidos para a competência 2024-01 (se existir
    ResultadoAuditoria).
    """

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        empresa = db.query(Empresa).first()
        if not empresa:
            print("Nenhuma empresa encontrada. Cadastre antes de rodar o demo.")
            return

        resultado = calcular_indev_para_competencia(db, empresa, "2024-01")
        if not resultado:
            print("Não há ResultadoAuditoria para a competência 2024-01.")
            return

        competencia = resultado.competencia
        print(
            {
                "ano_mes": competencia.ano_mes if competencia else "desconhecido",
                "diferenca_base": float(resultado.diferenca_base),
                "pis_indev": float(resultado.pis_indev) if resultado.pis_indev is not None else None,
                "cofins_indev": float(resultado.cofins_indev)
                if resultado.cofins_indev is not None
                else None,
                "total_indev": float(resultado.total_indev) if resultado.total_indev is not None else None,
            }
        )
    finally:
        db.close()


if __name__ == "__main__":
    # Permite rodar o demo diretamente: python app/services/calculator.py
    demo_calcular_indev_exemplo()
