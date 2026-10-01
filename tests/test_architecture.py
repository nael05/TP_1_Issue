"""Vérifie que les couches sont respectées — séance 7, exercice 1.5.

Un service qui importe FastAPI signale que de la logique HTTP a fui dans la
couche métier : il devient intestable sans client HTTP, et inutilisable depuis
un script.

L'équivalent en ligne de commande :

    grep -r "fastapi" app/services/     # ne doit rien renvoyer
"""

import ast
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
SERVICES = sorted((RACINE / "app" / "services").glob("*.py"))
DEPOTS = sorted((RACINE / "app" / "depots").glob("*.py"))


def modules_importes(fichier: Path) -> set[str]:
    """Les modules réellement importés — les commentaires ne comptent pas."""
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    modules: set[str] = set()

    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            modules.update(alias.name for alias in noeud.names)
        elif isinstance(noeud, ast.ImportFrom) and noeud.module:
            modules.add(noeud.module)

    return modules


def commence_par(modules: set[str], prefixe: str) -> set[str]:
    return {module for module in modules if module == prefixe or module.startswith(f"{prefixe}.")}


@pytest.mark.parametrize("fichier", SERVICES, ids=lambda chemin: chemin.name)
def test_aucun_service_n_importe_fastapi(fichier):
    assert commence_par(modules_importes(fichier), "fastapi") == set()
    assert "HTTPException(" not in fichier.read_text(encoding="utf-8")


@pytest.mark.parametrize("fichier", DEPOTS, ids=lambda chemin: chemin.name)
def test_aucun_depot_n_importe_fastapi(fichier):
    assert commence_par(modules_importes(fichier), "fastapi") == set()


@pytest.mark.parametrize("fichier", DEPOTS, ids=lambda chemin: chemin.name)
def test_un_depot_ne_remonte_pas_vers_les_couches_superieures(fichier):
    """Les dépendances vont dans un seul sens : routeur → service → dépôt."""
    modules = modules_importes(fichier)

    assert commence_par(modules, "app.services") == set()
    assert commence_par(modules, "app.routeurs") == set()


@pytest.mark.parametrize("fichier", SERVICES, ids=lambda chemin: chemin.name)
def test_aucun_service_ne_remonte_vers_les_routeurs(fichier):
    assert commence_par(modules_importes(fichier), "app.routeurs") == set()


def test_main_ne_declare_aucune_route():
    """`main.py` ne fait qu'assembler : configuration, middlewares, routeurs."""
    contenu = (RACINE / "app" / "main.py").read_text(encoding="utf-8")

    for methode in ("@app.get(", "@app.post(", "@app.put(", "@app.patch(", "@app.delete("):
        assert methode not in contenu


def test_tous_les_routeurs_sont_inclus():
    """Une route déclarée dans un routeur non inclus renvoie 404."""
    contenu = (RACINE / "app" / "main.py").read_text(encoding="utf-8")

    for module in (RACINE / "app" / "routeurs").glob("*.py"):
        if module.stem != "__init__":
            assert f"{module.stem}.routeur" in contenu
