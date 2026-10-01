"""Importe des jeux depuis un CSV — séance 6, exercice 5.

    python scripts/importer.py donnees/jeux.csv --simulation
    python scripts/importer.py donnees/jeux.csv --limite 50
    python scripts/importer.py --help

Le script réutilise la couche `services` : les contraintes, la validation et
les règles métier sont **les mêmes** que celles de l'API. C'est possible parce
que `app/services/` n'importe pas FastAPI.
"""

import argparse
import csv
import sys
from pathlib import Path

from _commun import configurer  # noqa: E402

from app.base_donnees import SessionLocale, creer_tables
from app.depots import utilisateurs as depot_utilisateurs
from app.exceptions import ErreurMetier
from app.modeles.jeux import JeuCreation
from app.services import jeux as service

logger = configurer("import")

COLONNES = ("titre", "genre", "note", "annee")


def lire_csv(chemin: Path) -> list[dict]:
    # `newline=""` est requis par le module csv : sans lui, un saut de ligne à
    # l'intérieur d'un champ casse la lecture, silencieusement.
    with chemin.open(encoding="utf-8", newline="") as fichier:
        return list(csv.DictReader(fichier))


def importer(chemin: Path, limite: int, simulation: bool, email_auteur: str) -> int:
    if not chemin.exists():
        logger.error("Fichier introuvable : %s", chemin)
        return 1

    creer_tables()
    lignes = lire_csv(chemin)[:limite]
    importes = ignores = erreurs = 0

    with SessionLocale() as session:
        auteur = depot_utilisateurs.par_email(session, email_auteur)
        if auteur is None and not simulation:
            logger.error(
                "Aucun compte %s. Lancez d'abord : python scripts/peupler.py", email_auteur
            )
            return 1

        # `start=2` : la ligne 1 du fichier contient les en-têtes, les numéros
        # affichés correspondent donc aux numéros réels du fichier.
        for numero, ligne in enumerate(lignes, start=2):
            try:
                entree = JeuCreation(
                    titre=ligne["titre"].strip(),
                    genre=ligne["genre"].strip(),
                    note=int(ligne["note"]),
                    annee=int(ligne["annee"]),
                    tags=[tag for tag in ligne.get("tags", "").split("|") if tag],
                )
            except Exception as erreur:
                # Chaque ligne est traitée indépendamment : un import à moitié
                # fait est pire qu'un échec net.
                logger.warning("Ligne %d ignorée : %s", numero, _resumer(erreur))
                erreurs += 1
                continue

            if simulation:
                logger.info("[simulation] Importerait : %s", entree.titre)
                importes += 1
                continue

            try:
                service.creer(session, entree, auteur)
                importes += 1
            except ErreurMetier as erreur:
                logger.warning("Ligne %d en échec : %s", numero, erreur.message)
                ignores += 1

    logger.info("Importés : %d — Ignorés : %d — Erreurs : %d", importes, ignores, erreurs)
    # Un code de sortie non nul permet d'enchaîner dans un pipeline :
    #   python scripts/importer.py jeux.csv && python scripts/statistiques.py
    return 1 if erreurs else 0


def _resumer(erreur: Exception) -> str:
    message = str(erreur).replace("\n", " ")
    return message[:160]


def main() -> None:
    analyseur = argparse.ArgumentParser(description="Importe des jeux depuis un fichier CSV")
    # `type=Path` : sans lui on reçoit une chaîne, et `chemin.exists()` échoue.
    analyseur.add_argument("fichier", type=Path, help="Chemin du fichier CSV")
    analyseur.add_argument("--limite", type=int, default=1000, help="Nombre maximum de lignes")
    analyseur.add_argument(
        "--simulation", action="store_true", help="N'écrit rien en base, affiche ce qui serait fait"
    )
    analyseur.add_argument(
        "--auteur", default="admin@example.com", help="Email du propriétaire des jeux créés"
    )

    arguments = analyseur.parse_args()
    sys.exit(
        importer(arguments.fichier, arguments.limite, arguments.simulation, arguments.auteur)
    )


# Sans ce bloc, importer le script pour le tester déclencherait tout le travail.
if __name__ == "__main__":
    main()
