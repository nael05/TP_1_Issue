"""Accès aux données des jeux — séance 4, partie 5.

Le dépôt ne décide de rien : il lit et il écrit. Aucune règle métier, aucune
exception applicative — c'est le service qui décide.
"""

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.tables.jeux import Jeu, Modification


def _requete_filtree(
    genre: str | None = None,
    note_min: int = 0,
    recherche: str | None = None,
    proprietaire_id: int | None = None,
) -> Select:
    """Chaque `.where()` renvoie une *nouvelle* requête : rien n'est exécuté
    avant `session.scalars(...)`, ce qui permet de composer les filtres."""
    requete = select(Jeu)

    if genre:
        requete = requete.where(Jeu.genre == genre)
    if note_min:
        requete = requete.where(Jeu.note >= note_min)
    if recherche:
        # `ilike` ignore la casse. La valeur reste un paramètre lié : ce n'est
        # pas une injection SQL. En revanche, un `%` saisi devient un joker.
        terme = recherche.replace("%", r"\%").replace("_", r"\_")
        requete = requete.where(Jeu.titre.ilike(f"%{terme}%"))
    if proprietaire_id is not None:
        requete = requete.where(Jeu.proprietaire_id == proprietaire_id)

    return requete


def lister(
    session: Session,
    genre: str | None = None,
    note_min: int = 0,
    recherche: str | None = None,
    proprietaire_id: int | None = None,
    tri: str = "titre",
    saut: int = 0,
    limite: int = 20,
) -> list[Jeu]:
    requete = _requete_filtree(genre, note_min, recherche, proprietaire_id)

    colonne = {"titre": Jeu.titre, "note": Jeu.note, "annee": Jeu.annee}[tri]
    ordre = colonne.desc() if tri == "annee" else colonne.asc()

    # `selectinload` : deux requêtes au total, quel que soit le nombre de jeux.
    # Sans lui, une requête par jeu pour charger l'éditeur — le problème N+1.
    requete = (
        requete.options(selectinload(Jeu.editeur))
        .order_by(ordre, Jeu.id)
        .offset(saut)
        .limit(limite)
    )
    return list(session.scalars(requete).all())


def compter(
    session: Session,
    genre: str | None = None,
    note_min: int = 0,
    recherche: str | None = None,
    proprietaire_id: int | None = None,
) -> int:
    """Le total compte les éléments correspondant aux filtres, pas le catalogue."""
    requete = _requete_filtree(genre, note_min, recherche, proprietaire_id)
    sous_requete = requete.with_only_columns(Jeu.id).subquery()
    return session.scalar(select(func.count()).select_from(sous_requete)) or 0


def par_id(session: Session, jeu_id: int) -> Jeu | None:
    """`session.get` lit par clé primaire et utilise le cache de la session."""
    return session.get(Jeu, jeu_id)


def par_titre(session: Session, titre: str) -> Jeu | None:
    return session.scalar(select(Jeu).where(func.lower(Jeu.titre) == titre.lower()))


def tous_les_identifiants(session: Session) -> list[int]:
    return list(session.scalars(select(Jeu.id).order_by(Jeu.id)).all())


def genres_distincts(session: Session) -> list[str]:
    return list(session.scalars(select(Jeu.genre).distinct().order_by(Jeu.genre)).all())


def similaires(session: Session, jeu: Jeu, limite: int = 20) -> list[Jeu]:
    requete = (
        select(Jeu)
        .where(Jeu.genre == jeu.genre)
        .order_by(Jeu.note.desc(), Jeu.titre)
        .limit(limite)
    )
    return list(session.scalars(requete).all())


def enregistrer(session: Session, jeu: Jeu) -> Jeu:
    """`add` prépare, `commit` écrit, `refresh` récupère l'identifiant attribué
    et les valeurs calculées par la base."""
    session.add(jeu)
    session.commit()
    session.refresh(jeu)
    return jeu


def supprimer(session: Session, jeu: Jeu) -> None:
    session.delete(jeu)
    session.commit()


def supprimer_par_genre(session: Session, genre: str) -> int:
    jeux = list(session.scalars(select(Jeu).where(func.lower(Jeu.genre) == genre.lower())).all())
    for jeu in jeux:
        session.delete(jeu)
    session.commit()
    return len(jeux)


def vider(session: Session) -> int:
    jeux = list(session.scalars(select(Jeu)).all())
    for jeu in jeux:
        session.delete(jeu)
    session.commit()
    return len(jeux)


def ajouter_modification(
    session: Session, jeu_id: int, champs: list[str], auteur_id: int | None
) -> None:
    session.add(
        Modification(jeu_id=jeu_id, champs=",".join(sorted(champs)), auteur_id=auteur_id)
    )
    session.commit()


def historique(session: Session, jeu_id: int) -> list[Modification]:
    requete = (
        select(Modification)
        .where(Modification.jeu_id == jeu_id)
        .order_by(Modification.date, Modification.id)
    )
    return list(session.scalars(requete).all())


def statistiques(session: Session) -> dict:
    """Agrégation *en SQL* — séance 4, exercice final C.

    Une seule ligne transite, au lieu de toutes les lignes de la table.
    """
    nombre, moyenne, meilleure = session.execute(
        select(func.count(Jeu.id), func.avg(Jeu.note), func.max(Jeu.note))
    ).one()

    par_genre = session.execute(
        select(Jeu.genre, func.count(Jeu.id)).group_by(Jeu.genre).order_by(Jeu.genre)
    ).all()

    return {
        "nombre": nombre or 0,
        # `func.avg` renvoie un Decimal sur PostgreSQL : le `float()` est requis.
        "moyenne": round(float(moyenne), 2) if moyenne is not None else 0.0,
        "meilleure_note": meilleure,
        "par_genre": {genre: compte for genre, compte in par_genre},
    }
