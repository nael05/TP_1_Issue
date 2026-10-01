"""Dépendances partagées — séances 4 et 5.

Le système de dépendances sert à tout ce qui doit être préparé avant une
route : une session, l'utilisateur authentifié, la pagination, un droit.
Elles s'imbriquent : `administrateur` utilise `utilisateur_courant`, qui
utilise la session et le schéma OAuth2.
"""

from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.base_donnees import obtenir_session
from app.exceptions import DroitInsuffisant, ErreurMetier
from app.services import utilisateurs as service
from app.tables.utilisateurs import Role, Utilisateur

# --- Session ----------------------------------------------------------------

SessionDep = Annotated[Session, Depends(obtenir_session)]


# --- Pagination -------------------------------------------------------------


class Pagination:
    """Les paramètres de requête communs, déclarés une fois.

    La borne supérieure sur `limite` est une protection : sans elle, un client
    peut demander un million d'éléments.
    """

    def __init__(self, saut: int = 0, limite: int = 20):
        self.saut = max(0, saut)
        self.limite = min(max(1, limite), 100)


PaginationDep = Annotated[Pagination, Depends()]


# --- Authentification -------------------------------------------------------

# `tokenUrl` fait apparaître le bouton « Authorize » dans Swagger.
schema_oauth = OAuth2PasswordBearer(tokenUrl="/api/v1/connexion")
schema_oauth_optionnel = OAuth2PasswordBearer(
    tokenUrl="/api/v1/connexion", auto_error=False
)


def utilisateur_courant(
    session: SessionDep, jeton: Annotated[str, Depends(schema_oauth)]
) -> Utilisateur:
    return service.utilisateur_du_jeton(session, jeton)


UtilisateurDep = Annotated[Utilisateur, Depends(utilisateur_courant)]


def utilisateur_optionnel(
    session: SessionDep,
    jeton: Annotated[str | None, Depends(schema_oauth_optionnel)] = None,
) -> Utilisateur | None:
    """`auto_error=False` : pas de jeton, pas d'erreur — simplement `None`."""
    return service.utilisateur_optionnel_du_jeton(session, jeton)


UtilisateurOptionnelDep = Annotated[Utilisateur | None, Depends(utilisateur_optionnel)]


# --- Autorisation -----------------------------------------------------------


def administrateur(utilisateur: UtilisateurDep) -> Utilisateur:
    if not utilisateur.est_admin:
        raise DroitInsuffisant("Droits d'administrateur requis")
    return utilisateur


AdminDep = Annotated[Utilisateur, Depends(administrateur)]


def exiger_role(*roles_autorises: Role):
    """Une *fabrique* de dépendances : elle renvoie la fonction que FastAPI
    appellera. Évite d'écrire une dépendance par rôle."""

    def dependance(utilisateur: UtilisateurDep) -> Utilisateur:
        if utilisateur.role not in roles_autorises:
            attendus = ", ".join(role.value for role in roles_autorises)
            raise DroitInsuffisant(f"Rôle requis : {attendus}")
        return utilisateur

    return dependance


# --- Divers -----------------------------------------------------------------


def verifier_client(
    x_client_id: Annotated[str | None, Header()] = None,
) -> str:
    """Séance 4, exercice 3.6 : une dépendance qui inspecte un en-tête.

    `x_client_id` correspond à l'en-tête `X-Client-Id` : FastAPI convertit les
    tirets bas en tirets. C'est exactement le mécanisme de l'authentification,
    avec un identifiant de client au lieu d'un jeton.
    """
    if not x_client_id:
        raise ErreurMetier(
            "EN_TETE_MANQUANT", "En-tête X-Client-Id obligatoire", 400
        )
    return x_client_id
