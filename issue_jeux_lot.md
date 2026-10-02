# Bug: POST /api/v1/jeux/lot crée une partie des jeux quand l'un d'eux est refusé

## Contexte

L'import en lot sert à l'outil d'administration. Constaté sur `main`.

## Étapes pour reproduire

1. Base peuplée avec `python scripts/peupler.py` (elle contient « Hades »).
2. Se connecter avec `admin@example.com`.
3. `POST /api/v1/jeux/lot` avec trois jeux : « Terraria », « Inside », « hades ».

## Comportement attendu

Rien n'est créé : l'opération est refusée en entier.

## Comportement observé

Réponse `409` :

```json
{"code":"TITRE_DEJA_UTILISE","message":"Un jeu intitulé 'hades' existe déjà","details":{"titre":"hades"}}
```

Mais « Terraria » et « Inside » ont été créés.

## Environnement

- Ubuntu 24.04
- Python 3.12
- SQLite

## Pistes

`service.creer_lot` appelle `creer` en boucle, et chaque `creer` fait son `commit`.

## Réponse API reproduite

```json
{"code":"TITRE_DEJA_UTILISE","message":"Un jeu intitulé 'hades' existe déjà","details":{"titre":"hades"}}
```

## Trace serveur

```text
12:24:02 INFO     api | Connexion réussie pour l'utilisateur 1
12:24:02 INFO     api | POST /api/v1/connexion -> 200 en 188.0 ms
12:24:02 INFO     api | POST /api/v1/jeux/lot -> 409 en 17.1 ms
INFO:     127.0.0.1:57865 - "POST /api/v1/jeux/lot HTTP/1.1" 409 Conflict
12:24:02 INFO     api | GET /api/v1/jeux -> 200 en 7.5 ms
```

## Cause racine

Le code de [app/services/jeux.py](app/services/jeux.py) montre que `creer_lot` applique `creer` de façon itérative et que chaque appel `creer` conclut par un `commit` ou un `session.rollback()`. Il n'y a donc pas de transaction globale pour l'ensemble du lot : les premiers jeux sont déjà validés avant qu'un doublon sur le titre ne déclenche l'exception.

## Labels

- bug
