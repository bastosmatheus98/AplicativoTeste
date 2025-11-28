"""
Modelos (tabelas) do banco de dados para auditoria do regime monofásico.
Cada classe representa uma tabela no SQLite usando o SQLAlchemy ORM.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Empresa(Base):
    """
    Representa a empresa auditada. É o "cadastro" básico.
    Cada empresa pode ter várias notas fiscais, competências PGDAS e auditorias.
    """

    __tablename__ = "empresas"

    id: int = Column(Integer, primary_key=True, index=True)
    cnpj: str = Column(String(18), unique=True, nullable=False, index=True)
    razao_social: str = Column(String(255), nullable=False)
    nome_fantasia: Optional[str] = Column(String(255), nullable=True)
    cnae_principal: Optional[str] = Column(String(20), nullable=True)
    data_inicio_simpl: Optional[date] = Column(Date, nullable=True)
    data_fim_simpl: Optional[date] = Column(Date, nullable=True)

    # Relacionamentos: uma empresa possui várias notas, competências e auditorias.
    notas_fiscais: List["NotaFiscal"] = relationship(
        "NotaFiscal", back_populates="empresa", cascade="all, delete-orphan"
    )
    competencias_pgdas: List["CompetenciaPGDAS"] = relationship(
        "CompetenciaPGDAS", back_populates="empresa", cascade="all, delete-orphan"
    )
    resultados_auditoria: List["ResultadoAuditoria"] = relationship(
        "ResultadoAuditoria", back_populates="empresa", cascade="all, delete-orphan"
    )


class NotaFiscal(Base):
    """
    Cabeçalho da NF-e de saída. Guarda dados gerais da nota e se relaciona com os itens.
    """

    __tablename__ = "notas_fiscais"

    id: int = Column(Integer, primary_key=True, index=True)
    empresa_id: int = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    chave: str = Column(String(60), unique=True, nullable=False, index=True)
    numero: str = Column(String(20), nullable=False)
    serie: str = Column(String(10), nullable=False)
    cnpj_emitente: str = Column(String(18), nullable=False)
    cnpj_destinatario: Optional[str] = Column(String(18), nullable=True)
    data_emissao: datetime = Column(DateTime, nullable=False)
    data_saida: Optional[datetime] = Column(DateTime, nullable=True)
    modelo: str = Column(String(5), nullable=False, default="55")
    tipo_operacao: str = Column(String(20), nullable=False, default="saida")
    valor_total: float = Column(Numeric(14, 2), nullable=False)
    uf_destino: Optional[str] = Column(String(2), nullable=True)

    # Relacionamentos: uma nota possui vários itens e pertence a uma empresa.
    empresa: "Empresa" = relationship("Empresa", back_populates="notas_fiscais")
    itens: List["ItemNota"] = relationship(
        "ItemNota", back_populates="nota", cascade="all, delete-orphan"
    )


class ItemNota(Base):
    """
    Representa cada item de produto/mercadoria dentro de uma NF-e.
    É aqui que estão NCM, CFOP, CST e valores específicos de PIS/COFINS.
    """

    __tablename__ = "itens_nota"

    id: int = Column(Integer, primary_key=True, index=True)
    nota_id: int = Column(Integer, ForeignKey("notas_fiscais.id"), nullable=False, index=True)
    ncm: str = Column(String(20), nullable=False)
    cest: Optional[str] = Column(String(20), nullable=True)
    descricao_produto: str = Column(String(255), nullable=False)
    cfop: str = Column(String(10), nullable=False)
    quantidade: float = Column(Numeric(14, 4), nullable=False)
    valor_unitario: float = Column(Numeric(14, 4), nullable=False)
    valor_total: float = Column(Numeric(14, 2), nullable=False)
    cst_pis: str = Column(String(5), nullable=False)
    cst_cofins: str = Column(String(5), nullable=False)
    base_pis: Optional[float] = Column(Numeric(14, 2), nullable=True)
    valor_pis: Optional[float] = Column(Numeric(14, 2), nullable=True)
    base_cofins: Optional[float] = Column(Numeric(14, 2), nullable=True)
    valor_cofins: Optional[float] = Column(Numeric(14, 2), nullable=True)
    eh_monofasico: bool = Column(Boolean, default=False, nullable=False)
    eh_inconsistente: bool = Column(Boolean, default=False, nullable=False)

    # Relacionamento: cada item pertence a uma nota fiscal.
    nota: "NotaFiscal" = relationship("NotaFiscal", back_populates="itens")


class CompetenciaPGDAS(Base):
    """
    Representa as informações da PGDAS-D para uma competência (mês/ano) de uma empresa.
    Guarda receitas declaradas e alíquotas aplicáveis.
    """

    __tablename__ = "competencias_pgdas"

    id: int = Column(Integer, primary_key=True, index=True)
    empresa_id: int = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    ano_mes: str = Column(String(7), nullable=False, index=True)  # Formato AAAA-MM
    anexo: str = Column(String(5), nullable=False)
    receita_bruta_total: float = Column(Numeric(16, 2), nullable=False)
    receita_monofasica_declarada: float = Column(Numeric(16, 2), nullable=False)
    receita_substituicao_tributaria: Optional[float] = Column(Numeric(16, 2), nullable=True)
    receita_outras_exclusoes: Optional[float] = Column(Numeric(16, 2), nullable=True)
    receita_bruta_12m: float = Column(Numeric(16, 2), nullable=False)
    aliquota_nominal: Optional[float] = Column(Numeric(6, 4), nullable=True)
    parcela_a_deduzir: Optional[float] = Column(Numeric(16, 2), nullable=True)
    aliquota_efetiva: Optional[float] = Column(Numeric(6, 4), nullable=True)

    # Relacionamentos
    empresa: "Empresa" = relationship("Empresa", back_populates="competencias_pgdas")
    auditorias: List["ResultadoAuditoria"] = relationship(
        "ResultadoAuditoria", back_populates="competencia", cascade="all, delete-orphan"
    )


class NCMMonofasico(Base):
    """
    Tabela de referência com NCMs sujeitos ao regime monofásico de PIS/COFINS.
    Permite parametrizar vigência e setor.
    """

    __tablename__ = "ncm_monofasicos"

    id: int = Column(Integer, primary_key=True, index=True)
    ncm: str = Column(String(10), nullable=False, index=True)
    descricao: str = Column(String(255), nullable=False)
    setor: str = Column(String(50), nullable=False)
    data_inicio_vigencia: date = Column(Date, nullable=False)
    data_fim_vigencia: Optional[date] = Column(Date, nullable=True)
    flag_monofasico: bool = Column(Boolean, default=True, nullable=False)


class AnexoAliquota(Base):
    """
    Tabela de partilha do Simples Nacional por anexo e faixa de receita.
    Guarda alíquota nominal, parcela a deduzir e percentuais de PIS/COFINS.
    """

    __tablename__ = "anexos_aliquotas"

    id: int = Column(Integer, primary_key=True, index=True)
    anexo: str = Column(String(5), nullable=False, index=True)
    faixa: int = Column(Integer, nullable=False)
    receita_bruta_min: float = Column(Numeric(16, 2), nullable=False)
    receita_bruta_max: float = Column(Numeric(16, 2), nullable=False)
    aliquota_nominal: float = Column(Numeric(6, 4), nullable=False)
    parcela_a_deduzir: float = Column(Numeric(16, 2), nullable=False)
    percentual_pis: float = Column(Numeric(6, 4), nullable=False)
    percentual_cofins: float = Column(Numeric(6, 4), nullable=False)


class ResultadoAuditoria(Base):
    """
    Resumo da auditoria por competência. Guarda bases comparadas e valores estimados
    de PIS/COFINS pagos a maior ou a menor.
    """

    __tablename__ = "resultados_auditoria"

    id: int = Column(Integer, primary_key=True, index=True)
    empresa_id: int = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    competencia_id: int = Column(
        Integer, ForeignKey("competencias_pgdas.id"), nullable=False, index=True
    )
    base_monofasica_xml: float = Column(Numeric(16, 2), nullable=False)
    base_monofasica_pgdas: float = Column(Numeric(16, 2), nullable=False)
    diferenca_base: float = Column(Numeric(16, 2), nullable=False)
    pis_indev: Optional[float] = Column(Numeric(16, 2), nullable=True)
    cofins_indev: Optional[float] = Column(Numeric(16, 2), nullable=True)
    total_indev: Optional[float] = Column(Numeric(16, 2), nullable=True)
    detalhes_json: Optional[str] = Column(Text, nullable=True)

    # Relacionamentos
    empresa: "Empresa" = relationship("Empresa", back_populates="resultados_auditoria")
    competencia: "CompetenciaPGDAS" = relationship(
        "CompetenciaPGDAS", back_populates="auditorias"
    )
