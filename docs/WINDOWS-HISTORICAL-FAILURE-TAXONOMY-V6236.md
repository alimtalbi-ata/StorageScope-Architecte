# StorageScope — classification des échecs Windows historiques

**Auteur : Abdelhalim Talbi**  
**Run de référence :** https://github.com/alimtalbi-ata/StorageScope-Architecte/actions/runs/39668811238  
**Commit examiné :** 70220f62575e964b62a87db82e9f579a75f21569  
**Date du run :** 21 octobre 2026

## Résultat observé

Le job natif Windows a exécuté 958 tests et terminé avec 52 échecs et 173 erreurs. Le build s'est arrêté dans 02-Compilation-Windows/build-all-windows.ps1, à l'appel de build-engine-windows.ps1 ; les étapes PyInstaller, qualification native, installateur et portable ont donc été ignorées. Le seul artefact de diagnostic de ce run contient un rapport de qualification indiquant que les preuves natives manquent.

Un passage systématique sur les 225 enregistrements FAIL/ERROR du journal du job a produit la ventilation heuristique suivante :

| Cause racine probable | Échecs | Erreurs | Total |
|---|---:|---:|---:|
| Import-root / PYTHONPATH | 0 | 51 | 51 |
| Arborescence de tests / répertoire courant | 1 | 99 | 100 |
| Cycle de vie SQLite / handles encore ouverts | 0 | 17 | 17 |
| Attentes de version périmées | 37 | 0 | 37 |
| Assertions statiques sur des fragments de source périmés | 0 | 4 | 4 |
| Fixture PE ou structure de l'archive portable invalide | 0 | 2 | 2 |
| Contrat de build / packaging / qualification à examiner | 14 | 0 | 14 |
| **Total** | **52** | **173** | **225** |

Aucune signature UnicodeDecodeError ou UnicodeEncodeError n'a été trouvée dans ce journal. Cela ne prouve pas que le code est exempt de problèmes d'encodage en général.

## Indices représentatifs

- ModuleNotFoundError pour governance, decision_views_v543 et d'autres modules : le lanceur historique n'avait pas PYTHONPATH=03-Sources pour de nombreuses importations.
- FileNotFoundError pour desktop.py, storagescope_windows.py, decision_workspace_ui_v543.py, StorageScope.iss, VERSION ou des scripts depuis 04-Tests-et-Qualification : plusieurs tests résolvaient des fichiers depuis le mauvais répertoire ou attendaient des fichiers au mauvais emplacement.
- PermissionError [WinError 32] lors de la suppression de fichiers SQLite temporaires : handles non fermés, particulièrement visibles sous Windows.
- Assertions 6.108 contre des attentes historiques telles que 6.87 ou 6.88 : attentes statiques incompatibles avec la version canonique.
- ValueError: substring not found : tests de contrat recherchant des fragments d'implémentation disparus ou déplacés.
- Invalid PE section count et Entry module absent : fixtures synthétiques rejetées par les vérificateurs.

## Interprétation et limites

Il s'agit d'une classification heuristique de premier passage destinée à prioriser les correctifs, et non d'une preuve que chaque anomalie a été corrigée. Les 14 écarts de contrat build/packaging doivent être examinés test par test. Les changements ultérieurs ont renforcé le lancement depuis la racine, la fermeture de fixtures SQLite et la qualification native ; toutefois, le run de référence ne contient pas de cartographie officielle de chaque symptôme vers un correctif ultérieur.

L'outil tools/classify_windows_regression_log.py permet de régénérer une classification par test à partir d'un journal UTF-8 téléchargé depuis Actions. Il conserve les cas ambigus dans OTHER_NEEDS_MANUAL_TRIAGE, compare les comptes extraits au résumé unittest et ne désactive aucun contrôle.

Commande de reproduction :

python tools/classify_windows_regression_log.py windows-job.log --run-id 39668811238 --json-output taxonomy.json --markdown-output taxonomy.md

Le code de sortie est non nul si aucun enregistrement n'est extrait ou si les décomptes ne correspondent pas au résumé final de unittest.
