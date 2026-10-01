"""Logique métier des jeux — séance 7, partie 1.

Ce module n'importe **ni FastAPI ni HTTPException** : il lève des exceptions
métier, traduites en réponses HTTP par les gestionnaires de `main.py`.

C'est ce qui le rend testable sans serveur et réutilisable depuis un script —
`scripts/importer.py` s'en sert.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.depots import editeurs as depot_editeurs
from app.depots import jeux as depot
from app.exceptions import (
    DroitInsuffisant,
    EditeurIntrouvable,
    JeuIntrouvable,
    ParametreManquant,
    TitreDejaUtilise,
)
from app.modeles.jeux import JeuCreation, JeuMiseAJour
from app.tables.jeux import Jeu
from app.tables.utilisateurs import Utilisateur


def lister(
    session: Session,
    genre: str | None = None,
    note_min: int = 0,
    recherche: str | None = None,
    proprietaire_id: int | None = None,
    tri: str = "titre",
    saut: int = 0,
    limite: int = 20,
) -> tuple[list[Jeu], int]:
    """Renvoie la page demandée *et* le total."""
    elements = depot.lister(
        session, genre, note_min, recherche, proprietaire_id, tri, saut, limite
    )
    total = depot.compter(session, genre, note_min, recherche)
    return elements, total


def trouver(session: Session, jeu_id: int) -> Jeu:
    """Lève au lieu de renvoyer `None` : l'appelant n'a plus à vérifier."""
    jeu = depot.par_id(session, jeu_id)
    if jeu is None:
        raise JeuIntrouvable(jeu_id)
    return jeu


def recommandes(session: Session, note_minimale: int = 8, limite: int = 20) -> list[Jeu]:
    return depot.lister(session, note_min=note_minimale, tri="note", limite=limite)


def genres(session: Session) -> list[str]:
    return depot.genres_distincts(session)


def similaires(session: Session, jeu_id: int) -> list[Jeu]:
    """Le 404 porte sur le jeu demandé, pas sur le résultat.

    Si aucun jeu ne partage le genre, on renvoie une liste vide avec un 200 :
    « la ressource n'existe pas » et « elle existe mais est vide » sont deux
    situations différentes.
    """
    jeu = trouver(session, jeu_id)
    return depot.similaires(session, jeu)


def voisins(session: Session, jeu_id: int) -> dict[str, Jeu | None]:
    """Le précédent et le suivant par identifiant, `None` aux extrémités."""
    identifiants = depot.tous_les_identifiants(session)
    if jeu_id not in identifiants:
        raise JeuIntrouvable(jeu_id)

    index = identifiants.index(jeu_id)
    precedent = depot.par_id(session, identifiants[index - 1]) if index >= 0 else None
    suivant = (
        depot.par_id(session, identifiants[index + 1])
        if index < len(identifiants) - 1
        else None
    )
    return {"precedent": precedent, "suivant": suivant}


def _verifier_editeur(session: Session, editeur_id: int | None) -> None:
    if editeur_id is not None and depot_editeurs.par_id(session, editeur_id) is None:
        raise EditeurIntrouvable(editeur_id)


def _verifier_titre_libre(session: Session, titre: str, sauf_id: int | None = None) -> None:
    """Refuse « Celeste » comme « celeste ».

    Cette vérification ne remplace pas la contrainte d'unicité : entre la
    lecture et l'insertion, une autre requête peut créer le même titre. Elle
    la complète, parce qu'un `UNIQUE` SQL est sensible à la casse et qu'un
    client ne devrait pas avoir à deviner la casse déjà utilisée.

    La garantie reste la contrainte en base, d'où le `try` / `except` autour
    du `commit`.
    """
    existant = depot.par_titre(session, titre)
    if existant is not None and existant.id != sauf_id:
        raise TitreDejaUtilise(titre)


def creer(session: Session, entree: JeuCreation, utilisateur: Utilisateur) -> Jeu:
    """Le propriétaire vient du serveur, jamais du client."""
    _verifier_editeur(session, entree.editeur_id)
    _verifier_titre_libre(session, entree.titre)

    donnees = entree.model_dump()
    donnees["genre"] = entree.genre.value

    jeu = Jeu(**donnees, proprietaire_id=utilisateur.id)

    try:
        return depot.enregistrer(session, jeu)
    except IntegrityError:
        # Le `rollback` est obligatoire : sans lui, la session reste dans un
        # état invalide et toutes les opérations suivantes échouent, souvent
        # loin de la vraie cause.
        session.rollback()
        raise TitreDejaUtilise(entree.titre) from None


def creer_lot(
    session: Session, entrees: list[JeuCreation], utilisateur: Utilisateur
) -> list[Jeu]:
    return [creer(session, entree, utilisateur) for entree in entrees]


def verifier_droit(jeu: Jeu, utilisateur: Utilisateur) -> None:
    """Authentifié ne veut pas dire autorisé.

    Sans cette vérification, n'importe quel utilisateur connecté modifie les
    ressources des autres en changeant l'identifiant dans l'URL — c'est la
    première vulnérabilité du classement OWASP pour les API, et elle ne se voit
    pas en testant avec un seul compte.
    """
    if jeu.proprietaire_id != utilisateur.id and not utilisateur.est_admin:
        raise DroitInsuffisant("Vous ne pouvez modifier que vos propres jeux")


def remplacer(
    session: Session, jeu_id: int, entree: JeuCreation, utilisateur: Utilisateur
) -> Jeu:
    """PUT : tous les champs sont fournis, la ressource est remplacée."""
    jeu = trouver(session, jeu_id)
    verifier_droit(jeu, utilisateur)
    _verifier_editeur(session, entree.editeur_id)

    _verifier_titre_libre(session, entree.titre, sauf_id=jeu.id)

    donnees = entree.model_dump()
    donnees["genre"] = entree.genre.value
    return _appliquer(session, jeu, donnees, utilisateur)


def modifier(
    session: Session, jeu_id: int, entree: JeuMiseAJour, utilisateur: Utilisateur
) -> Jeu:
    """PATCH : `exclude_unset=True` ne conserve que les champs *envoyés*.

    Sans lui, `model_dump()` renverrait aussi les champs valant `None` par
    défaut, et la modification effacerait tout ce que le client n'a pas
    mentionné — sans lever la moindre exception.
    """
    jeu = trouver(session, jeu_id)
    verifier_droit(jeu, utilisateur)

    donnees = entree.model_dump(exclude_unset=True)
    if "editeur_id" in donnees:
        _verifier_editeur(session, donnees["editeur_id"])
    if donnees.get("titre"):
        _verifier_titre_libre(session, donnees["titre"], sauf_id=jeu.id)
    if isinstance(donnees.get("genre"), object) and donnees.get("genre") is not None:
        donnees["genre"] = getattr(donnees["genre"], "value", donnees["genre"])

    return _appliquer(session, jeu, donnees, utilisateur)


def modifier_note(
    session: Session, jeu_id: int, note: int, utilisateur: Utilisateur
) -> Jeu:
    jeu = trouver(session, jeu_id)
    verifier_droit(jeu, utilisateur)
    return _appliquer(session, jeu, {"note": note}, utilisateur)


def _appliquer(
    session: Session, jeu: Jeu, donnees: dict, utilisateur: Utilisateur
) -> Jeu:
    if not donnees:
        # Un PATCH vide ne modifie rien et ne casse rien : le client n'a rien
        # demandé, il n'y a aucune raison de lever une erreur.
        return jeu

    for cle, valeur in donnees.items():
        setattr(jeu, cle, valeur)

    try:
        depot.enregistrer(session, jeu)
    except IntegrityError:
        session.rollback()
        raise TitreDejaUtilise(str(donnees.get("titre", jeu.titre))) from None

    depot.ajouter_modification(session, jeu.id, list(donnees), utilisateur.id)
    return jeu


def supprimer(session: Session, jeu_id: int, utilisateur: Utilisateur) -> None:
    jeu = trouver(session, jeu_id)
    verifier_droit(jeu, utilisateur)
    depot.supprimer(session, jeu)


def supprimer_par_genre(session: Session, genre: str | None) -> int:
    """Une opération destructrice doit exiger une intention explicite.

    `DELETE /jeux` sans paramètre supprimerait tout le catalogue sur une faute
    de frappe.
    """
    if not genre:
        raise ParametreManquant("genre")
    return depot.supprimer_par_genre(session, genre)


def historique(session: Session, jeu_id: int):
    trouver(session, jeu_id)
    return depot.historique(session, jeu_id)


def statistiques(session: Session) -> dict:
    return depot.statistiques(session)
