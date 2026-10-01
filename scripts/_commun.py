"""Amorçage commun aux scripts — séance 6, partie 5.

Les scripts vivent dans `scripts/`, l'application dans `app/` : il faut que la
racine du projet soit sur le chemin d'import pour que `import app...` marche
quand on lance `python scripts/importer.py` depuis la racine.
"""

import logging
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))


def configurer(nom: str) -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s | %(message)s")
    return logging.getLogger(nom)
