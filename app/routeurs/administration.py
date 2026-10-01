"""Routes d'administration — séance 7, exercice 2.4.

La dépendance est déclarée **au niveau du routeur** : elle s'applique à toutes
ses routes, présentes et futures. Un développeur qui ajoute une route ici ne
peut pas oublier la protection.

Ce qui est appliqué globalement ne peut pas être omis individuellement.
"""

from fastapi import APIRouter, Depends, Query, status

from app.dependances import PaginationDep, SessionDep, administrateur
from app.depots import jeux as depot_jeux
from app.depots import utilisateurs as depot_utilisateurs
from app.journalisation import logger
from app.modeles.commun import REPONSES_DROITS, Message, Page
from app.modeles.utilisateurs import ChangementRole, UtilisateurSortie
from app.services import jeux as service_jeux
from app.services import utilisateurs as service_utilisateurs

routeur = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(administrateur)],
    responses=REPONSES_DROITS,
)


@routeur.get("/utilisateurs", response_model=Page[UtilisateurSortie], summary="Lister les comptes")
def lister_utilisateurs(session: SessionDep, page: PaginationDep):
    elements = depot_utilisateurs.lister(session, page.saut, page.limite)
    total = depot_utilisateurs.compter(session)
    return Page(elements=elements, total=total, saut=page.saut, limite=page.limite)


@routeur.patch(
    "/utilisateurs/{utilisateur_id}/role",
    response_model=UtilisateurSortie,
    summary="Changer le rôle d'un compte",
)
def changer_role(session: SessionDep, utilisateur_id: int, entree: ChangementRole):
    from app.exceptions import ErreurMetier

    cible = depot_utilisateurs.par_id(session, utilisateur_id)
    if cible is None:
        raise ErreurMetier("UTILISATEUR_INTROUVABLE", "Compte introuvable", 404)

    logger.info("Rôle de l'utilisateur %s changé en %s", utilisateur_id, entree.role.value)
    return service_utilisateurs.changer_role(session, cible, entree.role)


@routeur.patch(
    "/utilisateurs/{utilisateur_id}/activation",
    response_model=UtilisateurSortie,
    summary="Activer ou désactiver un compte",
)
def changer_activation(session: SessionDep, utilisateur_id: int, actif: bool):
    """Désactiver un compte coupe l'accès immédiatement, sans attendre
    l'expiration de son jeton : c'est la vérification en base à chaque requête
    qui le permet."""
    from app.exceptions import ErreurMetier

    cible = depot_utilisateurs.par_id(session, utilisateur_id)
    if cible is None:
        raise ErreurMetier("UTILISATEUR_INTROUVABLE", "Compte introuvable", 404)

    return service_utilisateurs.definir_activation(session, cible, actif)


@routeur.delete("/jeux", response_model=Message, summary="Supprimer les jeux d'un genre")
def supprimer_par_genre(session: SessionDep, genre: str | None = Query(default=None)):
    """Sans le paramètre `genre`, l'opération est refusée avec un 400 : une
    opération destructrice doit exiger une intention explicite."""
    supprimes = service_jeux.supprimer_par_genre(session, genre)
    logger.warning("%d jeux supprimés pour le genre %s", supprimes, genre)
    return Message(message=f"{supprimes} jeu(x) supprimé(s)")


@routeur.post(
    "/reinitialiser",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Réinitialiser le catalogue",
)
def reinitialiser(session: SessionDep):
    """Très pratique en développement, dangereuse en production.

    Une route capable de détruire toutes les données ne reste jamais ouverte :
    c'est pourquoi elle vit dans le routeur protégé.
    """
    from app.donnees_initiales import JEUX_INITIAUX
    from app.modeles.jeux import JeuCreation

    supprimes = depot_jeux.vider(session)

    administrateur_courant = depot_utilisateurs.lister(session, limite=1)
    auteur = administrateur_courant[0] if administrateur_courant else None

    crees = 0
    if auteur is not None:
        for donnees in JEUX_INITIAUX:
            service_jeux.creer(session, JeuCreation(**donnees), auteur)
            crees += 1

    logger.warning("Catalogue réinitialisé : %d supprimés, %d créés", supprimes, crees)
    return Message(message=f"Données réinitialisées : {crees} jeu(x)")
