# StorageScope V6.227 — isolation du domaine de restauration des ancrages

**Auteur : Abdelhalim Talbi** — 25 octobre 2026.

## Incident et cause racine

La V6.226 interdisait un ancrage directement dans le répertoire du registre SQLite, mais acceptait un ancrage dans un **sous-répertoire** de ce répertoire (`ledger/backups/checkpoint.json`). Un chemin contenant `..` permettait la même situation. L'ancrage pouvait ainsi être sauvegardé et restauré avec le registre, malgré le contrôle de séparation. Les nouveaux tests ont reproduit le défaut avant correction : 3 échecs sur 4 tests.

## Correction

La validation normalise les répertoires avec `Path.resolve()` et refuse tout répertoire parent d'ancrage égal au répertoire du registre **ou situé dans son sous-arbre**. Cette règle s'applique à la création et à la vérification. Les contrôles V6.226 sur les symlinks, hardlinks, fichiers ordinaires et JSON canonique restent actifs. Un répertoire frère reste accepté ; aucune écriture dans le registre n'est déclenchée par la vérification.

## Schéma conceptuel (non issu d'une capture)

```text
/srv/storage/ledger/replay.sqlite
/srv/storage/ledger/backups/checkpoint.json  -> REJET (même sous-arbre)
/srv/storage/protected/checkpoint.json       -> ADMIS (arbre distinct)
```

## Tests et qualification

- `test_storage_replay_anchor_v6227.py` : 4 tests (création sous-arbre refusée, vérification refusée, traversée `..` refusée, répertoire frère accepté).
- Régressions `test_storage_replay_anchor_v6225.py` et `test_storage_replay_anchor_v6226.py` conservées.
- `qualify_frozen_replay_anchor_v6227.py` : qualification synthétique **dans l'exécutable Windows compilé**, intégrée au workflow `windows-build.yml`.
- Tests locaux Linux après correction : **18/18 ancrage** et **186/186 stockage**. Ce résultat ne qualifie pas Windows ; seule une exécution native complète du workflow sur le commit publié le permet.

## Exploitation et limites

Un arbre distinct ne garantit pas à lui seul des sauvegardes indépendantes. L'opérateur doit stocker l'ancrage dans un domaine protégé, idéalement immuable, distinct de celui du registre. La clé `STORAGESCOPE_REPLAY_ANCHOR_KEY` ne doit jamais être journalisée. Une restauration simultanée du registre et de l'ancrage reste indétectable ; les courses de modification des chemins sous Windows ne sont pas toutes éliminées. Aucun équipement physique ni capture réelle d'interface n'a été testé pour cette évolution.

**Référentiels :** ISO 27001/27040 (intégrité et séparation des preuves), ISO 42010 (justification architecturale), ITIL 4 (gestion des changements). Alignement de conception, pas certification.
