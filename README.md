# API catalogue de jeux

API REST pour gérer un catalogue de jeux vidéo, avec authentification, gestion des éditeurs, statistiques et administration.

## Prérequis

- Python 3.12
- PostgreSQL 16 ou une base locale compatible
- Git
- Un terminal PowerShell, CMD ou bash

## Démarrage rapide

1. Créez et activez un environnement virtuel.
2. Installez les dépendances.
3. Copiez le fichier de configuration et remplissez les variables requises.
4. Lancez l’API.

```bash
py -m venv .venv
# PowerShell
. .\.venv\Scripts\Activate.ps1
# Bash / zsh
# source .venv/bin/activate

python -m pip install -r requirements.txt
copy .env.example .env
# puis éditez .env pour remplacer :
# - DATABASE_URL avec l’URL de votre base PostgreSQL
# - CLE_SECRETE avec une clé secrète aléatoire

python -m uvicorn app.main:app --reload
```

Ouvrez ensuite http://localhost:8000/docs : la documentation Swagger de l’API doit s’afficher avec la liste des routes.
