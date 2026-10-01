FROM python:3.12-slim

# Sans PYTHONUNBUFFERED, Python tamponne la sortie : les journaux n'apparaissent
# qu'à l'arrêt du conteneur — ou jamais s'il est tué.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

# Les dépendances AVANT le code : Docker met chaque étape en cache, et le code
# change bien plus souvent que les dépendances. Inverser ces deux blocs
# réinstalle tout à chaque modification. C'est l'optimisation la plus rentable
# d'un Dockerfile, et elle tient à l'ordre de deux instructions.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

# Après les RUN qui ont besoin de privilèges. Par défaut un conteneur s'exécute
# en root : si l'application est compromise, l'attaquant l'est aussi.
RUN useradd --create-home application
USER application

EXPOSE 8000

# `fastapi run`, jamais `fastapi dev` : pas de rechargement en production.
# `--host 0.0.0.0` : lié à 127.0.0.1, rien n'entrerait depuis l'extérieur.
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
