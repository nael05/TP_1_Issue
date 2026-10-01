"""Consomme une API tierce — séance 6, partie 6.

    python scripts/enrichir.py
    python scripts/enrichir.py --base https://hote-injoignable.invalid --nombre 2

Un service tiers est hors de votre contrôle : il sera indisponible un jour,
lent un autre, et changera de format sans prévenir. La gestion d'erreur n'est
pas une précaution, c'est le fonctionnement normal.
"""

import argparse
import sys
import time

import requests
from _commun import configurer  # noqa: E402
from requests.exceptions import RequestException

logger = configurer("enrichir")

BASE_PAR_DEFAUT = "https://jsonplaceholder.typicode.com"
DELAI = 10


def recuperer(session: requests.Session, url: str) -> dict | None:
    try:
        # `requests` n'a AUCUN timeout par défaut : sans lui, une requête peut
        # attendre indéfiniment et bloquer le script, sans message.
        reponse = session.get(url, timeout=DELAI)
        # Comme `fetch` en JavaScript, `requests` ne lève rien sur un 4xx/5xx :
        # la requête a abouti, la réponse est une erreur.
        reponse.raise_for_status()
        return reponse.json()
    except RequestException as erreur:
        logger.error("Appel échoué sur %s : %s", url, erreur)
        return None
    except ValueError:
        logger.error("Réponse illisible (JSON invalide) sur %s", url)
        return None


def enrichir(base: str, nombre: int, pause: float) -> int:
    reussis = echecs = 0

    # Une session réutilise la connexion TCP : sur cent requêtes vers le même
    # hôte, la négociation TLS n'a lieu qu'une fois.
    with requests.Session() as session:
        session.headers.update({"Accept": "application/json", "User-Agent": "api-jeux/1.0"})

        for identifiant in range(1, nombre + 1):
            donnees = recuperer(session, f"{base}/posts/{identifiant}")

            if donnees is None:
                echecs += 1
            else:
                reussis += 1
                logger.info("Reçu : %s", str(donnees.get("title", ""))[:60])

            # Beaucoup d'API limitent le nombre d'appels ; un 429 signale qu'on
            # va trop vite. En production : nouvelle tentative après un délai
            # croissant.
            if identifiant < nombre:
                time.sleep(pause)

    logger.info("Réussis : %d — Échecs : %d", reussis, echecs)
    return 1 if reussis == 0 else 0


def main() -> None:
    analyseur = argparse.ArgumentParser(description="Appelle une API publique")
    analyseur.add_argument("--base", default=BASE_PAR_DEFAUT, help="URL de base du service")
    analyseur.add_argument("--nombre", type=int, default=5, help="Nombre d'appels")
    analyseur.add_argument("--pause", type=float, default=0.5, help="Pause entre les appels")

    arguments = analyseur.parse_args()
    sys.exit(enrichir(arguments.base, arguments.nombre, arguments.pause))


if __name__ == "__main__":
    main()
