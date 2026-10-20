# Intégration StorageScope v6.109 → v6.113

Base GitHub vérifiée : **v6.108**, commit `eaa954c`.
Dernière archive cumulative préparée hors dépôt : **v6.113**.
**Statut : intégration des sources non encore effectuée.**

## Procédure sûre

1. Récupérer l'archive `StorageScope-v6.113-Cumulative.zip` depuis la conversation de développement.
2. Sur une copie locale de cette branche, exécuter `python tools/import_cumulative_release.py /chemin/StorageScope-v6.113-Cumulative.zip` (prévisualisation).
3. Exécuter la même commande avec `--apply` et inspecter `git diff --stat`.
4. Vérifier les modifications de GitHub depuis v6.108, résoudre les divergences, exécuter les tests et mettre à jour les manifestes.
5. Compiler et qualifier les binaires sur Windows ; ne pas annoncer de binaires précompilés avant vérification.
6. Ajouter les modifications validées à cette PR et demander une revue avant fusion dans `main`.

Ne pas remplacer directement `main` par l'archive cumulative ; elle peut contenir des fichiers historiques et ne prend pas en compte les changements distants.

Auteur : Abdelhalim Talbi.
