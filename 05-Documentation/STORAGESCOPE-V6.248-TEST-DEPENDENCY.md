# StorageScope V6.248 — dépendances explicites de qualification

**Auteur : Abdelhalim Talbi**  
**Date : 26 octobre 2026**

## Défaut historique établi

Le run natif Windows de référence [#39668811238](https://github.com/alimtalbi-ata/StorageScope-Architecte/actions/runs/39668811238), commit `70220f62575e964b62a87db82e9f579a75f21569`, a exécuté 958 tests avec 52 échecs et 173 erreurs. Le journal de `test_graph_export.ExportTests.test_png` contient `ModuleNotFoundError: No module named 'PIL'`, suivi de `RuntimeError: PNG export requires Pillow`.

Il s'agit d'une cause racine concrète : la suite a été lancée dans un environnement qui ne possédait pas la dépendance nécessaire à une fonctionnalité testée. Ce cas ne doit ni être ignoré, ni être transformé en test optionnel, ni être confondu avec une erreur d'import de `03-Sources`.

## Correction

- Ajout de `04-Tests-et-Qualification/requirements-test.txt`, avec Pillow épinglé à `11.3.0`, identique à la version du build Windows.
- Les workflows Windows natif et gouvernance Linux/Windows installent ce manifeste, exécutent `pip check`, le test du contrat de dépendance, puis `test_graph_export.py`.
- `build-engine-windows.ps1` installe également ce manifeste dans le venv isolé de construction avant la suite historique complète. Les contrôles de sortie et d'absence de tests ignorés restent actifs.
- Le test cible ouvre le PNG généré avec Pillow et appelle `Image.verify()` : le contrôle exerce une vraie écriture/lecture, pas seulement la présence du module.

## Portée de preuve

La CI V6.248 doit confirmer cette correction sur son HEAD exact avant de la marquer comme livrée. Le correctif ne suffit pas à démontrer la résolution de toutes les 225 anomalies de la baseline. Les autres catégories (racines source/CWD, cycle de vie SQLite, contrat de version et contrats historiques) restent indépendantes. Aucun succès de gouvernance seul ne vaut qualification Windows native.

## Alignement d'architecture

La séparation entre dépendances de build et de test améliore la reproductibilité de livraison (gestion de changement/release ITIL 4 et traçabilité d'architecture ISO/IEC/IEEE 42010). Les manifestes sont des contrats explicites ; aucune certification ISO n'est revendiquée.
