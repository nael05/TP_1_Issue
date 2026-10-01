"""Configuration partagée des tests — séance 6, partie 3.

Un test doit être **isolé** et **reproductible** : le même résultat à chaque
exécution, dans n'importe quel ordre.
"""

import os

# Avant tout import de `app` : `app.config` lit l'environnement au chargement,
# et `app.base_donnees` crée le moteur dans la foulée. Sans ces deux lignes,
# les tests se connecteraient à la base de développement.
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("CLE_SECRETE", "cle-de-test-uniquement")
os.environ.setdefault("ENVIRONNEMENT", "test")
os.environ.setdefault("NIVEAU_JOURNAL", "WARNING")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.base_donnees import Base, obtenir_session  # noqa: E402
from app.main import app  # noqa: E402
from app.securite import hacher  # noqa: E402
from app.services import tentatives  # noqa: E402
from app.tables import Editeur, Role, Utilisateur  # noqa: E402  (enregistre les tables)

BASE = "/api/v1"

# `sqlite://` sans chemin : base en mémoire, rien n'est écrit sur disque.
# `StaticPool` est indispensable — sans lui, chaque connexion obtiendrait sa
# *propre* base vide, et les données écrites disparaîtraient entre deux appels.
engine_test = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionTest = sessionmaker(bind=engine_test, autoflush=False)


@pytest.fixture
def session():
    """Tables créées avant, supprimées après : chaque test repart de zéro."""
    Base.metadata.create_all(bind=engine_test)
    session = SessionTest()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)
        tentatives.reinitialiser()


@pytest.fixture
def client(session):
    """`dependency_overrides` remplace la dépendance de session le temps du test.

    L'application utilise la base de test sans qu'une seule ligne de code
    applicatif ne change.
    """

    def remplacer_session():
        yield session

    app.dependency_overrides[obtenir_session] = remplacer_session
    yield TestClient(app)
    # Placé après le `yield` : s'exécute même si le test échoue. Sans ce
    # nettoyage, le remplacement persisterait pour les tests suivants.
    app.dependency_overrides.clear()


@pytest.fixture
def client_sans_relance(session):
    """Même client, mais sans relancer les exceptions serveur.

    Nécessaire pour vérifier ce que reçoit *le client* sur une erreur 500.
    """

    def remplacer_session():
        yield session

    app.dependency_overrides[obtenir_session] = remplacer_session
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# --- Utilisateurs et jetons -------------------------------------------------

MOT_DE_PASSE = "motdepasse123"


def _inscrire_et_connecter(client, email: str) -> str:
    client.post(f"{BASE}/inscription", json={"email": email, "mot_de_passe": MOT_DE_PASSE})
    reponse = client.post(
        f"{BASE}/connexion",
        # `data=` et non `json=` : OAuth2PasswordRequestForm attend un
        # formulaire. Avec `json=`, on obtient un 422 sur des champs pourtant
        # envoyés — c'est le blocage le plus fréquent de l'exercice.
        data={"username": email, "password": MOT_DE_PASSE},
    )
    return reponse.json()["access_token"]


@pytest.fixture
def jeton(client):
    return _inscrire_et_connecter(client, "test@example.com")


@pytest.fixture
def entetes(jeton):
    return {"Authorization": f"Bearer {jeton}"}


@pytest.fixture
def deux_utilisateurs(client):
    """Le test de propriété a besoin de deux comptes : la faille ne se voit pas
    avec un seul."""
    return {nom: _inscrire_et_connecter(client, f"{nom}@example.com") for nom in ("a", "b")}


@pytest.fixture
def entetes_admin(client, session):
    jeton_admin = _inscrire_et_connecter(client, "admin@example.com")
    utilisateur = session.query(Utilisateur).filter_by(email="admin@example.com").one()
    utilisateur.role = Role.admin
    session.commit()
    return {"Authorization": f"Bearer {jeton_admin}"}


# --- Données ----------------------------------------------------------------


@pytest.fixture
def jeu_exemple() -> dict:
    return {"titre": "Celeste", "genre": "Plateforme", "note": 9, "annee": 2018}


@pytest.fixture
def editeur(session) -> Editeur:
    editeur = Editeur(nom="Maddy Makes Games", pays="Canada")
    session.add(editeur)
    session.commit()
    session.refresh(editeur)
    return editeur


@pytest.fixture
def utilisateur_en_base(session) -> Utilisateur:
    utilisateur = Utilisateur(email="direct@example.com", empreinte=hacher(MOT_DE_PASSE))
    session.add(utilisateur)
    session.commit()
    session.refresh(utilisateur)
    return utilisateur
