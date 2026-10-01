"""Logique métier des utilisateurs — séance 5."""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.depots import utilisateurs as depot
from app.exceptions import EmailDejaUtilise, IdentifiantsInvalides, JetonInvalide
from app.modeles.utilisateurs import UtilisateurCreation
from app.securite import creer_jeton, decoder_jeton, hacher, verifier_a_temps_constant
from app.tables.utilisateurs import Role, Utilisateur


def inscrire(session: Session, entree: UtilisateurCreation) -> Utilisateur:
    """À l'inscription, on est bien obligé de dire qu'un email est déjà pris —
    c'est une fuite d'information assumée, inévitable sur ce formulaire.
    À la connexion, en revanche, on ne révèle jamais rien."""
    if depot.par_email(session, entree.email) is not None:
        raise EmailDejaUtilise(entree.email)

    utilisateur = Utilisateur(
        email=entree.email.lower(),
        empreinte=hacher(entree.mot_de_passe),
        role=Role.lecteur,
    )

    try:
        return depot.enregistrer(session, utilisateur)
    except IntegrityError:
        session.rollback()
        raise EmailDejaUtilise(entree.email) from None


def authentifier(session: Session, email: str, mot_de_passe: str) -> Utilisateur:
    """Email inconnu, mot de passe faux, compte désactivé : même erreur.

    Distinguer les cas permettrait d'énumérer les comptes inscrits, et dire
    « votre compte est désactivé » confirmerait que le mot de passe est bon.
    """
    utilisateur = depot.par_email(session, email)
    empreinte = utilisateur.empreinte if utilisateur else None

    if not verifier_a_temps_constant(mot_de_passe, empreinte):
        raise IdentifiantsInvalides()

    assert utilisateur is not None  # garanti par la vérification ci-dessus
    if not utilisateur.actif:
        raise IdentifiantsInvalides()

    utilisateur.derniere_connexion = datetime.now(timezone.utc)
    session.commit()
    return utilisateur


def jeton_pour(utilisateur: Utilisateur) -> str:
    """Aucune donnée sensible dans la charge utile : un JWT est lisible par tous."""
    return creer_jeton({"sub": str(utilisateur.id), "role": utilisateur.role.value})


def utilisateur_du_jeton(session: Session, jeton: str) -> Utilisateur:
    """Vérifie le jeton *puis* l'utilisateur en base.

    Le jeton reflète l'état au moment de l'émission. Entre-temps, le compte a
    pu être désactivé ou supprimé : c'est la requête en base qui permet de
    couper l'accès sans attendre l'expiration.
    """
    charge = decoder_jeton(jeton)
    if charge is None:
        raise JetonInvalide()

    identifiant = charge.get("sub")
    if identifiant is None:
        raise JetonInvalide()

    try:
        utilisateur = depot.par_id(session, int(identifiant))
    except (TypeError, ValueError):
        raise JetonInvalide() from None

    if utilisateur is None or not utilisateur.actif:
        raise JetonInvalide()

    return utilisateur


def utilisateur_optionnel_du_jeton(session: Session, jeton: str | None) -> Utilisateur | None:
    """Pour une route publique qui affiche davantage à un utilisateur connecté."""
    if not jeton:
        return None
    try:
        return utilisateur_du_jeton(session, jeton)
    except JetonInvalide:
        return None


def changer_role(session: Session, utilisateur: Utilisateur, role: Role) -> Utilisateur:
    utilisateur.role = role
    session.commit()
    session.refresh(utilisateur)
    return utilisateur


def definir_activation(
    session: Session, utilisateur: Utilisateur, actif: bool
) -> Utilisateur:
    utilisateur.actif = actif
    session.commit()
    session.refresh(utilisateur)
    return utilisateur
