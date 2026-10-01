"""Tests d'intégration du catalogue — séance 6, partie 2.

Un test d'intégration couvre tout le chemin : routage, validation Pydantic,
dépendances, authentification, accès aux données et sérialisation.
"""

from tests.conftest import BASE


def creer_jeu(client, entetes, **remplacements) -> dict:
    donnees = {"titre": "Celeste", "genre": "Plateforme", "note": 9, "annee": 2018}
    donnees.update(remplacements)
    return client.post(f"{BASE}/jeux", json=donnees, headers=entetes).json()


def test_racine(client):
    reponse = client.get("/")

    assert reponse.status_code == 200
    assert reponse.json()["message"] == "API opérationnelle"


def test_sante(client):
    reponse = client.get("/sante")

    assert reponse.status_code == 200
    assert reponse.json()["base"] == "ok"


def test_lister_renvoie_une_page(client):
    reponse = client.get(f"{BASE}/jeux")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["elements"] == []
    assert corps["total"] == 0
    assert corps["pages_totales"] == 0


def test_lire_jeu_absent(client):
    reponse = client.get(f"{BASE}/jeux/99999")

    assert reponse.status_code == 404
    assert reponse.json()["code"] == "JEU_INTROUVABLE"


def test_identifiant_invalide(client):
    """Aucune ligne écrite pour ce cas : l'annotation `jeu_id: int` suffit."""
    reponse = client.get(f"{BASE}/jeux/abc")

    assert reponse.status_code == 422
    assert reponse.json()["code"] == "VALIDATION_ECHOUEE"


def test_creation_refusee_sans_jeton(client, jeu_exemple):
    reponse = client.post(f"{BASE}/jeux", json=jeu_exemple)

    assert reponse.status_code == 401


def test_creation_refusee_avec_un_jeton_invalide(client, jeu_exemple):
    reponse = client.post(
        f"{BASE}/jeux", json=jeu_exemple, headers={"Authorization": "Bearer nimporte.quoi"}
    )

    assert reponse.status_code == 401


def test_creation(client, entetes, jeu_exemple):
    reponse = client.post(f"{BASE}/jeux", json=jeu_exemple, headers=entetes)

    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["titre"] == "Celeste"
    assert "id" in corps
    assert corps["date_creation"] is not None


def test_identifiant_impose_par_le_client_ignore(client, entetes, jeu_exemple):
    """Ce qui n'est pas dans le modèle d'entrée n'entre pas."""
    reponse = client.post(
        f"{BASE}/jeux",
        json={**jeu_exemple, "id": 999, "proprietaire_id": 42, "date_creation": "1990-01-01"},
        headers=entetes,
    )

    corps = reponse.json()
    assert corps["id"] != 999
    assert corps["proprietaire_id"] != 42
    assert not corps["date_creation"].startswith("1990")


def test_champ_interne_jamais_renvoye(client, entetes, session, jeu_exemple):
    """`notes_internes` existe en base mais pas dans `JeuSortie` : le
    `response_model` filtre réellement la réponse."""
    from app.tables import Jeu

    cree = creer_jeu(client, entetes)
    session.get(Jeu, cree["id"]).notes_internes = "à ne jamais exposer"
    session.commit()

    corps = client.get(f"{BASE}/jeux/{cree['id']}").json()

    assert "notes_internes" not in corps


def test_doublon_de_titre(client, entetes, jeu_exemple):
    client.post(f"{BASE}/jeux", json=jeu_exemple, headers=entetes)
    reponse = client.post(f"{BASE}/jeux", json=jeu_exemple, headers=entetes)

    # 409 et non 400 : la requête est bien formée, elle entre en conflit avec
    # l'état actuel.
    assert reponse.status_code == 409
    assert reponse.json()["code"] == "TITRE_DEJA_UTILISE"


def test_creation_en_lot(client, entetes):
    reponse = client.post(
        f"{BASE}/jeux/lot",
        json=[
            {"titre": "Hades", "genre": "Roguelike", "note": 9, "annee": 2020},
            {"titre": "Undertale", "genre": "RPG", "note": 8, "annee": 2015},
        ],
        headers=entetes,
    )

    assert reponse.status_code == 201
    assert len(reponse.json()) == 2


def test_patch_preserve_les_champs_non_envoyes(client, entetes):
    cree = creer_jeu(client, entetes)
    reponse = client.patch(f"{BASE}/jeux/{cree['id']}", json={"note": 7}, headers=entetes)

    corps = reponse.json()
    assert corps["note"] == 7
    assert corps["titre"] == "Celeste"
    assert corps["annee"] == 2018


def test_put_exige_tous_les_champs(client, entetes):
    cree = creer_jeu(client, entetes)
    reponse = client.put(
        f"{BASE}/jeux/{cree['id']}", json={"titre": "Celeste", "note": 7}, headers=entetes
    )

    assert reponse.status_code == 422


def test_patch_note_seule(client, entetes):
    cree = creer_jeu(client, entetes)
    reponse = client.patch(f"{BASE}/jeux/{cree['id']}/note", json={"note": 3}, headers=entetes)

    assert reponse.json()["note"] == 3


