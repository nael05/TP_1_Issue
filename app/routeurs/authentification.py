"""Inscription, connexion, déconnexion — séance 5, partie 3."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.dependances import SessionDep, UtilisateurDep
from app.exceptions import ErreurMetier
from app.journalisation import logger
from app.modeles.commun import ErreurReponse, Jeton, Message
from app.modeles.utilisateurs import UtilisateurCreation, UtilisateurSortie
from app.services import tentatives
from app.services import utilisateurs as service

routeur = APIRouter(tags=["Authentification"])


@routeur.post(
    "/inscription",
    response_model=UtilisateurSortie,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte",
    responses={409: {"model": ErreurReponse, "description": "Email déjà utilisé"}},
)
def inscription(session: SessionDep, entree: UtilisateurCreation):
    """La réponse ne contient jamais l'empreinte : `UtilisateurSortie` ne la
    déclare pas, donc FastAPI la retire."""
    utilisateur = service.inscrire(session, entree)
    logger.info("Inscription de l'utilisateur %s", utilisateur.id)
    return utilisateur


@routeur.post(
    "/connexion",
    response_model=Jeton,
    summary="Obtenir un jeton",
    description=(
        "Formulaire OAuth2 : les champs s'appellent `username` et `password`. "
        "On met une adresse email dans `username` — c'est la norme."
    ),
    responses={
        401: {"model": ErreurReponse, "description": "Identifiants incorrects"},
        429: {"model": ErreurReponse, "description": "Trop de tentatives"},
    },
)
def connexion(
    session: SessionDep, formulaire: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    email = formulaire.username.lower()
    tentatives.verifier(email)

    try:
        utilisateur = service.authentifier(session, email, formulaire.password)
    except ErreurMetier:
        tentatives.enregistrer_echec(email)
        # L'email sur un échec : acceptable, et utile pour détecter une
        # attaque. Le mot de passe, même incorrect : jamais.
        logger.warning("Échec de connexion pour l'email %s", email)
        raise

    tentatives.reinitialiser(email)
    logger.info("Connexion réussie pour l'utilisateur %s", utilisateur.id)

    return Jeton(access_token=service.jeton_pour(utilisateur))


@routeur.post("/deconnexion", response_model=Message, summary="Se déconnecter")
def deconnexion(utilisateur: UtilisateurDep):
    """Cette route **ne peut pas** invalider le jeton : il est autoporteur, le
    serveur ne le stocke nulle part.

    Trois réponses possibles : le client oublie le jeton ; une liste de
    révocation, qui rétablit un état côté serveur ; ou des jetons courts avec
    rafraîchissement, le compromis le plus répandu. Ce qui compte est de
    comprendre pourquoi la question se pose.
    """
    logger.info("Déconnexion de l'utilisateur %s", utilisateur.id)
    return Message(message="Déconnecté. Supprimez le jeton côté client.")
