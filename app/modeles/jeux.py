"""Modèles Pydantic des jeux — séance 3.

Un modèle d'entrée, un de mise à jour, deux de sortie. Ce ne sont pas les mêmes
besoins : l'entrée doit refuser `id` et `proprietaire_id`, la sortie doit
masquer `notes_internes`.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Genre(str, Enum):
    """Un ensemble fixe de valeurs : Swagger affiche une liste déroulante, et le
    message d'erreur énumère les valeurs acceptées."""

    action = "Action"
    aventure = "Aventure"
    metroidvania = "Metroidvania"
    party = "Party"
    plateforme = "Plateforme"
    reflexion = "Réflexion"
    roguelike = "Roguelike"
    rpg = "RPG"
    simulation = "Simulation"
    strategie = "Stratégie"


class TriJeu(str, Enum):
    titre = "titre"
    note = "note"
    annee = "annee"


class EditeurSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    pays: str | None = None


class EditeurEntree(BaseModel):
    nom: str = Field(min_length=1, max_length=100, examples=["Maddy Makes Games"])
    pays: str | None = Field(default=None, min_length=2, max_length=50, examples=["Canada"])

    @field_validator("nom")
    @classmethod
    def nettoyer_nom(cls, valeur: str) -> str:
        nettoye = valeur.strip()
        if not nettoye:
            raise ValueError("Le nom ne peut pas être vide")
        return nettoye


class JeuBase(BaseModel):
    """Les contraintes sont écrites une seule fois, et héritées."""

    titre: str = Field(
        min_length=1,
        max_length=100,
        description="Titre du jeu",
        examples=["Celeste"],
    )
    genre: Genre = Field(description="Genre principal", examples=[Genre.plateforme])
    note: int = Field(ge=0, le=10, description="Note sur 10", examples=[9])
    annee: int = Field(ge=1970, le=2030, description="Année de sortie", examples=[2018])
    tags: list[str] = Field(default_factory=list, max_length=10)
    code_editeur: str | None = Field(
        default=None,
        pattern=r"^[A-Z]{3}-\d{4}$",
        description="Format ABC-1234",
        examples=["MMG-2018"],
    )

    @field_validator("titre")
    @classmethod
    def titre_non_vide(cls, valeur: str) -> str:
        """Un validateur *renvoie* la valeur, éventuellement normalisée.

        L'oublier remplace silencieusement le champ par `None`.
        """
        nettoye = valeur.strip()
        if not nettoye:
            raise ValueError("Le titre ne peut pas être vide")
        return nettoye

    @field_validator("annee")
    @classmethod
    def annee_raisonnable(cls, valeur: int) -> int:
        if valeur > date.today().year + 1:
            raise ValueError("L'année ne peut pas dépasser l'année prochaine")
        return valeur

    @field_validator("tags")
    @classmethod
    def normaliser_tags(cls, valeurs: list[str]) -> list[str]:
        """Minuscules, sans doublon, *en conservant l'ordre*.

        `list(set(...))` serait plus court mais perdrait l'ordre.
        """
        vus: set[str] = set()
        resultat: list[str] = []
        for tag in valeurs:
            propre = tag.strip().lower()
            if propre and propre not in vus:
                vus.add(propre)
                resultat.append(propre)
        return resultat

    @model_validator(mode="after")
    def coherence_note_annee(self):
        """Une règle qui porte sur deux champs exige `model_validator`."""
        if self.note == 10 and self.annee > date.today().year:
            raise ValueError("Un jeu non sorti ne peut pas avoir la note maximale")
        return self


class JeuCreation(JeuBase):
    """Ce que le client envoie pour créer.

    Ni `id`, ni `date_creation`, ni `proprietaire_id` : ce qui n'est pas
    déclaré n'entre pas. La protection est structurelle, pas défensive.
    """

    editeur_id: int | None = None


class JeuMiseAJour(BaseModel):
    """Tout facultatif — n'hérite donc pas de `JeuBase`, dont les champs sont
    obligatoires. Duplication assumée, et plus lisible qu'une génération."""

    titre: str | None = Field(default=None, min_length=1, max_length=100)
    genre: Genre | None = None
    note: int | None = Field(default=None, ge=0, le=100)
    annee: int | None = Field(default=None, ge=1970, le=2030)
    tags: list[str] | None = Field(default=None, max_length=10)
    code_editeur: str | None = Field(default=None, pattern=r"^[A-Z]{3}-\d{4}$")
    editeur_id: int | None = None


class NoteEntree(BaseModel):
    """Un modèle même pour un seul champ : un `int` nu serait cherché dans la
    requête, pas dans le corps."""

    note: int = Field(ge=0, le=10)


class JeuResume(BaseModel):
    """Forme allégée, pour les listes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titre: str
    genre: str
    note: int


class JeuSortie(BaseModel):
    """Ce que l'API renvoie.

    `notes_internes` n'y figure pas : même si la fonction renvoie l'objet
    complet, FastAPI retire le champ avant l'envoi.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    titre: str
    genre: str
    note: int
    annee: int
    tags: list[str] = Field(default_factory=list)
    code_editeur: str | None = None
    editeur: EditeurSortie | None = None
    proprietaire_id: int | None = None
    date_creation: datetime
    date_modification: datetime | None = None


class Voisins(BaseModel):
    """Séance 1, exercice final C. `null` aux extrémités."""

    precedent: JeuResume | None = None
    suivant: JeuResume | None = None


class ModificationSortie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: datetime
    champs: list[str]
    auteur_id: int | None = None

    @field_validator("champs", mode="before")
    @classmethod
    def decouper(cls, valeur: object) -> object:
        """La colonne stocke `note,titre` ; l'API expose une liste."""
        if isinstance(valeur, str):
            return [champ for champ in valeur.split(",") if champ]
        return valeur


class JeuStatistiques(BaseModel):
    """Séance 3, exercice final B : une réponse typée se documente."""

    nombre: int = Field(ge=0)
    moyenne: float = Field(ge=0, le=10)
    meilleure_note: int | None = Field(default=None, ge=0, le=10)
    par_genre: dict[str, int] = Field(default_factory=dict)
