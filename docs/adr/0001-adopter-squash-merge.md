# ADR 0001 : Adopter le squash merge pour les pull requests

- **Statut :** Proposée
- **Date :** 2026-10-06

## Contexte

La PR des statistiques du catalogue vide (#8) a été fusionnée dans `main` avec
la méthode **Squash and merge**. L'équipe doit expliciter cette stratégie pour
que l'historique des prochaines PR reste cohérent et que chacun sache comment
les changements seront intégrés.

## Décision proposée

Utiliser **Squash and merge** pour fusionner les pull requests dans `main`.
Chaque PR sera représentée par un commit regroupant ses changements, avec un
message décrivant le changement livré.

## Options envisagées

### Merge commit

- **Pour :** conserve les commits de la branche et ajoute un commit de fusion
  qui rend visible l'intégration de la PR.
- **Contre :** ajoute des commits de fusion à l'historique, qui peut devenir
  moins linéaire et plus difficile à parcourir.

### Squash and merge

- **Pour :** regroupe les changements de la PR en un commit sur `main`, ce qui
  rend l'historique principal plus concis et permet de retrouver le changement
  livré en un seul commit.
- **Contre :** les commits individuels de la branche ne sont pas conservés
  séparément dans l'historique de `main`, ce qui réduit le détail disponible
  pour retracer les étapes du travail.

### Rebase and merge

- **Pour :** conserve les commits individuels tout en plaçant leur suite après
  les commits de `main`, pour un historique linéaire sans commit de fusion.
- **Contre :** la fusion de la PR est moins visible dans l'historique et le
  rebase réécrit les identifiants des commits de la branche.

## Conséquences

- **Positif :** l'historique de `main` reste concis et chaque commit correspond
  à une PR fusionnée.
- **Négatif :** les commits de travail intermédiaires de la PR ne sont pas
  consultables séparément dans l'historique de `main`.
- **Réexamen :** revoir cette décision si l'équipe a besoin de conserver dans
  `main` les étapes détaillées des commits de chaque PR, ou si le suivi des
  fusions devient plus important que la concision de l'historique.
