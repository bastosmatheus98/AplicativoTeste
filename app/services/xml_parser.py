"""
Serviço de parsing e importação de XML de NF-e (modelo 55) para o banco de dados.
O objetivo é extrair os dados relevantes de cabeçalho e itens e gravar
nas tabelas NotaFiscal e ItemNota associadas a uma Empresa.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Optional
import xml.etree.ElementTree as ET

from sqlalchemy.orm import Session

from app.models import Empresa, ItemNota, NotaFiscal


# Helpers de parsing ---------------------------------------------------------

def _find_first(element: ET.Element, candidates: Iterable[str]) -> Optional[ET.Element]:
    """
    Retorna o primeiro subelemento que exista dentre os caminhos informados.
    Útil porque o XML da NF-e pode ter namespaces ou variações de tag.
    """

    for candidate in candidates:
        found = element.find(candidate)
        if found is not None:
            return found
    return None


def _get_text(element: Optional[ET.Element]) -> Optional[str]:
    """Extrai o texto de uma tag, retornando None se a tag não existe."""

    if element is None or element.text is None:
        return None
    return element.text.strip() or None


def _to_decimal(value: Optional[str]) -> Optional[Decimal]:
    """
    Converte string numérica do XML para Decimal.
    Retorna None se não houver valor ou se estiver vazio.
    """

    if value is None:
        return None
    value = value.strip()
    return Decimal(value) if value else None


def _parse_datetime(text: Optional[str]) -> Optional[datetime]:
    """
    Converte valores de data/hora da NF-e em datetime.
    Suporta tanto o formato completo (AAA-MM-DDTHH:MM:SS-03:00) quanto apenas data.
    """

    if text is None:
        return None
    text = text.strip()
    if not text:
        return None

    # NF-e costuma vir com timezone, usamos fromisoformat que entende o sufixo -03:00.
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        # Caso venha apenas a data (sem hora), tentamos só a parte de data.
        try:
            return datetime.fromisoformat(text + "T00:00:00")
        except ValueError:
            return None


# Funções principais ---------------------------------------------------------

def importar_xml_nfe(caminho_arquivo: str, db_sessao: Session, empresa: Empresa) -> NotaFiscal:
    """
    Lê um arquivo XML de NF-e (modelo 55) e persiste NotaFiscal + Itens no banco.

    Parâmetros:
    - caminho_arquivo: caminho para o arquivo XML.
    - db_sessao: sessão SQLAlchemy já aberta.
    - empresa: instância de Empresa à qual a nota pertence.

    Retorna a instância de NotaFiscal criada.
    """

    xml_path = Path(caminho_arquivo)
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # As NF-e costumam vir embrulhadas em <nfeProc> ou diretamente em <NFe>.
    nfe = _find_first(root, ["NFe", "./NFe", "{http://www.portalfiscal.inf.br/nfe}NFe"])
    if nfe is None and root.tag.endswith("NFe"):
        nfe = root
    if nfe is None:
        raise ValueError("Arquivo XML não contém tag NFe válida")

    inf_nfe = _find_first(
        nfe,
        [
            "infNFe",
            "./infNFe",
            "{http://www.portalfiscal.inf.br/nfe}infNFe",
        ],
    )
    if inf_nfe is None:
        raise ValueError("Tag infNFe não encontrada no XML")

    # Chave da nota fica no atributo Id da tag infNFe, normalmente "NFe<chave>".
    chave_atributo = inf_nfe.attrib.get("Id")
    chave = chave_atributo[3:] if chave_atributo and chave_atributo.startswith("NFe") else chave_atributo

    ide = _find_first(inf_nfe, ["ide", "{http://www.portalfiscal.inf.br/nfe}ide"])
    emit = _find_first(inf_nfe, ["emit", "{http://www.portalfiscal.inf.br/nfe}emit"])
    dest = _find_first(inf_nfe, ["dest", "{http://www.portalfiscal.inf.br/nfe}dest"])

    numero = _get_text(_find_first(ide, ["nNF", "{http://www.portalfiscal.inf.br/nfe}nNF"])) if ide is not None else None
    serie = _get_text(_find_first(ide, ["serie", "{http://www.portalfiscal.inf.br/nfe}serie"])) if ide is not None else None
    data_emissao = _parse_datetime(
        _get_text(
            _find_first(
                ide,
                ["dhEmi", "dEmi", "{http://www.portalfiscal.inf.br/nfe}dhEmi", "{http://www.portalfiscal.inf.br/nfe}dEmi"],
            )
        )
    ) if ide is not None else None
    data_saida = _parse_datetime(
        _get_text(
            _find_first(
                ide,
                ["dhSaiEnt", "dSaiEnt", "{http://www.portalfiscal.inf.br/nfe}dhSaiEnt", "{http://www.portalfiscal.inf.br/nfe}dSaiEnt"],
            )
        )
    ) if ide is not None else None
    modelo = _get_text(_find_first(ide, ["mod", "{http://www.portalfiscal.inf.br/nfe}mod"])) if ide is not None else None
    tp_nf = _get_text(_find_first(ide, ["tpNF", "{http://www.portalfiscal.inf.br/nfe}tpNF"])) if ide is not None else None
    tipo_operacao = "saida" if tp_nf == "1" else "entrada"

    cnpj_emitente = _get_text(_find_first(emit, ["CNPJ", "{http://www.portalfiscal.inf.br/nfe}CNPJ"])) if emit is not None else None
    cnpj_destinatario = _get_text(
        _find_first(dest, ["CNPJ", "CPF", "{http://www.portalfiscal.inf.br/nfe}CNPJ", "{http://www.portalfiscal.inf.br/nfe}CPF"])
    ) if dest is not None else None
    uf_destino = _get_text(
        _find_first(dest, ["enderDest/UF", "{http://www.portalfiscal.inf.br/nfe}enderDest/{http://www.portalfiscal.inf.br/nfe}UF"])
    ) if dest is not None else None

    icms_tot = _find_first(
        inf_nfe,
        ["total/ICMSTot", "{http://www.portalfiscal.inf.br/nfe}total/{http://www.portalfiscal.inf.br/nfe}ICMSTot"],
    )
    valor_total = _to_decimal(_get_text(_find_first(icms_tot, ["vNF", "{http://www.portalfiscal.inf.br/nfe}vNF"]))) if icms_tot is not None else None

    nota = NotaFiscal(
        empresa=empresa,
        chave=chave or "",
        numero=numero or "",
        serie=serie or "",
        cnpj_emitente=cnpj_emitente or "",
        cnpj_destinatario=cnpj_destinatario,
        data_emissao=data_emissao or datetime.utcnow(),
        data_saida=data_saida,
        modelo=modelo or "55",
        tipo_operacao=tipo_operacao,
        valor_total=valor_total or Decimal("0"),
        uf_destino=uf_destino,
    )
    db_sessao.add(nota)
    db_sessao.flush()  # garante que nota.id exista para relação com itens

    # Percorre os itens (<det>) da NF-e. Alguns XML vêm com namespace completo, por isso somamos as duas buscas.
    for det in inf_nfe.findall("det") + inf_nfe.findall("{http://www.portalfiscal.inf.br/nfe}det"):
        prod = _find_first(det, ["prod", "{http://www.portalfiscal.inf.br/nfe}prod"])
        if prod is None:
            # Sem tag <prod> não há item para importar.
            continue

        ncm = _get_text(_find_first(prod, ["NCM", "{http://www.portalfiscal.inf.br/nfe}NCM"])) or ""
        cest = _get_text(_find_first(prod, ["CEST", "{http://www.portalfiscal.inf.br/nfe}CEST"]))
        descricao = _get_text(_find_first(prod, ["xProd", "{http://www.portalfiscal.inf.br/nfe}xProd"])) or ""
        cfop = _get_text(_find_first(prod, ["CFOP", "{http://www.portalfiscal.inf.br/nfe}CFOP"])) or ""
        quantidade = _to_decimal(_get_text(_find_first(prod, ["qCom", "{http://www.portalfiscal.inf.br/nfe}qCom"]))) or Decimal("0")
        valor_unitario = _to_decimal(_get_text(_find_first(prod, ["vUnCom", "{http://www.portalfiscal.inf.br/nfe}vUnCom"]))) or Decimal("0")
        valor_total_item = _to_decimal(_get_text(_find_first(prod, ["vProd", "{http://www.portalfiscal.inf.br/nfe}vProd"]))) or Decimal("0")

        # Grupo de PIS: existem variações (PISAliq, PISNT, PISOutr). Pegamos o primeiro grupo e extraímos os campos comuns.
        pis = _find_first(det, ["imposto/PIS", "{http://www.portalfiscal.inf.br/nfe}imposto/{http://www.portalfiscal.inf.br/nfe}PIS"])
        cst_pis = None
        base_pis = None
        valor_pis = None
        if pis is not None:
            pis_group = next(iter(pis), None)  # primeiro filho do grupo PIS
            cst_pis = _get_text(_find_first(pis_group, ["CST", "{http://www.portalfiscal.inf.br/nfe}CST"])) if pis_group is not None else None
            base_pis = _to_decimal(_get_text(_find_first(pis_group, ["vBC", "{http://www.portalfiscal.inf.br/nfe}vBC"]))) if pis_group is not None else None
            valor_pis = _to_decimal(_get_text(_find_first(pis_group, ["vPIS", "{http://www.portalfiscal.inf.br/nfe}vPIS"]))) if pis_group is not None else None

        # Grupo de COFINS: mesma ideia, grupos COFINSAliq, COFINSNT, COFINSOutr, etc.
        cofins = _find_first(
            det,
            ["imposto/COFINS", "{http://www.portalfiscal.inf.br/nfe}imposto/{http://www.portalfiscal.inf.br/nfe}COFINS"],
        )
        cst_cofins = None
        base_cofins = None
        valor_cofins = None
        if cofins is not None:
            cofins_group = next(iter(cofins), None)
            cst_cofins = _get_text(_find_first(cofins_group, ["CST", "{http://www.portalfiscal.inf.br/nfe}CST"])) if cofins_group is not None else None
            base_cofins = _to_decimal(_get_text(_find_first(cofins_group, ["vBC", "{http://www.portalfiscal.inf.br/nfe}vBC"]))) if cofins_group is not None else None
            valor_cofins = _to_decimal(_get_text(_find_first(cofins_group, ["vCOFINS", "{http://www.portalfiscal.inf.br/nfe}vCOFINS"]))) if cofins_group is not None else None

        item = ItemNota(
            nota=nota,
            ncm=ncm,
            cest=cest,
            descricao_produto=descricao,
            cfop=cfop,
            quantidade=quantidade,
            valor_unitario=valor_unitario,
            valor_total=valor_total_item,
            cst_pis=cst_pis or "",
            cst_cofins=cst_cofins or "",
            base_pis=base_pis,
            valor_pis=valor_pis,
            base_cofins=base_cofins,
            valor_cofins=valor_cofins,
        )
        db_sessao.add(item)

    db_sessao.commit()
    db_sessao.refresh(nota)
    return nota


def importar_xml_conteudo(conteudo_xml: str, db_sessao: Session, empresa: Empresa) -> NotaFiscal:
    """
    Versão auxiliar que recebe o conteúdo XML como string (útil para uploads em memória).
    """

    # Carregamos o XML a partir da string e o escrevemos temporariamente para
    # reaproveitar a lógica principal baseada em caminho de arquivo.
    temp_path = Path("/tmp/nfe_temp.xml")
    temp_path.write_text(conteudo_xml, encoding="utf-8")
    try:
        return importar_xml_nfe(str(temp_path), db_sessao, empresa)
    finally:
        if temp_path.exists():
            temp_path.unlink()


# Demonstração simples -------------------------------------------------------

def demo_importar_pasta_xml(caminho_pasta: str, db_sessao: Session, empresa: Empresa) -> None:
    """
    Percorre todos os arquivos .xml da pasta informada e importa cada um.
    Exemplo de uso rápido em um script:

    >>> from app.database import SessionLocal
    >>> from app.models import Empresa
    >>> from app.services.xml_parser import demo_importar_pasta_xml
    >>> db = SessionLocal()
    >>> empresa = db.query(Empresa).first()
    >>> demo_importar_pasta_xml("./xmls", db, empresa)
    """

    pasta = Path(caminho_pasta)
    for xml_file in pasta.glob("*.xml"):
        importar_xml_nfe(str(xml_file), db_sessao, empresa)
