"""Assemblage de l'application — séance 7.

`main.py` ne fait qu'assembler : configuration, middlewares, gestionnaires
d'erreurs et routeurs. Aucune route métier n'est déclarée ici.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as ErreurHTTPStarlette

from app.base_donnees import creer_tables, engine
from app.config import configuration
from app.exceptions import ErreurMetier
from app.journalisation import configurer_journalisation, logger
from app.routeurs import (
    administration,
    authentification,
    demonstration,
    editeurs,
    jeux,
    systeme,
    utilisateurs,
)

PREFIXE = "/api/v1"


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    """Avant le `yield` : le démarrage. Après : l'arrêt."""
    configurer_journalisation()
    logger.info("Démarrage — environnement : %s", configuration.environnement)

    try:
        creer_tables()
        with engine.connect() as connexion:
            connexion.execute(text("SELECT 1"))
        logger.info("Base de données joignable")
    except Exception:
        logger.exception("Base de données injoignable au démarrage")

    yield

    logger.info("Arrêt de l'API")


app = FastAPI(
    title="API Catalogue de jeux",
    version="1.0.0",
    summary="API REST construite au fil des sept séances du module Python Backend & FastAPI.",
    lifespan=cycle_de_vie,
    openapi_tags=[
        {"name": "Système", "description": "Racine et contrôle de santé."},
        {"name": "Authentification", "description": "Inscription, connexion, déconnexion."},
        {"name": "Mon compte", "description": "Profil et ressources de l'appelant."},
        {"name": "Jeux", "description": "CRUD du catalogue. Les lectures sont publiques."},
        {"name": "Éditeurs", "description": "Éditeurs et leurs jeux."},
        {"name": "Administration", "description": "Réservé au rôle `admin`."},
        {"name": "Démonstration async", "description": "Illustrations de la séance 7."},
    ],
)


# --- Middlewares ------------------------------------------------------------

# Jamais d'astérisque avec `allow_credentials` : la combinaison est rejetée par
# les navigateurs. Et CORS protège le navigateur, pas l'API — curl l'ignore.
app.add_middleware(
    CORSMiddleware,
    allow_origins=configuration.origines_autorisees,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def journaliser_requetes(requete: Request, appeler_suivant):
    debut = time.perf_counter()
    reponse = await appeler_suivant(requete)
    duree = (time.perf_counter() - debut) * 1000

    # Formatage différé : la chaîne n'est assemblée que si le niveau est actif.
    logger.info(
        "%s %s -> %s en %.1f ms",
        requete.method,
        requete.url.path,
        reponse.status_code,
        duree,
    )
    return reponse


# --- Gestionnaires d'erreurs ------------------------------------------------


@app.exception_handler(ErreurMetier)
async def gerer_erreur_metier(requete: Request, erreur: ErreurMetier):
    """Un seul endroit pour le format des erreurs de toute l'API."""
    return JSONResponse(
        status_code=erreur.statut,
        content={
            "code": erreur.code,
            "message": erreur.message,
            "details": erreur.details,
        },
        headers=erreur.entetes,
    )


# Les codes donnés aux erreurs que FastAPI et Starlette lèvent eux-mêmes :
# route inconnue, méthode interdite, ou jeton absent — ce dernier cas est
# traité par `OAuth2PasswordBearer`, avant même que notre code s'exécute.
CODES_HTTP = {
    401: "NON_AUTHENTIFIE",
    403: "DROIT_INSUFFISANT",
    404: "ROUTE_INTROUVABLE",
    405: "METHODE_NON_AUTORISEE",
}


@app.exception_handler(ErreurHTTPStarlette)
async def gerer_erreur_http(requete: Request, erreur: ErreurHTTPStarlette):
    """Ramène les erreurs du framework au format de l'API.

    Sans ce gestionnaire, un appel sans jeton renverrait
    `{"detail": "Not authenticated"}` — une forme différente de toutes les
    autres erreurs, que le client devrait traiter à part.
    """
    return JSONResponse(
        status_code=erreur.status_code,
        content={
            "code": CODES_HTTP.get(erreur.status_code, "ERREUR_HTTP"),
            "message": str(erreur.detail),
            "details": None,
        },
        headers=getattr(erreur, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def gerer_validation(requete: Request, erreur: RequestValidationError):
    """Les erreurs Pydantic adoptent le même format que les nôtres.

    `input` est retiré de chaque erreur : sur un formulaire de connexion, il
    contiendrait le mot de passe saisi. C'est un cas réel de fuite par
    inadvertance.
    """
    details = []
    for detail in erreur.errors():
        propre = {cle: valeur for cle, valeur in detail.items() if cle not in ("input", "ctx", "url")}
        propre["loc"] = [str(element) for element in detail.get("loc", ())]
        details.append(propre)

    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ECHOUEE",
            "message": "Les données envoyées sont invalides",
            "details": details,
        },
    )


@app.exception_handler(Exception)
async def gerer_inattendu(requete: Request, erreur: Exception):
    """Le détail va dans les journaux, jamais dans la réponse.

    Une trace révèle des chemins, des noms de tables, parfois des identifiants
    de connexion : c'est de la reconnaissance offerte à un attaquant.
    """
    logger.exception("Erreur non gérée sur %s %s", requete.method, requete.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "ERREUR_INTERNE", "message": "Une erreur est survenue"},
    )


# --- Routeurs ---------------------------------------------------------------

app.include_router(systeme.routeur)
app.include_router(authentification.routeur, prefix=PREFIXE)
app.include_router(utilisateurs.routeur, prefix=PREFIXE)
app.include_router(jeux.routeur, prefix=PREFIXE)
app.include_router(editeurs.routeur, prefix=PREFIXE)
app.include_router(administration.routeur, prefix=PREFIXE)
app.include_router(demonstration.routeur, prefix=PREFIXE)
