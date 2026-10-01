"""Routes des jeux — séance 7, partie 2.

Une route fait trois choses : recevoir, déléguer, répondre. Aucun filtrage,
aucun calcul, aucune règle métier ici.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.dependances import PaginationDep, SessionDep, UtilisateurDep
from app.journalisation import logger
from app.modeles.commun import REPONSES_DROITS, ErreurReponse, Page
from app.modeles.jeux import (
    Genre,
    JeuCreation,
    JeuMiseAJour,
    JeuResume,
    JeuSortie,
    JeuStatistiques,
    ModificationSortie,
    NoteEntree,
    TriJeu,
    Voisins,
)
from app.services import jeux as service

routeur = APIRouter(prefix="/jeux", tags=["Jeux"])


def journaliser_creation(jeu_id: int, utilisateur_id: int) -> None:
    """Tâche d'arrière-plan : elle s'exécute après l'envoi de la réponse."""
    logger.info("Jeu %s créé par l'utilisateur %s", jeu_id, utilisateur_id)


# --- Lecture ----------------------------------------------------------------


@routeur.get(
    "",
    response_model=Page[JeuResume],
    summary="Lister les jeux",
    description="Filtre, trie et pagine le catalogue. Tous les filtres sont cumulables.",
)
def lister(
    session: SessionDep,
    page: PaginationDep,
    genre: Genre | None = None,
    note_min: Annotated[int, Query(ge=0, le=10)] = 0,
    recherche: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    tri: TriJeu = TriJeu.titre,
):
    elements, total = service.lister(
        session,
        genre=genre.value if genre else None,
        note_min=note_min,
        recherche=recherche,
        tri=tri.value,
        saut=page.saut,
        limite=page.limite,
    )
    return Page(elements=elements, total=total, saut=page.saut, limite=page.limite)


@routeur.get("/statistiques", response_model=JeuStatistiques, summary="Statistiques")
def statistiques(session: SessionDep):
    """Agrégation calculée en SQL, pas en Python : une seule ligne transite."""
    return service.statistiques(session)


@routeur.get(
    "/{jeu_id}",
    response_model=JeuSortie,
    summary="Lire un jeu",
    responses={
        404: {"model": ErreurReponse, "description": "Jeu introuvable"},
        422: {"description": "Identifiant invalide"},
    },
)
def lire(session: SessionDep, jeu_id: int):
    return service.trouver(session, jeu_id)


@routeur.get(
    "/{jeu_id}/similaires",
    response_model=list[JeuResume],
    summary="Jeux du même genre",
    responses={404: {"model": ErreurReponse, "description": "Jeu introuvable"}},
)
def lister_similaires(session: SessionDep, jeu_id: int):
    """Une liste vide n'est pas une erreur : le 404 porte sur le jeu demandé."""
    return service.similaires(session, jeu_id)


@routeur.get("/{jeu_id}/voisins", response_model=Voisins, summary="Jeu précédent et suivant")
def lire_voisins(session: SessionDep, jeu_id: int):
    return service.voisins(session, jeu_id)


@routeur.get(
    "/{jeu_id}/historique",
    response_model=list[ModificationSortie],
    summary="Historique des modifications",
)
def lire_historique(session: SessionDep, jeu_id: int):
    return service.historique(session, jeu_id)


@routeur.get("/recommandes", response_model=list[JeuResume], summary="Les mieux notés")
def lister_recommandes(session: SessionDep, note_minimale: Annotated[int, Query(ge=0, le=10)] = 8):
    return service.recommandes(session, note_minimale)


# --- Écriture (authentification requise) ------------------------------------


@routeur.post(
    "",
    response_model=JeuSortie,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un jeu",
    responses={
        **REPONSES_DROITS,
        409: {"model": ErreurReponse, "description": "Titre déjà utilisé"},
    },
)
def creer(
    session: SessionDep,
    entree: JeuCreation,
    utilisateur: UtilisateurDep,
    taches: BackgroundTasks,
):
    """Renvoie l'objet complet : le client ne connaît pas l'identifiant attribué."""
    jeu = service.creer(session, entree, utilisateur)
    taches.add_task(journaliser_creation, jeu.id, utilisateur.id)
    return jeu


@routeur.post(
    "/lot",
    response_model=list[JeuSortie],
    status_code=status.HTTP_201_CREATED,
    summary="Créer plusieurs jeux",
)
def creer_lot(session: SessionDep, entrees: list[JeuCreation], utilisateur: UtilisateurDep):
    return service.creer_lot(session, entrees, utilisateur)


@routeur.put(
    "/{jeu_id}",
    response_model=JeuSortie,
    summary="Remplacer un jeu",
    description="Tous les champs sont obligatoires : un champ omis produit un 422.",
    responses=REPONSES_DROITS,
)
def remplacer(
    session: SessionDep, jeu_id: int, entree: JeuCreation, utilisateur: UtilisateurDep
):
    return service.remplacer(session, jeu_id, entree, utilisateur)


@routeur.patch(
    "/{jeu_id}",
    response_model=JeuSortie,
    summary="Modifier partiellement un jeu",
    description="Seuls les champs envoyés sont modifiés.",
    responses=REPONSES_DROITS,
)
def modifier(
    session: SessionDep, jeu_id: int, entree: JeuMiseAJour, utilisateur: UtilisateurDep
):
    return service.modifier(session, jeu_id, entree, utilisateur)


@routeur.patch(
    "/{jeu_id}/note", response_model=JeuSortie, summary="Modifier uniquement la note"
)
def modifier_note(
    session: SessionDep, jeu_id: int, entree: NoteEntree, utilisateur: UtilisateurDep
):
    return service.modifier_note(session, jeu_id, entree.note, utilisateur)


@routeur.delete(
    "/{jeu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un jeu",
    responses=REPONSES_DROITS,
)
def supprimer(session: SessionDep, jeu_id: int, utilisateur: UtilisateurDep):
    """Le statut 204 interdit tout corps de réponse : on ne renvoie rien."""
    service.supprimer(session, jeu_id, utilisateur)
