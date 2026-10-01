"""Moteur, session et base déclarative — séance 4, partie 2."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import configuration

engine = create_engine(
    configuration.database_url,
    echo=configuration.echo_sql,
    pool_pre_ping=True,
)

SessionLocale = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Base commune à toutes les tables."""


def obtenir_session():
    """Une session par requête HTTP.

    `yield` et non `return` : le `finally` s'exécute après l'envoi de la
    réponse, y compris si la route a levé une exception. Avec `return`, la
    session ne serait jamais fermée et le pool de connexions s'épuiserait.
    """
    session = SessionLocale()
    try:
        yield session
    finally:
        session.close()


def creer_tables() -> None:
    """Suffisant pour ce module. En production : Alembic."""
    from app import tables  # noqa: F401  (enregistre les tables sur Base.metadata)

    Base.metadata.create_all(bind=engine)
