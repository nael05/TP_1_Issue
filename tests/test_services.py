"""Tests de la couche métier — séance 6, exercice 1.

Ces tests n'utilisent ni serveur, ni HTTP, ni `TestClient` : c'est le bénéfice
de la séparation en couches faite depuis la séance 2.
"""

import pytest

from app.exceptions import (
    DroitInsuffisant,
    JeuIntrouvable,
    ParametreManquant,
    TitreDejaUtilise,
)
from app.modeles.jeux import JeuCreation, JeuMiseAJour
from app.services import jeux as service
from app.tables import Role, Utilisateur


@pytest.fixture
def auteur(session) -> Utilisateur:
    utilisateur = Utilisateur(email="auteur@example.com", empreinte="x")
    session.add(utilisateur)
    session.commit()
    return utilisateur


@pytest.fixture
def catalogue(session, auteur):
    donnees = [
        {"titre": "Celeste", "genre": "Plateforme", "note": 9, "annee": 2018},
        {"titre": "Among Us", "genre": "Party", "note": 6, "annee": 2018},
        {"titre": "Hades", "genre": "Roguelike", "note": 9, "annee": 2020},
        {"titre": "Undertale", "genre": "RPG", "note": 8, "annee": 2015},
        {"titre": "Disco Elysium", "genre": "RPG", "note": 9, "annee": 2019},
    ]
    return [service.creer(session, JeuCreation(**entree), auteur) for entree in donnees]


def test_lister_sans_filtre(session, catalogue):
    elements, total = service.lister(session)

    assert total == 5
    assert len(elements) == 5


def test_filtrer_par_genre(session, catalogue):
    elements, total = service.lister(session, genre="RPG")

    assert total == 2
    assert {jeu.titre for jeu in elements} == {"Undertale", "Disco Elysium"}


def test_filtres_cumulables(session, catalogue):
    _, total = service.lister(session, genre="RPG", note_min=9)

    assert total == 1


def test_recherche_insensible_a_la_casse(session, catalogue):
    _, total = service.lister(session, recherche="cELEste")

    assert total == 1


def test_filtre_sans_resultat_renvoie_une_liste_vide(session, catalogue):
    elements, total = service.lister(session, genre="Simulation")

    assert (elements, total) == ([], 0)


def test_total_suit_les_filtres_pas_la_page(session, catalogue):
    """Le total compte les éléments filtrés — ni le catalogue, ni la page."""
    elements, total = service.lister(session, limite=2)

    assert len(elements) == 2
    assert total == 5


def test_pagination_apres_tri(session, catalogue):
    """L'ordre est : filtrer, trier, paginer. Trier après avoir coupé ne
    trierait que la page."""
    page_1, _ = service.lister(session, tri="titre", limite=2)
    page_2, _ = service.lister(session, tri="titre", saut=2, limite=2)

    assert [jeu.titre for jeu in page_1] == ["Among Us", "Celeste"]
    assert [jeu.titre for jeu in page_2] == ["Disco Elysium", "Hades"]


def test_trouver_leve_si_absent(session):
    with pytest.raises(JeuIntrouvable):
        service.trouver(session, 999)


def test_titre_en_double_refuse(session, auteur, catalogue):
    """La contrainte est appliquée par la base : la tentative est la seule
    approche fiable, une vérification préalable laisserait une fenêtre de
    concurrence entre la lecture et l'insertion."""
    with pytest.raises(TitreDejaUtilise):
        service.creer(
            session,
            JeuCreation(titre="celeste", genre="RPG", note=5, annee=2020),
            auteur,
        )


def test_session_utilisable_apres_le_conflit(session, auteur, catalogue):
    """Le `rollback` après l'IntegrityError : sans lui, toutes les opérations
    suivantes échoueraient, souvent loin de la vraie cause."""
    with pytest.raises(TitreDejaUtilise):
        service.creer(
            session, JeuCreation(titre="Celeste", genre="RPG", note=5, annee=2020), auteur
        )

    apres = service.creer(
        session, JeuCreation(titre="Portal 2", genre="Réflexion", note=10, annee=2011), auteur
    )
    assert apres.id is not None


