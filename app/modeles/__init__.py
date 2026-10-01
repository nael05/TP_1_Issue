"""Modèles Pydantic — la forme de ce qui entre et sort de l'API."""

from app.modeles.commun import ErreurReponse, Jeton, Message, Page
from app.modeles.jeux import (
    EditeurEntree,
    EditeurSortie,
    Genre,
    JeuCreation,
    JeuMiseAJour,
    JeuResume,
    JeuSortie,
    JeuStatistiques,
    ModificationSortie,
    NoteEntree,
    TriJeu,
    Voisins,
)
from app.modeles.utilisateurs import ChangementRole, UtilisateurCreation, UtilisateurSortie

__all__ = [
    "ChangementRole",
    "EditeurEntree",
    "EditeurSortie",
    "ErreurReponse",
    "Genre",
    "Jeton",
    "JeuCreation",
    "JeuMiseAJour",
    "JeuResume",
    "JeuSortie",
    "JeuStatistiques",
    "Message",
    "ModificationSortie",
    "NoteEntree",
    "Page",
    "TriJeu",
    "UtilisateurCreation",
    "UtilisateurSortie",
    "Voisins",
]
