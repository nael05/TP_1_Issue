"""Hachage des mots de passe et jetons JWT — séance 5, parties 1 et 2.

Note d'implémentation : le cours utilise `passlib[bcrypt]`. passlib 1.7.4 n'est
plus compatible avec bcrypt >= 4.1 ni avec Python >= 3.13 (le module `crypt` a
été retiré). On appelle donc `bcrypt` directement, avec la même API publique —
`hacher` et `verifier` — et exactement les mêmes propriétés : sel aléatoire
intégré à l'empreinte, et lenteur volontaire.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import configuration

# bcrypt ignore silencieusement ce qui dépasse 72 octets : on tronque
# explicitement pour que le comportement soit visible et prévisible.
LONGUEUR_MAX = 72


def hacher(mot_de_passe: str) -> str:
    """Renvoie une empreinte bcrypt. Deux appels donnent deux résultats différents.

    C'est le sel, aléatoire et stocké dans l'empreinte elle-même : deux
    utilisateurs ayant le même mot de passe ont des empreintes distinctes.
    """
    octets = mot_de_passe.encode("utf-8")[:LONGUEUR_MAX]
    return bcrypt.hashpw(octets, bcrypt.gensalt()).decode("utf-8")


def verifier(mot_de_passe: str, empreinte: str) -> bool:
    """Vérifie un mot de passe. Le sel est retrouvé dans l'empreinte."""
    try:
        return bcrypt.checkpw(
            mot_de_passe.encode("utf-8")[:LONGUEUR_MAX], empreinte.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Empreinte corrompue ou tronquée en base : on refuse, sans lever.
        return False


EMPREINTE_FACTICE = hacher("empreinte-factice-pour-temps-constant")


def verifier_a_temps_constant(mot_de_passe: str, empreinte: str | None) -> bool:
    """Vérifie même quand l'utilisateur n'existe pas.

    Sans cela, une réponse beaucoup plus rapide trahirait l'absence du compte :
    une fuite peut passer par autre chose que le contenu de la réponse.
    """
    if empreinte is None:
        verifier(mot_de_passe, EMPREINTE_FACTICE)
        return False
    return verifier(mot_de_passe, empreinte)


def creer_jeton(donnees: dict, duree_minutes: float | None = None) -> str:
    """Signe un JWT. Signé, pas chiffré : n'y mettez jamais rien de sensible."""
    duree = configuration.duree_jeton_minutes if duree_minutes is None else duree_minutes
    maintenant = datetime.now(timezone.utc)

    a_encoder = donnees.copy()
    a_encoder["iat"] = maintenant
    a_encoder["exp"] = maintenant + timedelta(minutes=duree)

    return jwt.encode(
        a_encoder, configuration.cle_secrete, algorithm=configuration.algorithme_jeton
    )


def decoder_jeton(jeton: str) -> dict | None:
    """Vérifie la signature *et* l'expiration. Renvoie `None` si le jeton est invalide."""
    try:
        return jwt.decode(
            jeton, configuration.cle_secrete, algorithms=[configuration.algorithme_jeton]
        )
    except JWTError:
        return None
