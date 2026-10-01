"""Limitation des tentatives de connexion — séance 5, exercice 6.4.

En mémoire : perdue au redémarrage, non partagée entre plusieurs instances.
En production, on utilise Redis, et on limite aussi par adresse IP.

Une API sans limitation permet de tester des millions de mots de passe.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.config import configuration
from app.exceptions import TropDeTentatives

_tentatives: dict[str, list[datetime]] = defaultdict(list)


def _fenetre() -> timedelta:
    return timedelta(minutes=configuration.fenetre_tentatives_minutes)


def verifier(cle: str) -> None:
    maintenant = datetime.now(timezone.utc)
    recentes = [instant for instant in _tentatives[cle] if maintenant - instant < _fenetre()]
    _tentatives[cle] = recentes

    if len(recentes) >= configuration.max_tentatives_connexion:
        raise TropDeTentatives(configuration.fenetre_tentatives_minutes)


def enregistrer_echec(cle: str) -> None:
    _tentatives[cle].append(datetime.now(timezone.utc))


def reinitialiser(cle: str | None = None) -> None:
    if cle is None:
        _tentatives.clear()
    else:
        _tentatives.pop(cle, None)
