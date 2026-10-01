"""Modèles transverses — séance 3, parties 4 et 5."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field, computed_field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Réponse paginée générique.

    Le client sait combien d'éléments existent au total, ce qui est
    indispensable pour afficher une pagination.
    """

    elements: list[T]
    total: int = Field(ge=0, description="Nombre d'éléments après filtrage")
    saut: int = Field(ge=0)
    limite: int = Field(ge=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages_totales(self) -> int:
        if self.limite == 0:
            return 0
        # Arrondi supérieur : 101 éléments par pages de 20 font 6 pages, pas 5.
        return (self.total + self.limite - 1) // self.limite


class ErreurReponse(BaseModel):
    """Le format d'erreur unique de l'API.

    `code` est stable et destiné au code client ; `message` est destiné à
    l'humain et peut changer sans rien casser.
    """

    code: str = Field(examples=["JEU_INTROUVABLE"])
    message: str = Field(examples=["Aucun jeu avec l'identifiant 42"])
    details: dict | list | None = None


class Message(BaseModel):
    message: str


class Jeton(BaseModel):
    """Les noms sont imposés par OAuth2 : ne les traduisez pas."""

    access_token: str
    token_type: str = "bearer"


# Réponses d'erreur réutilisables dans `responses=` sur les routes.
REPONSES_AUTHENTIFICATION = {
    401: {"model": ErreurReponse, "description": "Non authentifié"},
}
REPONSES_DROITS = {
    401: {"model": ErreurReponse, "description": "Non authentifié"},
    403: {"model": ErreurReponse, "description": "Droits insuffisants"},
}
