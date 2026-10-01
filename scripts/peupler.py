"""Peuple la base avec le catalogue de départ — séance 4, exercice 2.4.

    python scripts/peupler.py
    python scripts/peupler.py --admin admin@example.com --mot-de-passe secret123
    python scripts/peupler.py --vider
"""

import argparse
import sys

from _commun import configurer  # noqa: E402  (ajoute la racine au chemin)

from app.base_donnees import SessionLocale, creer_tables
from app.depots import utilisateurs as depot_utilisateurs
from app.donnees_initiales import EDITEURS_INITIAUX, JEUX_INITIAUX
from app.securite import hacher
from app.tables import Editeur, Jeu, Role, Utilisateur

logger = configurer("peupler")


def peupler(email_admin: str, mot_de_passe: str, vider: bool) -> int:
    creer_tables()

    # `with` ferme la session automatiquement, y compris en cas d'erreur.
    # Dans un script c'est la bonne forme ; dans FastAPI, c'est la dépendance.
    with SessionLocale() as session:
        if vider:
            for jeu in session.query(Jeu).all():
                session.delete(jeu)
            session.commit()
            logger.info("Catalogue vidé")

        administrateur = depot_utilisateurs.par_email(session, email_admin)
        if administrateur is None:
            administrateur = Utilisateur(
                email=email_admin, empreinte=hacher(mot_de_passe), role=Role.admin
            )
            session.add(administrateur)
            session.commit()
            session.refresh(administrateur)
            logger.info("Administrateur créé : %s", email_admin)
        else:
            logger.info("Administrateur déjà présent : %s", email_admin)

        editeurs: dict[str, Editeur] = {}
        for donnees in EDITEURS_INITIAUX:
            editeur = session.query(Editeur).filter_by(nom=donnees["nom"]).one_or_none()
            if editeur is None:
                editeur = Editeur(**donnees)
                session.add(editeur)
            editeurs[donnees["nom"]] = editeur
        session.commit()

        crees = ignores = 0
        for donnees in JEUX_INITIAUX:
            donnees = dict(donnees)
            nom_editeur = donnees.pop("editeur", None)

            if session.query(Jeu).filter_by(titre=donnees["titre"]).one_or_none() is not None:
                ignores += 1
                continue

            session.add(
                Jeu(
                    **donnees,
                    editeur_id=editeurs[nom_editeur].id if nom_editeur else None,
                    proprietaire_id=administrateur.id,
                )
            )
            crees += 1

        # `add` prépare seulement ; sans `commit`, le script affiche
        # « Base peuplée » et la table reste vide.
        session.commit()

    logger.info("Jeux créés : %d — déjà présents : %d", crees, ignores)
    return 0


def main() -> None:
    analyseur = argparse.ArgumentParser(description="Peuple la base de démonstration")
    analyseur.add_argument("--admin", default="admin@example.com", help="Email de l'administrateur")
    analyseur.add_argument(
        "--mot-de-passe", default="motdepasse123", help="Mot de passe de l'administrateur"
    )
    analyseur.add_argument("--vider", action="store_true", help="Vide le catalogue d'abord")

    arguments = analyseur.parse_args()
    sys.exit(peupler(arguments.admin, arguments.mot_de_passe, arguments.vider))


if __name__ == "__main__":
    main()
