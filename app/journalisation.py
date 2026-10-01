"""Journalisation — séance 6, partie 4.

`print` n'a ni niveau, ni horodatage, ni origine, et se perd en production.
"""

import logging

from app.config import configuration

logger = logging.getLogger("api")


def configurer_journalisation() -> None:
    logging.basicConfig(
        level=getattr(logging, configuration.niveau_journal.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
