"""Table des utilisateurs — séance 5."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy import Enum as EnumSQL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_donnees import Base


class Role(str, Enum):
    """Séance 5, exercice final B."""

    lecteur = "lecteur"
    editeur = "editeur"
    admin = "admin"


class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # La colonne s'appelle `empreinte`, jamais `mot_de_passe` : le nom rappelle
    # ce qui s'y trouve. 255 caractères — une empreinte bcrypt en fait 60, et
    # une colonne trop courte tronque silencieusement.
    empreinte: Mapped[str] = mapped_column(String(255))

    role: Mapped[Role] = mapped_column(
        EnumSQL(Role, native_enum=False, length=20), default=Role.lecteur
    )
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    derniere_connexion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    jeux: Mapped[list["Jeu"]] = relationship(  # noqa: F821
        back_populates="proprietaire", cascade="all, delete-orphan"
    )

    @property
    def est_admin(self) -> bool:
        return self.role == Role.admin
