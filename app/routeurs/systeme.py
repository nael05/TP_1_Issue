"""Routes système — séance 7, partie 3."""

from fastapi import APIRouter
from sqlalchemy import text

from app.config import configuration
from app.dependances import SessionDep
from app.exceptions import ErreurMetier
from app.journalisation import logger

routeur = APIRouter(tags=["Système"])


@routeur.get("/", summary="Racine")
def racine():
    return {
        "message": "API opérationnelle",
        "documentation": "/docs",
        "version": "1.0.0",
    }


@routeur.get("/sante", summary="Contrôle de santé")
def sante(session: SessionDep):
    """Rapide, sans authentification, et 503 en cas de problème — c'est ce qui
    déclenche le redémarrage ou le retrait du trafic par la plateforme.

    Cette route est publique : elle dit « je fonctionne », pas « voici comment
    je suis construit ».
    """
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Contrôle de santé : base injoignable")
        raise ErreurMetier("BASE_INJOIGNABLE", "Base de données injoignable", 503) from None

    return {
        "statut": "ok",
        "base": "ok",
        "environnement": configuration.environnement,
    }
