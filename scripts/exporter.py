"""Exporte le catalogue vers un CSV — séance 6, exercice 5.6.

    python scripts/exporter.py sortie.csv
    python scripts/exporter.py sortie.csv --genre RPG --note-min 8
"""

import argparse
import csv
import sys
from pathlib import Path

from _commun import configurer  # noqa: E402

from app.base_donnees import SessionLocale
from app.depots import jeux as depot

logger = configurer("export")

COLONNES = ["id", "titre", "genre", "note", "annee", "tags", "date_creation"]


def exporter(chemin: Path, genre: str | None, note_min: int) -> int:
    with SessionLocale() as session:
        jeux = depot.lister(session, genre=genre, note_min=note_min, limite=10_000)

        with chemin.open("w", encoding="utf-8", newline="") as fichier:
            redacteur = csv.DictWriter(fichier, fieldnames=COLONNES)
            redacteur.writeheader()
            for jeu in jeux:
                redacteur.writerow(
                    {
                        "id": jeu.id,
                        "titre": jeu.titre,
                        "genre": jeu.genre,
                        "note": jeu.note,
                        "annee": jeu.annee,
                        "tags": "|".join(jeu.tags or []),
                        "date_creation": jeu.date_creation.isoformat() if jeu.date_creation else "",
                    }
                )

    logger.info("%d jeux exportés vers %s", len(jeux), chemin)
    return 0


def main() -> None:
    analyseur = argparse.ArgumentParser(description="Exporte le catalogue vers un CSV")
    analyseur.add_argument("fichier", type=Path, help="Chemin du fichier à écrire")
    analyseur.add_argument("--genre", default=None, help="Filtrer sur un genre")
    analyseur.add_argument("--note-min", type=int, default=0, help="Note minimale")

    arguments = analyseur.parse_args()
    sys.exit(exporter(arguments.fichier, arguments.genre, arguments.note_min))


if __name__ == "__main__":
    main()
