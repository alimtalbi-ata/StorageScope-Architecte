# StorageScope V6.247 — intégrité fail-closed des preuves de sélecteurs historiques

**Auteur : Abdelhalim Talbi**  
**Branche :** `feature/storagescope-v6.247-selector-evidence-integrity-20261026`  
**Base :** V6.246 — traçabilité des 13 contrats de faible confiance

## Problème traité

Le rapport V6.246 associe 13 enregistrements historiques à huit méthodes unittest exécutées séparément. Deux ambiguïtés demeuraient dans le contrat de validation du rapport :

- `unittest` renvoie un statut global OK quand un test est ignoré, ce qui ne prouve pas qu'une assertion a été exercée ;
- un dictionnaire de résultats indexé directement par sélecteur peut laisser une ligne dupliquée remplacer une ligne précédente, et la présence d'un résultat « PASS » ne prouvait pas que le journal brut correspondant existait encore ni que ses octets correspondaient aux hashes déclarés.

## Correction

`build_low_confidence_closure` impose désormais :

1. exactement un sélecteur pleinement qualifié par sous-processus, parmi les huit sélecteurs attendus ;
2. exactement une ligne d'évidence par sélecteur, sans dédoublonnage « dernier résultat gagnant » ;
3. une synthèse terminale complète, un seul test exécuté, code retour entier zéro, et zéro échec, erreur, skip, expected failure ou unexpected success ;
4. une preuve du décodeur UTF-8 strict sans substitution ;
5. un nom de fichier de log sûr, présent dans le répertoire de preuves, non symbolique et non extérieur à celui-ci ;
6. le recalcul SHA-256 et du nombre d'octets du fichier brut, comparés aux métadonnées du sous-processus et du décodeur.

Le mode ciblé exige désormais `--report`, afin que les journaux bruts soient persistés et disponibles pour la vérification. Toute omission, duplication, incohérence, absence de log ou altération de contenu déclenche le refus de qualification. Aucun contrôle de test n'est désactivé.

## Tests ajoutés

`04-Tests-et-Qualification/test_historical_selector_evidence_integrity_v6247.py` vérifie le cas nominal et les contre-exemples suivants : sélecteur ignoré, doublon contradictoire, un seul processus prétendant couvrir plusieurs sélecteurs, synthèse absente, booléen à la place d'un compteur entier, journal modifié, journal manquant, absence du répertoire de preuves et chemin de log non sûr.

Les entrées synthétiques de ce fichier servent uniquement à tester le validateur ; elles ne constituent pas les preuves des sélecteurs de qualification. Les preuves de qualification sont les sorties brutes réellement capturées par `run_historical_windows_suite.py` dans le pipeline.

Le test V6.246 a été adapté afin que ses tests de logique utilisent également des fichiers de preuve temporaires et des métadonnées cohérentes.

## Portée et limites

Ce contrôle renforce l'intégrité et la reproductibilité du rapport. Il ne change pas la baseline historique `#39668811238` : 958 tests, 52 failures et 173 errors. Il ne démontre pas que chaque cause racine des 225 anomalies a été établie ou corrigée. La taxonomie originale demeure heuristique et `historical_root_cause_linkage = NOT_ESTABLISHED`.

La suite ciblée ne qualifie pas à elle seule PyInstaller, Inno Setup, l'installation/désinstallation ou le portable. La qualification native Windows exacte-HEAD reste un gate distinct. Aucune baie SAN/NAS physique, capture UI réelle, validation UX humaine ni certification ISO ne sont revendiquées.

## Alignement d'architecture

Cette évolution soutient la traçabilité des changements et des preuves de qualification (ITIL 4, ISO/IEC/IEEE 42010 et contrôles pertinents ISO/IEC 27001/27040). Les vues TOGAF/ArchiMate peuvent référencer le contrôle dans les vues de gouvernance et de livraison. Cela n'est pas une déclaration de conformité certifiée.
