"""Routes des éditeurs — séance 4, partie 6."""

from fastapi import APIRouter, status

from app.dependances import AdminDep, PaginationDep, SessionDep
from app.modeles.commun import REPONSES_DROITS, ErreurReponse, Page
from app.modeles.jeux import EditeurEntree, EditeurSortie, JeuResume
from app.services import editeurs as service

routeur = APIRouter(prefix="/editeurs", tags=["Éditeurs"])


@routeur.get("", response_model=Page[EditeurSortie], summary="Lister les éditeurs")
def lister(session: SessionDep, page: PaginationDep):
    elements, total = service.lister(session, page.saut, page.limite)
    return Page(elements=elements, total=total, saut=page.saut, limite=page.limite)


@routeur.get(
    "/{editeur_id}",
    response_model=EditeurSortie,
    summary="Lire un éditeur",
    responses={404: {"model": ErreurReponse, "description": "Éditeur introuvable"}},
)
def lire(session: SessionDep, editeur_id: int):
    return service.trouver(session, editeur_id)


@routeur.get(
    "/{editeur_id}/jeux", response_model=list[JeuResume], summary="Les jeux d'un éditeur"
)
def lister_jeux(session: SessionDep, editeur_id: int):
    return service.jeux_de(session, editeur_id)


@routeur.post(
    "",
    response_model=EditeurSortie,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un éditeur",
    responses=REPONSES_DROITS,
)
def creer(session: SessionDep, entree: EditeurEntree, admin: AdminDep):
    return service.creer(session, entree)


@routeur.delete(
    "/{editeur_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un éditeur",
    responses=REPONSES_DROITS,
)
def supprimer(session: SessionDep, editeur_id: int, admin: AdminDep):
    service.supprimer(session, editeur_id)
