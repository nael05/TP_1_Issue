"""Affiche un rapport lisible dans le terminal — séance 6, exercice 5.7.

    python scripts/statistiques.py
"""

import argparse
import sys

from _commun import configurer  # noqa: E402

from app.base_donnees import SessionLocale
from app.depots import jeux as depot

configurer("statistiques")


def rapport(largeur: int = 30) -> int:
    with SessionLocale() as session:
        stats = depot.statistiques(session)

    print()
    print("  Catalogue de jeux".ljust(largeur + 12))
    print("  " + "─" * (largeur + 10))
    print(f"  {'Nombre de jeux':<{largeur}} {stats['nombre']:>6}")
    print(f"  {'Note moyenne':<{largeur}} {stats['moyenne']:>6}")
    print(f"  {'Meilleure note':<{largeur}} {str(stats['meilleure_note'] or '—'):>6}")

    if stats["par_genre"]:
        print()
        print("  Répartition par genre")
        print("  " + "─" * (largeur + 10))
        maximum = max(stats["par_genre"].values())
        for genre, compte in sorted(stats["par_genre"].items(), key=lambda p: -p[1]):
            barre = "█" * max(1, round(compte / maximum * 20))
            print(f"  {genre:<{largeur}} {compte:>3}  {barre}")

    print()
    return 0


def main() -> None:
    analyseur = argparse.ArgumentParser(description="Rapport statistique du catalogue")
    analyseur.add_argument("--largeur", type=int, default=30, help="Largeur des colonnes")

    arguments = analyseur.parse_args()
    sys.exit(rapport(arguments.largeur))


if __name__ == "__main__":
    main()
