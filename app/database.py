"""
Módulo de conexão com o banco de dados SQLite usando SQLAlchemy.
Aqui criamos o engine, a classe Base e utilitários para gerenciar sessões.
"""

from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Caminho do arquivo de banco de dados SQLite.
# Por padrão, será criado dentro da pasta ./data/ com o nome auditoria_monofasico.db
# Exemplo de URL para o SQLAlchemy: sqlite:///./data/auditoria_monofasico.db
DATABASE_URL = "sqlite:///./data/auditoria_monofasico.db"

# Garante que a pasta de dados exista antes de criar/conectar ao banco.
os.makedirs("data", exist_ok=True)

# O engine é a "ponte" entre o SQLAlchemy e o banco de dados.
# Ele sabe como se conectar e enviar comandos SQL para o SQLite.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Necessário para uso em apps web com SQLite
)

# A classe Base é a classe mãe de todos os modelos (tabelas).
# Todo modelo deve herdar de Base para que o SQLAlchemy saiba mapear para a tabela.
Base = declarative_base()

# sessionmaker cria uma fábrica de sessões. Cada sessão representa uma conexão de trabalho
# com o banco (abrir transação, salvar, consultar, etc.).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_all_tables() -> None:
    """
    Cria todas as tabelas no banco de dados conforme os modelos declarados.
    Use esta função na inicialização da aplicação para garantir que o schema exista.
    """
    # Importamos os modelos aqui para garantir que o SQLAlchemy conheça todas
    # as classes antes de tentar criar as tabelas. Sem esse import, o metadata
    # estaria vazio e nenhuma tabela seria gerada.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependência padrão do FastAPI para obter uma sessão de banco de dados.
    Abre uma sessão, entrega para quem chamou (via yield) e fecha ao final.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
