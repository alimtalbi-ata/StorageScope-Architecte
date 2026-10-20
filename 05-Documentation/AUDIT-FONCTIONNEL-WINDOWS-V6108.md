# StorageScope Windows — audit fonctionnel et qualification (révision v6.108)

**Auteur : Abdelhalim Talbi**  
**Périmètre :** branche de développement `feature/storagescope-v6.114-diagnostic-pagination`.  
**Nature :** audit statique du code et tests automatisés ; aucune recette manuelle sur poste Windows revendiquée.

## 1. Mission du produit et cas d'usage

StorageScope doit servir les équipes infrastructure, stockage/SAN, architecture et exploitation. Le produit vise la constitution et la réconciliation d'inventaires, la gouvernance des décisions d'architecture, l'analyse des campagnes et la production de preuves exploitables. Les fonctions de maintenance et de diagnostic sont transversales, non le cœur métier.

| Parcours | Résultat attendu | Composants existants | Preuve requise avant statut « qualifié fonctionnellement » |
|---|---|---|---|
| Importer et réconcilier des inventaires | Identifier ajouts, écarts et conflits sans altérer la source | `inventory_reconcile_v619.py`, `inventory_quality_v618.py`, `governance_desktop.py` | Fixtures multi-vendeurs, vérification des écarts, revue humaine et exports |
| Gouverner les décisions | Créer, filtrer, revoir, tracer et retrouver une décision | `decision_governance_v537.py`, `decision_workspace_ui_v543.py` | Tests SQLite et UI de création/édition/consultation, redémarrage |
| Piloter les campagnes | Historique, comparaison et KPI lisibles | `campaign_history_v526.py`, `campaign_dashboard_v527.py` | Données réalistes, filtres, exactitude des KPI et performances |
| Diagnostiquer un poste | État SQLite, recommandations, export support sûr | `windows_support_diagnostic_v619.py`, `storagescope_windows.py` | Régression dédiée + vérification visuelle Windows |
| Sauvegarder les données | Snapshot cohérent, vérifiable, sans écrasement | `backup_snapshot`, `verify_backup_snapshot` | Tests corruption/WAL/concurrence et reprise après interruption |
| Installer et lancer Windows | Installer + portable autonomes | Workflows GitHub Actions Windows | Installation, lancement, désinstallation et upgrade sur VM propre |

## 2. Écarts identifiés

1. **Couverture CI incomplète :** la régression du diagnostic support existait mais n'était pas appelée dans le workflow principal. Correction : ajout explicite du test et compilation syntaxique du shell.
2. **Fonction orpheline :** le filtrage `ERROR/NOTICE/INFO` était implémenté dans le moteur mais inaccessible depuis l'UI. Correction : liste déroulante et actualisation immédiate.
3. **Documentation obsolète :** `03-Sources/README.md` indiquait encore v5.74. Le présent document décrit la révision courante et les limites de qualification.
4. **Priorités fonctionnelles :** l'effort ne doit pas être absorbé par le packaging. Les prochaines itérations cibleront les parcours inventaire → réconciliation → décision → preuve, puis campagnes et exports.

## 3. Diagnostic support — contrat

- Lecture seule des bases SQLite via `mode=ro` et `PRAGMA quick_check`.
- Les fichiers manquants sont `NOTICE` (initialisation facultative) et non systématiquement une panne.
- Les anomalies d'intégrité ou de lecture sont `ERROR`, les contrôles valides `INFO`.
- Les recommandations n'exécutent **aucune remédiation automatique**.
- Le filtre d'affichage ne modifie ni la collecte ni l'export : le JSON contient toujours le rapport complet.
- Le rapport exclut les lignes SQL, identifiants, chemins absolus et variables d'environnement.
- L'export utilise une création exclusive ; aucune réécriture d'un rapport existant.
- Les erreurs d'export et d'accès au presse-papiers sont présentées à l'utilisateur.

## 4. Vérification et limites

Les tests automatisés doivent vérifier : base valide, base corrompue, lien symbolique, fichier absent, confidentialité, export exclusif, classifications et filtrage. Une compilation Python réussie ne valide **pas** les interactions graphiques. Les captures d'écran réelles nécessitent une session Windows interactive et ne doivent pas être remplacées par des maquettes présentées comme preuves.

Le build Windows en CI valide la production des artefacts, mais **ne prouve pas à lui seul** l'installation, l'utilisation des parcours métier ni la compatibilité avec tous les environnements de production.

## 5. Plan de développement réaligné

**P0 — Qualité du cœur métier :** établir une matrice d'exigences et des tests end-to-end sur la réconciliation d'inventaires et la gouvernance des décisions ; traiter la cohérence transactionnelle, les erreurs, la traçabilité et la persistance.  
**P1 — Ergonomie :** parcours guidés, états vides explicites, retours d'erreur actionnables, navigation clavier et tests d'interface.  
**P1 — Windows :** qualification installateur/portable sur VM propre, migration et désinstallation ; empreintes SHA-256 et provenance des binaires.  
**P2 — Architecture :** extraire progressivement la logique métier du shell Tkinter et introduire des contrats de service testables. Évaluer Qt/PySide6 uniquement si les tests UX démontrent que Tkinter bloque des besoins concrets ; éviter une réécriture sans bénéfice démontré.  
**P2 — Documentation :** guides Word/PDF versionnés, diagrammes, exemples CLI/API exécutés, captures réelles avec manifeste d'absence le cas échéant.

## 6. Commandes de validation locale

```powershell
py -m py_compile 03-Sources/storagescope_windows.py 03-Sources/windows_support_diagnostic_v619.py
py -m unittest discover -s 04-Tests-et-Qualification -p "test_windows_support_diagnostic_v619.py" -v
py 03-Sources/release_version_guard.py
```

Résultat attendu : aucune erreur de compilation ; tous les tests découverts réussis ; cohérence des versions. **Ce sont des attentes, pas des sorties de commande prétendument observées.**

## 7. Règle de publication

Publier une archive cumulative uniquement après workflows verts. Signaler séparément les tests réellement exécutés, les contrôles statiques, les essais Windows automatisés et les essais humains non réalisés. Ne pas fusionner automatiquement dans `main`.
