"""Tests du hachage et des jetons — séance 6, exercice 1.5."""

import time

import pytest

from app.securite import creer_jeton, decoder_jeton, hacher, verifier


def test_empreinte_differente_du_mot_de_passe():
    assert hacher("motdepasse") != "motdepasse"


def test_verification_reussie():
    assert verifier("motdepasse", hacher("motdepasse")) is True


def test_verification_echouee():
    assert verifier("mauvais", hacher("motdepasse")) is False


def test_deux_empreintes_differentes():
    """Vérifie la présence du sel : c'est une propriété réellement testable."""
    assert hacher("motdepasse") != hacher("motdepasse")


def test_empreinte_illisible_ne_leve_pas():
    assert verifier("motdepasse", "pas-une-empreinte") is False


def test_jeton_contient_ce_qu_on_y_met():
    charge = decoder_jeton(creer_jeton({"sub": "42", "role": "admin"}))

    assert charge is not None
    assert charge["sub"] == "42"
    assert charge["role"] == "admin"
    assert "exp" in charge and "iat" in charge


def test_jeton_modifie_refuse():
    """Une charge utile altérée invalide la signature."""
    jeton = creer_jeton({"sub": "1"})
    entete, charge, signature = jeton.split(".")
    altere = f"{entete}.{charge[:-2]}XY.{signature}"

    assert decoder_jeton(altere) is None


def test_jeton_autre_cle_refuse(monkeypatch):
    jeton = creer_jeton({"sub": "1"})
    monkeypatch.setattr("app.securite.configuration.cle_secrete", "une-autre-cle")

    assert decoder_jeton(jeton) is None


def test_jeton_deja_expire_refuse():
    """`jwt.decode` vérifie l'expiration en plus de la signature : il n'y a
    aucune ligne à écrire pour cela."""
    assert decoder_jeton(creer_jeton({"sub": "1"}, duree_minutes=-1)) is None


def test_jeton_expire_pendant_l_attente():
    # `exp` est stocké en secondes entières : on prend une marge confortable
    # pour que le test ne dépende pas de la fraction de seconde courante.
    jeton = creer_jeton({"sub": "1"}, duree_minutes=0.01)  # 0,6 seconde
    time.sleep(2)

    assert decoder_jeton(jeton) is None


def test_jeton_lisible_sans_la_cle():
    """Un JWT est signé, pas chiffré : sa charge utile est publique.

    C'est pourquoi on n'y met jamais rien de sensible.
    """
    import base64
    import json

    jeton = creer_jeton({"sub": "7", "role": "lecteur"})
    charge = jeton.split(".")[1]
    charge += "=" * (-len(charge) % 4)
    lisible = json.loads(base64.urlsafe_b64decode(charge))

    assert lisible["sub"] == "7"


@pytest.mark.parametrize("mot_de_passe", ["a" * 100, "éàü" * 30, "court"])
def test_hachage_supporte_les_cas_limites(mot_de_passe):
    assert verifier(mot_de_passe, hacher(mot_de_passe)) is True
