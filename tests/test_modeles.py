"""Tests des modèles Pydantic — séance 3.

On teste **nos** règles : validateurs, normalisation, champs calculés. Pas le
fonctionnement de Pydantic lui-même.
"""

import pytest
from pydantic import ValidationError

from app.modeles.commun import Page
from app.modeles.jeux import JeuCreation, JeuMiseAJour, JeuResume


def creation(**remplacements) -> dict:
    donnees = {"titre": "Celeste", "genre": "Plateforme", "note": 9, "annee": 2018}
    donnees.update(remplacements)
    return donnees


def test_titre_nettoye_avant_la_route():
    """La validation a lieu avant l'appel de la fonction : les données
    arrivent déjà nettoyées, et aucune route ne peut l'oublier."""
    assert JeuCreation(**creation(titre="  Celeste  ")).titre == "Celeste"


def test_titre_vide_refuse():
    with pytest.raises(ValidationError):
        JeuCreation(**creation(titre="   "))


@pytest.mark.parametrize("note", [-1, 11, 100])
def test_note_hors_bornes_refusee(note):
    with pytest.raises(ValidationError):
        JeuCreation(**creation(note=note))


def test_genre_hors_enumeration_refuse():
    with pytest.raises(ValidationError):
        JeuCreation(**creation(genre="Inexistant"))


def test_code_editeur_format():
    assert JeuCreation(**creation(code_editeur="MMG-2018")).code_editeur == "MMG-2018"

    with pytest.raises(ValidationError):
        JeuCreation(**creation(code_editeur="mmg-2018"))

    # Sans `^` et `$`, cette valeur passerait : l'expression chercherait une
    # correspondance *quelque part* dans la chaîne.
    with pytest.raises(ValidationError):
        JeuCreation(**creation(code_editeur="XXMMG-2018YY"))


def test_tags_normalises_sans_perdre_l_ordre():
    jeu = JeuCreation(**creation(tags=["  Indé ", "DIFFICILE", "indé", ""]))

    assert jeu.tags == ["indé", "difficile"]


def test_tags_par_defaut_non_partages():
    """`default_factory` : deux instances ne partagent pas la même liste."""
    premier, second = JeuCreation(**creation()), JeuCreation(**creation(titre="Hades"))
    premier.tags.append("fuite")

    assert second.tags == []


def test_regle_croisee_note_et_annee():
    """Une règle qui porte sur deux champs exige `model_validator`."""
    with pytest.raises(ValidationError):
        JeuCreation(**creation(note=10, annee=2030))


def test_champs_inconnus_ignores():
    """Ce qui n'est pas dans le modèle n'entre pas : la protection est
    structurelle, pas défensive."""
    jeu = JeuCreation(**creation(), **{"id": 999, "proprietaire_id": 42})

    assert not hasattr(jeu, "id")
    assert not hasattr(jeu, "proprietaire_id")


def test_mise_a_jour_distingue_absent_et_none():
    """`exclude_unset=True` est toute la différence entre « modifier la note »
    et « modifier la note et effacer le reste »."""
    partiel = JeuMiseAJour(note=10)

    assert partiel.model_dump(exclude_unset=True) == {"note": 10}
    assert partiel.model_dump()["titre"] is None


@pytest.mark.parametrize(
    "total, limite, attendu",
    [(0, 20, 0), (1, 20, 1), (20, 20, 1), (21, 20, 2), (101, 20, 6)],
)
def test_pages_totales(total, limite, attendu):
    page = Page[JeuResume](elements=[], total=total, saut=0, limite=limite)

    assert page.pages_totales == attendu
