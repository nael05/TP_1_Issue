"""Profil et ressources de l'utilisateur courant — séance 5."""

from fastapi import APIRouter

from app.dependances import PaginationDep, SessionDep, UtilisateurDep
from app.modeles.commun import REPONSES_AUTHENTIFICATION, Page
from app.modeles.jeux import JeuResume
from app.modeles.utilisateurs import UtilisateurSortie
from app.services import jeux as service_jeux

routeur = APIRouter(prefix="/moi", tags=["Mon compte"])


@routeur.get(
    "",
    response_model=UtilisateurSortie,
    summary="Mon profil",
    responses=REPONSES_AUTHENTIFICATION,
)
def lire_profil(utilisateur: UtilisateurDep):
    return utilisateur


@routeur.get(
    "/jeux",
    response_model=Page[JeuResume],
    summary="Mes jeux",
    responses=REPONSES_AUTHENTIFICATION,
)
def mes_jeux(session: SessionDep, utilisateur: UtilisateurDep, page: PaginationDep):
    """Le filtre porte sur l'utilisateur du jeton, jamais sur un paramètre.

    Une route `/utilisateurs/{id}/jeux` exigerait une vérification
    supplémentaire ; `/moi/...` évite le problème par construction.
    """
    elements, total = service_jeux.lister(
        session,
        proprietaire_id=utilisateur.id,
        saut=page.saut,
        limite=page.limite,
    )
    return Page(elements=elements, total=total, saut=page.saut, limite=page.limite)