def test_patch_ne_touche_que_les_champs_envoyes(session, auteur, catalogue):
    jeu = catalogue[0]
    modifie = service.modifier(session, jeu.id, JeuMiseAJour(note=7), auteur)

    assert modifie.note == 7
    assert modifie.titre == "Celeste"
    assert modifie.genre == "Plateforme"


def test_patch_vide_ne_casse_rien(session, auteur, catalogue):
    jeu = catalogue[0]
    inchange = service.modifier(session, jeu.id, JeuMiseAJour(), auteur)

    assert inchange.titre == "Celeste"


def test_put_remplace_tous_les_champs(session, auteur, catalogue):
    jeu = catalogue[0]
    remplace = service.remplacer(
        session,
        jeu.id,
        JeuCreation(titre="Celeste", genre="Action", note=7, annee=2019),
        auteur,
    )

    assert (remplace.genre, remplace.note, remplace.annee) == ("Action", 7, 2019)
    assert remplace.id == jeu.id  # l'identifiant vient du chemin, pas du corps


def test_historique_enregistre_les_champs_modifies(session, auteur, catalogue):
    jeu = catalogue[0]
    service.modifier(session, jeu.id, JeuMiseAJour(note=7), auteur)
    service.modifier(session, jeu.id, JeuMiseAJour(annee=2019), auteur)

    historique = service.historique(session, jeu.id)

    assert [entree.champs for entree in historique] == ["note", "annee"]


def test_proprietaire_vient_du_serveur(session, auteur):
    jeu = service.creer(
        session, JeuCreation(titre="Hollow Knight", genre="Metroidvania", note=9, annee=2017), auteur
    )

    assert jeu.proprietaire_id == auteur.id


def test_un_autre_utilisateur_ne_peut_pas_modifier(session, auteur, catalogue):
    intrus = Utilisateur(email="intrus@example.com", empreinte="x")
    session.add(intrus)
    session.commit()

    with pytest.raises(DroitInsuffisant):
        service.modifier(session, catalogue[0].id, JeuMiseAJour(note=1), intrus)


def test_un_administrateur_peut_modifier_le_jeu_d_un_autre(session, auteur, catalogue):
    admin = Utilisateur(email="admin2@example.com", empreinte="x", role=Role.admin)
    session.add(admin)
    session.commit()

    modifie = service.modifier(session, catalogue[0].id, JeuMiseAJour(note=1), admin)

    assert modifie.note == 1


def test_similaires_sur_un_jeu_absent(session):
    with pytest.raises(JeuIntrouvable):
        service.similaires(session, 999)


def test_voisins(session, catalogue):
    premier = service.voisins(session, catalogue[0].id)
    dernier = service.voisins(session, catalogue[-1].id)

    assert premier["suivant"].id == catalogue[1].id
    assert dernier["suivant"] is None


def test_suppression_en_masse_sans_filtre_refusee(session, catalogue):
    with pytest.raises(ParametreManquant):
        service.supprimer_par_genre(session, None)


def test_suppression_en_masse_par_genre(session, catalogue):
    supprimes = service.supprimer_par_genre(session, "rpg")

    assert supprimes == 2
    assert service.lister(session)[1] == 3


def test_statistiques(session, catalogue):
    stats = service.statistiques(session)

    assert stats["nombre"] == 5
    assert stats["moyenne"] == pytest.approx(8.2)
    assert stats["meilleure_note"] == 9
    assert stats["par_genre"]["RPG"] == 2


def test_statistiques_catalogue_vide(session):
    stats = service.statistiques(session)
    assert stats["nombre"] == 0
    assert stats["moyenne"] == 0.0