def test_suppression_puis_seconde_suppression(client, entetes):
    cree = creer_jeu(client, entetes)

    premiere = client.delete(f"{BASE}/jeux/{cree['id']}", headers=entetes)
    seconde = client.delete(f"{BASE}/jeux/{cree['id']}", headers=entetes)

    assert premiere.status_code == 204
    assert premiere.content == b""  # le statut 204 interdit tout corps
    assert seconde.status_code == 404


def test_historique(client, entetes):
    cree = creer_jeu(client, entetes)
    client.patch(f"{BASE}/jeux/{cree['id']}", json={"note": 7}, headers=entetes)

    historique = client.get(f"{BASE}/jeux/{cree['id']}/historique").json()

    assert len(historique) == 1
    assert historique[0]["champs"] == ["note"]


def test_filtres_et_pagination(client, entetes):
    for indice, titre in enumerate(["Hades", "Undertale", "Disco Elysium"]):
        creer_jeu(client, entetes, titre=titre, genre="RPG", note=7 + indice, annee=2015 + indice)

    corps = client.get(f"{BASE}/jeux", params={"genre": "RPG", "note_min": 8, "limite": 1}).json()

    assert corps["total"] == 2
    assert len(corps["elements"]) == 1
    assert corps["pages_totales"] == 2


def test_contrainte_de_requete_hors_bornes(client):
    reponse = client.get(f"{BASE}/jeux", params={"note_min": 42})

    assert reponse.status_code == 422


def test_statistiques(client, entetes):
    creer_jeu(client, entetes, titre="Hades", genre="Roguelike", note=9, annee=2020)
    creer_jeu(client, entetes, titre="Among Us", genre="Party", note=5, annee=2018)

    corps = client.get(f"{BASE}/jeux/statistiques").json()

    assert corps["nombre"] == 2
    assert corps["moyenne"] == 7.0
    assert corps["par_genre"] == {"Party": 1, "Roguelike": 1}


def test_editeur_imbrique_dans_la_reponse(client, entetes, editeur):
    cree = creer_jeu(client, entetes, editeur_id=editeur.id)

    assert cree["editeur"]["nom"] == "Maddy Makes Games"
    assert cree["editeur"]["pays"] == "Canada"


def test_editeur_inexistant_refuse(client, entetes, jeu_exemple):
    reponse = client.post(f"{BASE}/jeux", json={**jeu_exemple, "editeur_id": 999}, headers=entetes)

    assert reponse.status_code == 404
    assert reponse.json()["code"] == "EDITEUR_INTROUVABLE"


def test_erreur_inattendue_ne_divulgue_rien(client_sans_relance):
    """Le détail part dans les journaux, le client reçoit un message générique."""
    reponse = client_sans_relance.get(f"{BASE}/demo/erreur")

    assert reponse.status_code == 500
    corps = reponse.json()
    assert corps == {"code": "ERREUR_INTERNE", "message": "Une erreur est survenue"}
    assert "ZeroDivision" not in reponse.text


def test_toutes_les_erreurs_partagent_le_meme_format(client, jeu_exemple):
    """Y compris celles levées par le framework avant notre code."""
    reponses = [
        client.get(f"{BASE}/jeux/99999"),                # notre exception métier
        client.get(f"{BASE}/jeux/abc"),                  # validation Pydantic
        client.post(f"{BASE}/jeux", json=jeu_exemple),   # OAuth2PasswordBearer
        client.get(f"{BASE}/route-inexistante"),         # Starlette
    ]

    for reponse in reponses:
        corps = reponse.json()
        assert set(corps) == {"code", "message", "details"}, reponse.url
        assert "detail" not in corps


def test_appel_sans_jeton_annonce_le_schema(client, jeu_exemple):
    """L'en-tête WWW-Authenticate indique au client comment s'authentifier."""
    reponse = client.post(f"{BASE}/jeux", json=jeu_exemple)

    assert reponse.status_code == 401
    assert reponse.headers["WWW-Authenticate"] == "Bearer"


def test_authentification_optionnelle_et_en_tete_client():
    """Deux dépendances de la séance 4/5 testées directement.

    `utilisateur_optionnel` ne lève pas sans jeton ; `verifier_client` exige
    l'en-tête `X-Client-Id` — c'est le même mécanisme que l'authentification,
    avec un identifiant de client au lieu d'un jeton.
    """
    import pytest

    from app.dependances import verifier_client
    from app.exceptions import ErreurMetier
    from app.services.utilisateurs import utilisateur_optionnel_du_jeton

    assert utilisateur_optionnel_du_jeton(None, None) is None
    assert utilisateur_optionnel_du_jeton(None, "jeton.invalide.xxx") is None

    assert verifier_client("client-42") == "client-42"
    with pytest.raises(ErreurMetier):
        verifier_client(None)


def test_pagination_borne_la_limite():
    """Sans plafond, un client peut demander un million d'éléments."""
    from app.dependances import Pagination

    assert Pagination(saut=-5, limite=10_000).limite == 100
    assert Pagination(saut=-5, limite=10_000).saut == 0
    assert Pagination(limite=0).limite == 1


def test_routes_asynchrones_de_demonstration(client):
    """Les deux routes non bloquantes répondent ; la troisième est documentée
    comme gelant le serveur, on ne l'appelle donc pas dans les tests."""
    assert client.get(f"{BASE}/demo/correct", params={"duree": 0}).status_code == 200
    assert client.get(f"{BASE}/demo/en-fil", params={"duree": 0}).status_code == 200
