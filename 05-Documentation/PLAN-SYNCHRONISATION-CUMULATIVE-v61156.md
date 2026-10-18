# Synchronisation cumulative StorageScope
Auteur : Abdelhalim Talbi.

**État : non exécutée.** GitHub construit v6.108 ; l'archive cumulative v6.115.5 conserve des sources v6.113 avec correctifs SQLite. Ces versions ne sont pas interchangeables.

1. Créer une branche dédiée depuis l'intégration ; préserver main.
2. Vérifier SHA-256 du ZIP et prévisualiser `python tools/import_cumulative_release.py <archive>` ; exécuter `--apply` uniquement sur arbre propre.
3. Examiner diff, workflows, dépendances, documentation Word/PDF et absence éventuelle de captures réelles.
4. Aligner les trois fichiers VERSION et AppVersion Inno Setup seulement **après** intégration des sources.
5. Exécuter le garde-fou de version, tests Python, tests SQLite, puis compiler et qualifier les exécutables sur Windows.
6. Commiter, ouvrir PR, produire ZIP cumulatif depuis le commit qualifié, joindre manifestes et SHA-256.

**Blocages :** pas de publication si versions incohérentes, tests échoués, import non revu ou binaires Windows non qualifiés. Ne pas annoncer v6.115 comme compilée avant l'intégration réelle.
