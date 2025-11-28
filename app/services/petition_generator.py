"""
Gera uma "peça espelho" em HTML com base nos resultados de auditoria. O HTML
servirá como modelo de petição para retificação das PGDAS-D e pedido de
restituição de PIS/COFINS, devendo ser revisado por profissional habilitado.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import CompetenciaPGDAS, Empresa, ResultadoAuditoria

PASTA_PECAS = Path("pecas")


def obter_resultados_para_peca(
    db: Session,
    empresa: Empresa,
    ano_mes_inicial: Optional[str] = None,
    ano_mes_final: Optional[str] = None,
) -> List[ResultadoAuditoria]:
    """
    Retorna os resultados de auditoria da empresa, opcionalmente filtrados
    por intervalo de competências (inclusive limites) no formato AAAA-MM.
    """

    query = db.query(ResultadoAuditoria).join(CompetenciaPGDAS)
    query = query.filter(ResultadoAuditoria.empresa_id == empresa.id)

    if ano_mes_inicial:
        query = query.filter(CompetenciaPGDAS.ano_mes >= ano_mes_inicial)
    if ano_mes_final:
        query = query.filter(CompetenciaPGDAS.ano_mes <= ano_mes_final)

    resultados = query.order_by(CompetenciaPGDAS.ano_mes).all()
    return resultados


def gerar_peca_espelho_html(
    db: Session,
    empresa: Empresa,
    resultados: List[ResultadoAuditoria],
    caminho_saida: Optional[str] = None,
) -> str:
    """
    Monta um HTML simples com a narrativa básica da petição e uma tabela
    resumo das competências auditadas.

    - O documento é um modelo e deve ser revisado por contador/advogado.
    - Os valores exibidos são provenientes da tabela ResultadoAuditoria.
    """

    if caminho_saida is None:
        caminho_saida = PASTA_PECAS / f"peca_espelho_{empresa.cnpj}.html"
    else:
        caminho_saida = Path(caminho_saida)

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    linhas_tabela = ""
    for resultado in resultados:
        competencia = resultado.competencia
        ano_mes = competencia.ano_mes if competencia else "-"
        linhas_tabela += f"""
        <tr>
            <td>{ano_mes}</td>
            <td>{float(resultado.base_monofasica_xml or 0):,.2f}</td>
            <td>{float(resultado.base_monofasica_pgdas or 0):,.2f}</td>
            <td>{float(resultado.diferenca_base or 0):,.2f}</td>
            <td>{float(resultado.pis_indev or 0):,.2f}</td>
            <td>{float(resultado.cofins_indev or 0):,.2f}</td>
            <td>{float(resultado.total_indev or 0):,.2f}</td>
        </tr>
        """

    html = f"""
<html>
<head>
    <meta charset="utf-8">
    <title>Peça Espelho - Retificação PGDAS-D e Restituição PIS/COFINS</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .observacao {{ margin-top: 24px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <h1>Requerimento de Retificação de PGDAS-D e Restituição de PIS/COFINS</h1>

    <h2>1. Qualificação da Empresa</h2>
    <p><strong>Razão Social:</strong> {empresa.razao_social}</p>
    <p><strong>CNPJ:</strong> {empresa.cnpj}</p>

    <h2>2. Dos Fatos e da Metodologia de Auditoria</h2>
    <p>
        Esta peça foi gerada automaticamente a partir do cruzamento de XML de NF-e
        (modelo 55) com as declarações PGDAS-D. O sistema identifica produtos
        sujeitos ao regime monofásico de PIS/COFINS usando NCM e CST (tipicamente
        CST 04), compara a base monofásica encontrada nos XML com a base declarada
        no PGDAS-D e calcula a diferença de base e os valores de PIS/COFINS
        potencialmente pagos a maior.
    </p>

    <h2>3. Quadro Resumo por Competência</h2>
    <table>
        <thead>
            <tr>
                <th>Competência (AAAA-MM)</th>
                <th>Base monofásica nos XML</th>
                <th>Base monofásica declarada no PGDAS-D</th>
                <th>Diferença de base</th>
                <th>PIS indevido estimado</th>
                <th>COFINS indevido estimado</th>
                <th>Total indevido</th>
            </tr>
        </thead>
        <tbody>
            {linhas_tabela}
        </tbody>
    </table>

    <h2>4. Do Direito</h2>
    <p>
        De forma geral, o Simples Nacional (LC 123/2006) prevê que receitas de
        produtos sujeitos ao regime monofásico de PIS/COFINS não devem compor a
        base das contribuições na etapa varejista, uma vez que a tributação é
        concentrada na indústria/importador. A correta segregação dessas receitas
        no PGDAS-D evita dupla incidência. Este modelo não substitui análise
        jurídica individualizada e deve ser revisado por profissional habilitado.
    </p>

    <h2>5. Dos Pedidos</h2>
    <ul>
        <li>Retificação das declarações PGDAS-D das competências listadas.</li>
        <li>Restituição ou compensação dos valores de PIS/COFINS pagos a maior,
            com atualização monetária conforme legislação aplicável.</li>
        <li>Notificação do contribuinte para eventual complementação de
            informações ou documentos, se necessário.</li>
    </ul>

    <p class="observacao">
        Este documento é um modelo gerado automaticamente pelo sistema de
        auditoria e deve ser revisado e adaptado por profissional habilitado
        antes de protocolo.
    </p>
</body>
</html>
"""

    caminho_saida.write_text(html, encoding="utf-8")
    return str(caminho_saida)


def gerar_peca_espelho_por_intervalo(
    db: Session,
    empresa: Empresa,
    ano_mes_inicial: Optional[str] = None,
    ano_mes_final: Optional[str] = None,
) -> str:
    """
    Recupera os resultados de auditoria no intervalo informado e gera a peça.
    """

    resultados = obter_resultados_para_peca(db, empresa, ano_mes_inicial=ano_mes_inicial, ano_mes_final=ano_mes_final)
    return gerar_peca_espelho_html(db, empresa, resultados)


def demo_gerar_peca_exemplo() -> None:
    """
    Demonstração: abre uma sessão, pega a primeira empresa cadastrada e gera
    um arquivo HTML de peça espelho com todos os resultados de auditoria.
    """

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        empresa = db.query(Empresa).first()
        if not empresa:
            print("Nenhuma empresa encontrada. Cadastre antes de rodar o demo.")
            return

        resultados = obter_resultados_para_peca(db, empresa)
        caminho = gerar_peca_espelho_html(db, empresa, resultados)
        print(f"Peça gerada em: {caminho}")
    finally:
        db.close()


if __name__ == "__main__":
    # Permite rodar o demo diretamente: python app/services/petition_generator.py
    demo_gerar_peca_exemplo()
