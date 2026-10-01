"""Exceptions métier — séance 3, partie 5.

Ces exceptions ne connaissent pas HTTP : elles portent un statut, mais aucun
objet FastAPI. C'est ce qui permet aux services d'être utilisés hors de l'API,
depuis un script par exemple.
"""


class ErreurMetier(Exception):
    """Toute erreur prévue de l'application.

    `code` est stable : le client s'en sert pour brancher son comportement.
    `message` s'adresse à un humain et peut changer sans rien casser.
    """

    def __init__(
        self,
        code: str,
        message: str,
        statut: int = 400,
        details: dict | None = None,
        entetes: dict[str, str] | None = None,
    ):
        self.code = code
        self.message = message
        self.statut = statut
        self.details = details
        self.entetes = entetes
        super().__init__(message)


# --- Jeux -------------------------------------------------------------------


class JeuIntrouvable(ErreurMetier):
    def __init__(self, jeu_id: int):
        super().__init__(
            "JEU_INTROUVABLE",
            f"Aucun jeu avec l'identifiant {jeu_id}",
            404,
            {"jeu_id": jeu_id},
        )


class TitreDejaUtilise(ErreurMetier):
    def __init__(self, titre: str):
        super().__init__(
            "TITRE_DEJA_UTILISE",
            f"Un jeu intitulé '{titre}' existe déjà",
            409,
            {"titre": titre},
        )


class EditeurIntrouvable(ErreurMetier):
    def __init__(self, editeur_id: int):
        super().__init__(
            "EDITEUR_INTROUVABLE",
            f"Aucun éditeur avec l'identifiant {editeur_id}",
            404,
            {"editeur_id": editeur_id},
        )


# --- Utilisateurs et accès --------------------------------------------------


class EmailDejaUtilise(ErreurMetier):
    def __init__(self, email: str):
        super().__init__("EMAIL_DEJA_UTILISE", "Cet email est déjà utilisé", 409, {"email": email})


class IdentifiantsInvalides(ErreurMetier):
    """Un seul message pour « email inconnu » et « mot de passe faux ».

    Distinguer les deux cas permettrait d'énumérer les comptes inscrits.
    """

    def __init__(self):
        super().__init__(
            "IDENTIFIANTS_INVALIDES",
            "Identifiants incorrects",
            401,
            entetes={"WWW-Authenticate": "Bearer"},
        )


class JetonInvalide(ErreurMetier):
    def __init__(self, message: str = "Jeton invalide ou expiré"):
        super().__init__(
            "JETON_INVALIDE", message, 401, entetes={"WWW-Authenticate": "Bearer"}
        )


class DroitInsuffisant(ErreurMetier):
    """403 : authentifié, mais sans le droit. À ne pas confondre avec 401."""

    def __init__(self, message: str = "Droits insuffisants"):
        super().__init__("DROIT_INSUFFISANT", message, 403)


class TropDeTentatives(ErreurMetier):
    def __init__(self, minutes: int):
        super().__init__(
            "TROP_DE_TENTATIVES",
            f"Trop de tentatives. Réessayez dans {minutes} minutes.",
            429,
        )


class ParametreManquant(ErreurMetier):
    def __init__(self, nom: str):
        super().__init__(
            "PARAMETRE_MANQUANT",
            f"Le paramètre '{nom}' est obligatoire pour cette opération",
            400,
            {"parametre": nom},
        )
