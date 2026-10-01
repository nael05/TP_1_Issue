"""Tests du parcours authentifié et des autorisations — séance 6, exercices 2.5 à 2.7."""

from tests.conftest import BASE, MOT_DE_PASSE


def test_parcours_complet(client):
    """Inscription, connexion, création avec le jeton obtenu."""
    inscription = client.post(
        f"{BASE}/inscription", json={"email": "a@example.com", "mot_de_passe": MOT_DE_PASSE}
    )
    assert inscription.status_code == 201

    connexion = client.post(
        f"{BASE}/connexion", data={"username": "a@example.com", "password": MOT_DE_PASSE}
    )
    assert connexion.status_code == 200
    assert connexion.json()["token_type"] == "bearer"

    jeton = connexion.json()["access_token"]
    creation = client.post(
        f"{BASE}/jeux",
        json={"titre": "Test", "genre": "RPG", "note": 8, "annee": 2020},
        headers={"Authorization": f"Bearer {jeton}"},
    )
    assert creation.status_code == 201


def test_empreinte_jamais_renvoyee(client):
    reponse = client.post(
        f"{BASE}/inscription", json={"email": "b@example.com", "mot_de_passe": MOT_DE_PASSE}
    )

    corps = reponse.json()
    assert "empreinte" not in corps
    assert "mot_de_passe" not in corps


def test_empreinte_stockee_jamais_le_mot_de_passe(client, session):
    from app.tables import Utilisateur

    client.post(
        f"{BASE}/inscription", json={"email": "c@example.com", "mot_de_passe": MOT_DE_PASSE}
    )
    utilisateur = session.query(Utilisateur).filter_by(email="c@example.com").one()

    assert utilisateur.empreinte != MOT_DE_PASSE
    assert utilisateur.empreinte.startswith("$2b$")


def test_mot_de_passe_trop_court_refuse(client):
    reponse = client.post(
        f"{BASE}/inscription", json={"email": "d@example.com", "mot_de_passe": "court"}
    )

    assert reponse.status_code == 422


def test_email_invalide_refuse(client):
    reponse = client.post(
        f"{BASE}/inscription", json={"email": "pas-un-email", "mot_de_passe": MOT_DE_PASSE}
    )

    assert reponse.status_code == 422


def test_email_deja_utilise(client):
    donnees = {"email": "e@example.com", "mot_de_passe": MOT_DE_PASSE}
    client.post(f"{BASE}/inscription", json=donnees)
    reponse = client.post(f"{BASE}/inscription", json=donnees)

    assert reponse.status_code == 409


def test_role_impose_par_le_client_ignore(client, session):
    """Sans cela, n'importe qui s'inscrirait administrateur."""
    from app.tables import Role, Utilisateur

    client.post(
        f"{BASE}/inscription",
        json={"email": "f@example.com", "mot_de_passe": MOT_DE_PASSE, "role": "admin"},
    )
    utilisateur = session.query(Utilisateur).filter_by(email="f@example.com").one()

    assert utilisateur.role == Role.lecteur


def test_les_deux_echecs_de_connexion_sont_indiscernables(client):
    """Distinguer les cas permettrait d'énumérer les comptes inscrits."""
    client.post(
        f"{BASE}/inscription", json={"email": "g@example.com", "mot_de_passe": MOT_DE_PASSE}
    )

    inconnu = client.post(
        f"{BASE}/connexion", data={"username": "inconnu@example.com", "password": MOT_DE_PASSE}
    )
    mauvais = client.post(
        f"{BASE}/connexion", data={"username": "g@example.com", "password": "mauvais-mdp"}
    )

    assert inconnu.status_code == mauvais.status_code == 401
    assert inconnu.json() == mauvais.json()


def test_compte_inactif_refuse_sans_reveler_la_raison(client, session):
    from app.tables import Utilisateur

    client.post(
        f"{BASE}/inscription", json={"email": "h@example.com", "mot_de_passe": MOT_DE_PASSE}
    )
    session.query(Utilisateur).filter_by(email="h@example.com").one().actif = False
    session.commit()

    reponse = client.post(
        f"{BASE}/connexion", data={"username": "h@example.com", "password": MOT_DE_PASSE}
    )

    assert reponse.status_code == 401
    assert reponse.json()["message"] == "Identifiants incorrects"


def test_derniere_connexion_enregistree(client, session):
    from app.tables import Utilisateur

    client.post(
        f"{BASE}/inscription", json={"email": "i@example.com", "mot_de_passe": MOT_DE_PASSE}
    )
    client.post(f"{BASE}/connexion", data={"username": "i@example.com", "password": MOT_DE_PASSE})

    utilisateur = session.query(Utilisateur).filter_by(email="i@example.com").one()
    assert utilisateur.derniere_connexion is not None


def test_blocage_apres_cinq_tentatives(client):
    client.post(
        f"{BASE}/inscription", json={"email": "j@example.com", "mot_de_passe": MOT_DE_PASSE}
    )

    for _ in range(5):
        client.post(f"{BASE}/connexion", data={"username": "j@example.com", "password": "faux"})

    bloquee = client.post(
        f"{BASE}/connexion", data={"username": "j@example.com", "password": MOT_DE_PASSE}
    )

    assert bloquee.status_code == 429
    assert bloquee.json()["code"] == "TROP_DE_TENTATIVES"


def test_profil(client, entetes):
    reponse = client.get(f"{BASE}/moi", headers=entetes)

    assert reponse.status_code == 200
    assert reponse.json()["email"] == "test@example.com"
    assert "empreinte" not in reponse.json()


def test_profil_sans_jeton(client):
    assert client.get(f"{BASE}/moi").status_code == 401


def test_jeton_cesse_de_fonctionner_apres_desactivation(client, session, entetes):
    """Le jeton reste valide cryptographiquement : c'est la vérification en
    base qui coupe l'accès, sans attendre son expiration."""
    from app.tables import Utilisateur

    assert client.get(f"{BASE}/moi", headers=entetes).status_code == 200

    session.query(Utilisateur).filter_by(email="test@example.com").one().actif = False
    session.commit()

    assert client.get(f"{BASE}/moi", headers=entetes).status_code == 401


def test_mes_jeux_ne_montre_que_les_siens(client, deux_utilisateurs):
    entetes_a = {"Authorization": f"Bearer {deux_utilisateurs['a']}"}
    entetes_b = {"Authorization": f"Bearer {deux_utilisateurs['b']}"}

    client.post(
        f"{BASE}/jeux",
        json={"titre": "Jeu de A", "genre": "RPG", "note": 8, "annee": 2020},
        headers=entetes_a,
    )

    assert len(client.get(f"{BASE}/moi/jeux", headers=entetes_a).json()["elements"]) == 1
    assert client.get(f"{BASE}/moi/jeux", headers=entetes_b).json()["elements"] == []


def test_deconnexion(client, entetes):
    reponse = client.post(f"{BASE}/deconnexion", headers=entetes)

    assert reponse.status_code == 200
    assert "jeton" in reponse.json()["message"].lower()
