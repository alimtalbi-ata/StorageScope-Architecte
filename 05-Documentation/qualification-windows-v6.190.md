# StorageScope — Qualification Windows V6.190 (23 octobre 2026)

**Auteur : Abdelhalim Talbi. Statut : ÉCHEC de qualification Windows.**
Cette note documente les exécutions réelles de GitHub Actions, et non des simulations.
La version applicative dans `07-Manifestes/VERSION` est `6.108`; V6.190 désigne ce cycle de correctifs.

## Corrections réellement publiées

- `d80cfc419` : contrôle de `$?` et `$LASTEXITCODE` (réinitialisé) après le preflight et le moteur Windows.
- `eaf3b08d6` : contrôles équivalents pour le build et le smoke test installateur dans le workflow.
- `e827e358b` : ancien contrat v6.35 préservé, avec version minimale, alignement source/manifeste/Inno et préflight fail-closed ; aucune suppression de test.
- `aa9e18b71` : journaux complets de chaque sous-processus unittest conservés, avec taille et SHA-256 dans le rapport JSON.
- `ad695503b` : deux tests fonctionnels sur fixtures isolées, l'un PASS et l'autre FAIL volontaire, contrôlant les journaux et leurs empreintes.
- `49c25c584` : harmonisation des tests v6.92/v6.98 pour vérifier explicitement l'absence de `$LASTEXITCODE` périmé, au lieu d'interdire les vérifications natives.

## Résultats GitHub Actions vérifiés

| Exécution | Suite principale | Suite imbriquée | Conclusion |
|---|---|---|---|
| [#39927960619](https://github.com/alimtalbi-ata/StorageScope-Architecte/actions/runs/39927960619) | 1 396 tests ; 65 failures ; 0 errors | 8 PASS | FAIL |
| [#39932788870](https://github.com/alimtalbi-ata/StorageScope-Architecte/actions/runs/39932788870) | 1 399 tests ; 61 failures ; 0 errors | 8 PASS | FAIL |
| [#39933148185](https://github.com/alimtalbi-ata/StorageScope-Architecte/actions/runs/39933148185) | **1 399 tests ; 59 failures ; 0 errors** | **8 PASS** | **FAIL** |

La CI gouvernance du dernier commit est PASS. Elle ne prouve pas la compilation Windows.

La CI #39933148185 a produit l'artefact `StorageScope-Windows-DIAGNOSTICS` (ID `12492861533`, 44 687 octets compressés, SHA-256 de l'archive GitHub : `b8c98839d1335d1b1eeb684cd21f7270991c32660f2e63e1cdbda531992c6af9`).

## Diagnostic de la suite principale

Sur l'exécution intermédiaire à 61 échecs, le regroupement **heuristique**, à confirmer test par test, est : 45 attentes de versions historiques figées, 14 contrats statiques de scripts obsolètes, 2 contrats contradictoires de gestion des codes de sortie (v6.92/v6.98). Ces deux derniers ont été corrigés : 59 échecs restent.

Une ligne `FAIL: test_check` apparaît dans le journal de la suite à cause d'un test de qualification **intentionnellement défaillant** exécuté dans un sous-processus par `test_historical_runner_evidence_v6190.py`. Ce sous-processus est attendu et vérifié ; il **n'ajoute pas un échec** à la suite principale de 1 399 tests.

## Gates bloqués et limites

La suite historique s'arrête en FAIL, donc **PyInstaller et Inno Setup ne sont pas atteints**. Aucune installation/désinstallation ni exécution portable Windows n'est qualifiée. Aucun exécutable Windows ni capture réelle d'interface n'est fourni. Aucune fusion automatique dans `main`.

Les journaux complets persistés augmentent la taille de l'artefact de diagnostic par rapport aux 1 749 octets du run #39927960619, sans modifier les résultats unittest.

## Prochain correctif

Priorité : remplacer les assertions figées à d'anciennes versions par des invariants stricts de compatibilité et d'alignement (sans supprimer les contrôles), puis traiter les contrats de scripts sur leurs propriétés de sécurité réelles. Vérifier ensuite 1 399+ tests et les 8 imbriqués, obtenir une CI Windows verte, compiler PyInstaller/Inno, qualifier les binaires/installation/désinstallation/portable, puis produire les manifestes SHA-256.

**PR :** [draft #4](https://github.com/alimtalbi-ata/StorageScope-Architecte/pull/4). Ne pas fusionner avant la qualification native complète.
