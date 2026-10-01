"""Modèles Pydantic des utilisateurs — séance 5."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.tables.utilisateurs import Role


class UtilisateurCreation(BaseModel):
    """Ni `role` ni `actif` : sans quoi n'importe qui s'inscrirait administrateur."""

    email: EmailStr = Field(examples=["etudiant@example.com"])
    mot_de_passe: str = Field(min_length=8, max_length=128, examples=["motdepasse123"])


class UtilisateurSortie(BaseModel):
    """Ni `mot_de_passe`, ni `empreinte`. Jamais."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: Role
    actif: bool
    date_creation: datetime
    derniere_connexion: datetime | None = None


class ChangementRole(BaseModel):
    role: Role
