"""Configuration centralisée — séance 7, partie 3.

`pydantic-settings` valide la configuration au démarrage : une variable
manquante empêche le lancement avec un message explicite, au lieu de produire
un `None` qui échouera plus tard, en production, au pire moment.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Obligatoires : aucune valeur par défaut, le démarrage échoue sans elles.
    database_url: str
    cle_secrete: str

    # Facultatives, avec une valeur par défaut raisonnable.
    algorithme_jeton: str = "HS256"
    duree_jeton_minutes: int = 30
    origines_autorisees: list[str] = ["http://localhost:5173"]
    environnement: str = "developpement"
    niveau_journal: str = "INFO"
    echo_sql: bool = False
    max_tentatives_connexion: int = 5
    fenetre_tentatives_minutes: int = 15

    @field_validator("origines_autorisees", mode="before")
    @classmethod
    def decouper_origines(cls, valeur: object) -> object:
        """Accepte `A,B` autant qu'une liste JSON, pour les plateformes d'hébergement."""
        if isinstance(valeur, str) and not valeur.strip().startswith("["):
            return [origine.strip() for origine in valeur.split(",") if origine.strip()]
        return valeur

    @field_validator("database_url")
    @classmethod
    def normaliser_url(cls, valeur: str) -> str:
        """Beaucoup de plateformes fournissent `postgres://`, refusé par SQLAlchemy."""
        if valeur.startswith("postgres://"):
            return valeur.replace("postgres://", "postgresql+psycopg://", 1)
        return valeur

    @property
    def est_production(self) -> bool:
        return self.environnement == "production"


configuration = Configuration()
