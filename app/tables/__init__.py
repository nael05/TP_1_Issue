"""Modèles SQLAlchemy — les tables.

À ne pas confondre avec `app/modeles/`, qui contient les modèles Pydantic :
les premiers persistent, les seconds valident ce qui entre et sort de l'API.
"""

from app.tables.editeurs import Editeur
from app.tables.jeux import Jeu, Modification
from app.tables.utilisateurs import Role, Utilisateur

__all__ = ["Editeur", "Jeu", "Modification", "Role", "Utilisateur"]
