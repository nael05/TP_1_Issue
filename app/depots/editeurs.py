"""Accès aux données des éditeurs — séance 4, partie 6."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.tables.editeurs import Editeur


def lister(session: Session, saut: int = 0, limite: int = 50) -> list[Editeur]:
    requete = select(Editeur).order_by(Editeur.nom).offset(saut).limit(limite)
    return list(session.scalars(requete).all())


def compter(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Editeur)) or 0


def par_id(session: Session, editeur_id: int) -> Editeur | None:
    return session.get(Editeur, editeur_id)


def par_id_avec_jeux(session: Session, editeur_id: int) -> Editeur | None:
    requete = (
        select(Editeur)
        .where(Editeur.id == editeur_id)
        .options(selectinload(Editeur.jeux))
    )
    return session.scalar(requete)


def par_nom(session: Session, nom: str) -> Editeur | None:
    return session.scalar(select(Editeur).where(func.lower(Editeur.nom) == nom.lower()))


def enregistrer(session: Session, editeur: Editeur) -> Editeur:
    session.add(editeur)
    session.commit()
    session.refresh(editeur)
    return editeur


def supprimer(session: Session, editeur: Editeur) -> None:
    session.delete(editeur)
    session.commit()
