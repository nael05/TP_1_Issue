"""Tests des éditeurs et de la relation — séance 4, partie 6."""

from tests.conftest import BASE


def test_lister_editeurs(client, editeur):
    reponse = client.get(f"{BASE}/editeurs")

    assert reponse.status_code == 200
    assert reponse.json()["total"] == 1


def test_lire_editeur(client, editeur):
    reponse = client.get(f"{BASE}/editeurs/{editeur.id}")

    assert reponse.status_code == 200
    assert reponse.json()["nom"] == "Maddy Makes Games"


def test_editeur_absent(client):
    reponse = client.get(f"{BASE}/editeurs/999")

    assert reponse.status_code == 404
    assert reponse.json()["code"] == "EDITEUR_INTROUVABLE"


def test_creation_reservee_aux_administrateurs(client, entetes):
    reponse = client.post(f"{BASE}/editeurs", json={"nom": "Nintendo"}, headers=entetes)

    assert reponse.status_code == 403


def test_creation_par_un_administrateur(client, entetes_admin):
    reponse = client.post(
        f"{BASE}/editeurs", json={"nom": "  Nintendo  ", "pays": "Japon"}, headers=entetes_admin
    )

    assert reponse.status_code == 201
    assert reponse.json()["nom"] == "Nintendo"  # nettoyé par le validateur


def test_editeur_en_double_refuse(client, entetes_admin, editeur):
    reponse = client.post(
        f"{BASE}/editeurs", json={"nom": "Maddy Makes Games"}, headers=entetes_admin
    )

    assert reponse.status_code == 409


def test_jeux_d_un_editeur(client, entetes, editeur):
    client.post(
        f"{BASE}/jeux",
        json={
            "titre": "Celeste",
            "genre": "Plateforme",
            "note": 9,
            "annee": 2018,
            "editeur_id": editeur.id,
        },
        headers=entetes,
    )

    reponse = client.get(f"{BASE}/editeurs/{editeur.id}/jeux")

    assert reponse.status_code == 200
    assert [jeu["titre"] for jeu in reponse.json()] == ["Celeste"]


def test_jeux_d_un_editeur_absent(client):
    assert client.get(f"{BASE}/editeurs/999/jeux").status_code == 404


def test_suppression_par_un_administrateur(client, entetes_admin, editeur):
    reponse = client.delete(f"{BASE}/editeurs/{editeur.id}", headers=entetes_admin)

    assert reponse.status_code == 204
    assert client.get(f"{BASE}/editeurs/{editeur.id}").status_code == 404


def test_le_nombre_de_requetes_ne_depend_pas_du_nombre_de_jeux(client, entetes, editeur, session):
    """Détection du N+1 : on compte les requêtes SQL réellement émises.

    Sans `selectinload`, chaque jeu déclencherait une requête supplémentaire
    pour charger son éditeur. Le symptôme : un nombre de requêtes qui croît
    avec le nombre de résultats.
    """
    from sqlalchemy import event

    for indice in range(6):
        client.post(
            f"{BASE}/jeux",
            json={
                "titre": f"Jeu {indice}",
                "genre": "RPG",
                "note": 8,
                "annee": 2020,
                "editeur_id": editeur.id,
            },
            headers=entetes,
        )

    requetes: list[str] = []

    def compter(conn, curseur, instruction, *reste):
        requetes.append(instruction)

    event.listen(session.bind, "before_cursor_execute", compter)
    try:
        reponse = client.get(f"{BASE}/jeux", params={"limite": 6})
    finally:
        event.remove(session.bind, "before_cursor_execute", compter)

    assert reponse.json()["total"] == 6
    # Une requête pour les jeux, une pour les éditeurs, une pour le comptage.
    # Sans chargement anticipé, on en compterait une par jeu en plus.
    assert len(requetes) <= 4, requetes
