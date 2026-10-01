"""Accès aux données des utilisateurs — séance 5."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.tables.utilisateurs import Utilisateur


def par_id(session: Session, utilisateur_id: int) -> Utilisateur | None:
    return session.get(Utilisateur, utilisateur_id)


def par_email(session: Session, email: str) -> Utilisateur | None:
    return session.scalar(
        select(Utilisateur).where(func.lower(Utilisateur.email) == email.lower())
    )


def lister(session: Session, saut: int = 0, limite: int = 50) -> list[Utilisateur]:
    requete = select(Utilisateur).order_by(Utilisateur.id).offset(saut).limit(limite)
    return list(session.scalars(requete).all())


def compter(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Utilisateur)) or 0


def enregistrer(session: Session, utilisateur: Utilisateur) -> Utilisateur:
    session.add(utilisateur)
    session.commit()
    session.refresh(utilisateur)
    return utilisateur
