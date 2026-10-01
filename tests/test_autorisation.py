"""Tests d'autorisation — le seul groupe qui vérifie une propriété de sécurité.

Les autres tests vérifient que ce qui doit marcher marche. Ceux-ci vérifient
que ce qui doit être refusé l'est — et une faille de propriété ne se manifeste
jamais quand on teste avec un seul compte.
"""

from tests.conftest import BASE


def creer_jeu_de_a(client, deux_utilisateurs) -> dict:
    return client.post(
        f"{BASE}/jeux",
        json={"titre": "Jeu de A", "genre": "RPG", "note": 8, "annee": 2020},
        headers={"Authorization": f"Bearer {deux_utilisateurs['a']}"},
    ).json()


def test_un_utilisateur_ne_modifie_pas_le_jeu_d_un_autre(client, deux_utilisateurs):
    """Référence directe non sécurisée à un objet : première vulnérabilité du
    classement OWASP pour les API."""
    jeu = creer_jeu_de_a(client, deux_utilisateurs)

    reponse = client.patch(
        f"{BASE}/jeux/{jeu['id']}",
        json={"note": 1},
        headers={"Authorization": f"Bearer {deux_utilisateurs['b']}"},
    )

    assert reponse.status_code == 403
    assert reponse.json()["code"] == "DROIT_INSUFFISANT"


def test_un_utilisateur_ne_supprime_pas_le_jeu_d_un_autre(client, deux_utilisateurs):
    jeu = creer_jeu_de_a(client, deux_utilisateurs)

    reponse = client.delete(
        f"{BASE}/jeux/{jeu['id']}",
        headers={"Authorization": f"Bearer {deux_utilisateurs['b']}"},
    )

    assert reponse.status_code == 403


def test_le_proprietaire_peut_modifier(client, deux_utilisateurs):
    jeu = creer_jeu_de_a(client, deux_utilisateurs)

    reponse = client.patch(
        f"{BASE}/jeux/{jeu['id']}",
        json={"note": 1},
        headers={"Authorization": f"Bearer {deux_utilisateurs['a']}"},
    )

    assert reponse.status_code == 200


def test_401_et_403_sont_distincts(client, deux_utilisateurs):
    """401 : vous n'êtes pas authentifié. 403 : vous l'êtes, sans le droit."""
    jeu = creer_jeu_de_a(client, deux_utilisateurs)

    sans_jeton = client.patch(f"{BASE}/jeux/{jeu['id']}", json={"note": 1})
    autre_compte = client.patch(
        f"{BASE}/jeux/{jeu['id']}",
        json={"note": 1},
        headers={"Authorization": f"Bearer {deux_utilisateurs['b']}"},
    )

    assert sans_jeton.status_code == 401
    assert autre_compte.status_code == 403


def test_routeur_admin_refuse_un_simple_lecteur(client, entetes):
    assert client.get(f"{BASE}/admin/utilisateurs", headers=entetes).status_code == 403


def test_routeur_admin_refuse_sans_jeton(client):
    assert client.get(f"{BASE}/admin/utilisateurs").status_code == 401


def test_routeur_admin_accepte_un_administrateur(client, entetes_admin):
    reponse = client.get(f"{BASE}/admin/utilisateurs", headers=entetes_admin)

    assert reponse.status_code == 200
    assert reponse.json()["total"] >= 1


def test_un_administrateur_modifie_le_jeu_d_un_autre(client, deux_utilisateurs, entetes_admin):
    jeu = creer_jeu_de_a(client, deux_utilisateurs)

    reponse = client.patch(f"{BASE}/jeux/{jeu['id']}", json={"note": 1}, headers=entetes_admin)

    assert reponse.status_code == 200


def test_reinitialisation_protegee(client, entetes):
    """Une route capable de détruire toutes les données ne reste jamais ouverte."""
    assert client.post(f"{BASE}/admin/reinitialiser").status_code == 401
    assert client.post(f"{BASE}/admin/reinitialiser", headers=entetes).status_code == 403


def test_suppression_en_masse_sans_genre_refusee(client, entetes_admin):
    reponse = client.delete(f"{BASE}/admin/jeux", headers=entetes_admin)

    assert reponse.status_code == 400
    assert reponse.json()["code"] == "PARAMETRE_MANQUANT"


def test_changement_de_role(client, entetes_admin, entetes, session):
    from app.tables import Utilisateur

    cible = session.query(Utilisateur).filter_by(email="test@example.com").one()
    reponse = client.patch(
        f"{BASE}/admin/utilisateurs/{cible.id}/role",
        json={"role": "editeur"},
        headers=entetes_admin,
    )

    assert reponse.status_code == 200
    assert reponse.json()["role"] == "editeur"


def test_activation_et_desactivation_par_un_administrateur(client, entetes_admin, session):
    from app.tables import Utilisateur

    client.post(
        f"{BASE}/inscription", json={"email": "cible@example.com", "mot_de_passe": "motdepasse123"}
    )
    cible = session.query(Utilisateur).filter_by(email="cible@example.com").one()

    reponse = client.patch(
        f"{BASE}/admin/utilisateurs/{cible.id}/activation",
        params={"actif": False},
        headers=entetes_admin,
    )

    assert reponse.status_code == 200
    assert reponse.json()["actif"] is False


def test_role_sur_un_compte_inexistant(client, entetes_admin):
    reponse = client.patch(
        f"{BASE}/admin/utilisateurs/9999/role", json={"role": "admin"}, headers=entetes_admin
    )

    assert reponse.status_code == 404


def test_suppression_en_masse_par_genre(client, entetes_admin):
    for titre in ("Undertale", "Disco Elysium"):
        client.post(
            f"{BASE}/jeux",
            json={"titre": titre, "genre": "RPG", "note": 8, "annee": 2019},
            headers=entetes_admin,
        )

    reponse = client.delete(f"{BASE}/admin/jeux", params={"genre": "RPG"}, headers=entetes_admin)

    assert reponse.status_code == 200
    assert "2" in reponse.json()["message"]
    assert client.get(f"{BASE}/jeux").json()["total"] == 0


def test_reinitialisation_restaure_le_catalogue(client, entetes_admin):
    reponse = client.post(f"{BASE}/admin/reinitialiser", headers=entetes_admin)

    assert reponse.status_code == 200
    assert client.get(f"{BASE}/jeux").json()["total"] == 8
