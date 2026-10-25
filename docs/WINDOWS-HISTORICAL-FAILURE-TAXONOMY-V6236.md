# StorageScope — classification des échecs Windows historiques

**Auteur : Abdelhalim Talbi**  
**Run de référence :** https://github.com/alimtalbi-ata/StorageScope-Architecte/actions/runs/39668811238  
**Job analysé :** `119460870039`  
**Commit examiné :** `70220f62575e964b62a87db82e9f579a75f21569`  
**Date du run :** 21 octobre 2026

## Résultat observé

Le job natif Windows a exécuté 958 tests en 21,042 secondes et terminé avec **52 échecs et 173 erreurs**. Le build s'est arrêté dans `02-Compilation-Windows/build-all-windows.ps1`, à l'appel de `build-engine-windows.ps1`; les étapes PyInstaller, qualification native, installateur et portable n'ont donc pas été atteintes. L'artefact de diagnostic de ce run ne contenait qu'un rapport indiquant que les preuves natives manquaient; la taxonomie ci-dessous est extraite du journal du job.

Les 225 en-têtes `FAIL`/`ERROR` du journal ont été comptés puis reclassés à l'aide de la ligne d'exception terminale et du nom du test. Le classificateur n'utilise pas les extraits arbitraires de source inclus dans les messages d'assertion pour décider qu'une erreur est liée à la version.

| Cause racine probable | Échecs | Erreurs | Total |
|---|---:|---:|---:|
| Résolution des imports / PYTHONPATH | 0 | 50 | 50 |
| Arborescence des tests / répertoire courant | 1 | 99 | 100 |
| Cycle de vie SQLite / handles ouverts | 0 | 17 | 17 |
| Dépendance de test absente (Pillow) | 0 | 1 | 1 |
| Attentes de version historiques | 29 | 0 | 29 |
| Contrats statiques sur des fragments de source | 9 | 4 | 13 |
| Fixture PE / structure portable invalide | 0 | 2 | 2 |
| Contrat build / packaging / qualification à examiner | 13 | 0 | 13 |
| **Total** | **52** | **173** | **225** |

Les totaux sont cohérents avec le résumé unittest du run.

Aucune signature `UnicodeDecodeError` ou `UnicodeEncodeError` n'a été trouvée dans ce journal. Cela n'établit pas que le code est généralement exempt de problèmes d'encodage.

## Indices représentatifs

- **Imports (50)** : `ModuleNotFoundError` pour des modules comme `governance`, `decision_views_v543`, `storagescope_windows` et les modules de campagne. Le lanceur historique n'exposait pas systématiquement `03-Sources` via `PYTHONPATH`.
- **Arborescence (100)** : `FileNotFoundError` pour `desktop.py`, `decision_workspace_ui_v543.py`, `storagescope_windows.py`, `StorageScope.iss`, `VERSION` et d'autres fichiers cherchés depuis `04-Tests-et-Qualification`. Il faut résoudre les chemins depuis la racine du dépôt sans déplacer artificiellement les sources.
- **SQLite (17)** : `PermissionError [WinError 32]` à la suppression de bases temporaires, signalant des handles encore ouverts. Les contrôles de fermeture doivent rester actifs.
- **Dépendance (1)** : le test PNG termine par `RuntimeError: PNG export requires Pillow`. Déclarer la dépendance de test ou vérifier explicitement son contrat, sans ignorer le test.
- **Versions (29)** : de nombreuses assertions attendent un ancien numéro de cycle (p. ex. `6.87`) alors que le manifeste canonique de ce dépôt indique `6.108`. Les tests doivent valider la source canonique de version ou un contrat de compatibilité explicite; il ne faut pas modifier le produit seulement pour satisfaire un littéral historique.
- **Contrats statiques source (13)** : quatre erreurs `ValueError: substring not found` et neuf assertions sur des mots/fragments (rollback, promotion, portable, exit codes). Ce sont des signaux de dérive des tests textuels; avant de les modifier, vérifier les invariants par des tests de comportement.
- **Fixtures Windows (2)** : `Invalid PE section count` et `Entry module absent`. Réparer les fixtures positives tout en conservant les tests négatifs.
- **Build/packaging (13)** : échecs de schéma natif, de préflight, de présence des outils et d'empaquetage. Cette catégorie reste ouverte jusqu'à l'examen individuel de chaque test.

## 13 cas conservés en revue manuelle

1. `test_real_native_schema_passes`
2. `test_scripts`
3. `test_bootstrap_files_exist: Construire-StorageScope.cmd`
4. `test_bootstrap_files_exist: build-all-windows.ps1`
5. `test_bootstrap_files_exist: StorageScope.spec`
6. `test_bootstrap_files_exist: StorageScope.iss`
7. `test_bootstrap_files_exist: requirements-build.txt`
8. `test_bootstrap_files_exist: verify-windows-build.py`
9. `test_preflight`
10. `test_cumulative_packaging`
11. `test_script_present`
12. `test_installer_files`
13. `test_complete_success`

## Interprétation et suites

Il s'agit d'une classification heuristique de premier passage, et non d'une preuve que chaque anomalie a été corrigée. Les évolutions suivantes ont ajouté des contrôles du répertoire racine et des fermetures SQLite, et une version ultérieure a passé la qualification native Windows. Le run historique n'a cependant pas été re-joué avec une matrice qui relie chaque ancien test à son correctif; les 13 cas ci-dessus restent explicitement ouverts.

L'outil `tools/classify_windows_regression_log.py` régénère un rapport JSON/Markdown test par test à partir d'un journal UTF-8 téléchargé depuis Actions. Il compare les comptes extraits au résumé unittest, conserve les cas ambigus dans `OTHER_NEEDS_MANUAL_TRIAGE` et ne désactive aucun contrôle.

Commande de reproduction :

```powershell
python tools/classify_windows_regression_log.py windows-job.log --run-id 39668811238 --json-output taxonomy.json --markdown-output taxonomy.md
```

Le code de sortie est non nul si aucun échec n'est extrait ou si les décomptes ne concordent pas avec le résumé final d'unittest.

**Statut du cycle V6.236 :** outil + tests ciblés en qualification sur GitHub. Cette classification ne qualifie pas à elle seule les nouveaux binaires Windows V6.236.
