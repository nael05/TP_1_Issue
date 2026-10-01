"""Démonstration de l'asynchrone — séance 7, partie 4.

Appelez `/demo/bloquant`, puis `/sante` dans un autre onglet pendant ce
temps : **rien ne répond**. Les deux autres routes ne posent aucun problème.
"""

import asyncio
import time

import httpx
from fastapi import APIRouter, Query

routeur = APIRouter(prefix="/demo", tags=["Démonstration async"])

DUREE_MAX = 10


@routeur.get("/bloquant", summary="async def + code bloquant — gèle tout le serveur")
async def bloquant(duree: int = Query(default=3, ge=0, le=DUREE_MAX)):
    """`time.sleep` n'annonce rien à la boucle d'événements : il bloque le fil.

    FastAPI exécute les `async def` sur une boucle à **un seul fil**. Gelée,
    elle ne traite plus aucune requête — pour aucun client.
    """
    time.sleep(duree)
    return {"type": "async def + time.sleep", "duree": duree, "effet": "serveur gelé"}


@routeur.get("/correct", summary="async def + await — la boucle reste libre")
async def correct(duree: int = Query(default=3, ge=0, le=DUREE_MAX)):
    """`await asyncio.sleep` rend la main : la boucle traite autre chose."""
    await asyncio.sleep(duree)
    return {"type": "async def + await asyncio.sleep", "duree": duree, "effet": "aucun"}


@routeur.get("/en-fil", summary="def normal — exécuté dans un pool de fils")
def en_fil(duree: int = Query(default=3, ge=0, le=DUREE_MAX)):
    """Une route `def` normale est un choix valide : FastAPI l'exécute dans un
    pool de fils séparé, où elle peut bloquer sans conséquence.

    Dans le doute, c'est le choix sûr — écrire `async def` par habitude, avec
    du code bloquant dedans, est pire que de ne pas l'écrire du tout.
    """
    time.sleep(duree)
    return {"type": "def normal + time.sleep", "duree": duree, "effet": "aucun"}


@routeur.get("/parallele", summary="Trois appels réseau simultanés")
async def parallele():
    """Le cas où `async` apporte vraiment quelque chose : plusieurs attentes
    indépendantes. Trois appels de 200 ms font ~200 ms au lieu de 600.

    `httpx` et non `requests` : ce dernier est bloquant, et les trois appels
    redeviendraient séquentiels tout en gelant la boucle.
    """
    base = "https://jsonplaceholder.typicode.com/posts"

    async with httpx.AsyncClient(timeout=10) as client:
        reponses = await asyncio.gather(
            *(client.get(f"{base}/{identifiant}") for identifiant in (1, 2, 3)),
            return_exceptions=True,
        )

    resultats = []
    for reponse in reponses:
        if isinstance(reponse, Exception):
            resultats.append({"erreur": type(reponse).__name__})
        else:
            resultats.append(reponse.json())
    return resultats


@routeur.get("/erreur", summary="Erreur inattendue — vérifie l'absence de divulgation")
def erreur():
    """La réponse est un 500 générique ; la trace part dans les journaux."""
    return {"resultat": 1 / 0}
