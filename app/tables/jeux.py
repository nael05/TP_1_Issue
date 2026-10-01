"""Table des jeux — séances 4 et 5."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base_donnees import Base


class Jeu(Base):
    __tablename__ = "jeux"
    __table_args__ = (
        # Une contrainte en base est une garantie définitive : aucun script,
        # aucune console d'administration ne peut l'enfreindre. La validation
        # Pydantic ne protège que ce qui passe par l'API — les deux sont utiles.
        CheckConstraint("note >= 0 AND note <= 10", name="ck_jeux_note"),
        CheckConstraint("annee >= 1970 AND annee <= 2030", name="ck_jeux_annee"),
        # Index composite : sert un filtre sur `genre`, ou sur `genre` + `note`.
        # Pas un filtre sur `note` seul — c'est le principe du préfixe.
        Index("ix_jeux_genre_note", "genre", "note"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    titre: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    genre: Mapped[str] = mapped_column(String(50), index=True)
    note: Mapped[int] = mapped_column(Integer)
    annee: Mapped[int] = mapped_column(Integer)

    # `JSON` fonctionne sur PostgreSQL comme sur SQLite (utilisé par les tests).
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    code_editeur: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Champ interne : absent de `JeuSortie`, donc jamais renvoyé au client.
    notes_internes: Mapped[str | None] = mapped_column(Text, nullable=True)

    editeur_id: Mapped[int | None] = mapped_column(
        ForeignKey("editeurs.id", ondelete="SET NULL"), nullable=True
    )
    proprietaire_id: Mapped[int | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )

    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    date_modification: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    editeur: Mapped["Editeur | None"] = relationship(back_populates="jeux")  # noqa: F821
    proprietaire: Mapped["Utilisateur | None"] = relationship(  # noqa: F821
        back_populates="jeux"
    )
    modifications: Mapped[list["Modification"]] = relationship(
        back_populates="jeu", cascade="all, delete-orphan", order_by="Modification.date"
    )


class Modification(Base):
    """Historique des modifications — séance 2, exercice final A.

    Le cours le garde en mémoire ; une table survit au redémarrage.
    """

    __tablename__ = "modifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    jeu_id: Mapped[int] = mapped_column(
        ForeignKey("jeux.id", ondelete="CASCADE"), index=True
    )
    auteur_id: Mapped[int | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="SET NULL"), nullable=True
    )
    champs: Mapped[str] = mapped_column(String(255))
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    jeu: Mapped["Jeu"] = relationship(back_populates="modifications")
