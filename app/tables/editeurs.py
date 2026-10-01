"""Table des éditeurs — séance 4, partie 6 (relations)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_donnees import Base


class Editeur(Base):
    __tablename__ = "editeurs"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    pays: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # `back_populates` relie les deux côtés : modifier l'un met l'autre à jour.
    jeux: Mapped[list["Jeu"]] = relationship(back_populates="editeur")  # noqa: F821
