# StorageScope V6.253 — validation stricte des seuils de capacité

**Auteur : Abdelhalim Talbi**  
**Date : 26 octobre 2026**  
**Branche :** `feature/storagescope-v6.253-capacity-threshold-type-safety-20261026`  
**Base :** V6.252 — protection des manifestes de sauvegarde JSON

## Problème métier

En Python, `bool` est une sous-classe de `int`. Le contrat précédent de `storage_path_risk_v6194.assess` vérifiait seulement l'ordre numérique des seuils. Un appel avec `warning_percent=True` pouvait donc être accepté comme un seuil de 1 %. La validation d'une politique de capacité doit distinguer explicitement un vrai pourcentage d'un booléen, d'une chaîne ou d'une valeur non finie.

## Correction

- Rejeter les seuils booléens, non numériques, NaN et infinis.
- Rejeter sans exception de débordement les entiers dont la conversion vers un flottant dépasse la plage.
- Conserver le contrat métier `0 < warning < critical <= 100`.
- Ne modifier ni les données de topologie ni les seuils reçus.
- N'ajouter aucune fusion CMDB, collecte fournisseur ou action de remédiation.

## Qualification

Le test `test_storage_threshold_type_contract_v6253.py` vérifie les booléens, chaînes, valeurs complexes, NaN, infinis, entiers hors plage et l'équivalence des seuils entiers/flottants valides. Il est raccordé à la gouvernance Linux/Windows et au workflow natif Windows.

Les scénarios sont synthétiques et hors ligne. La qualification de livraison doit être lue sur le HEAD exact du workflow Windows : build PyInstaller, installateur Inno Setup, installation/désinstallation, portable, manifestes et SHA-256. La réussite du seul workflow de gouvernance ne qualifie pas une livraison Windows.

## Gouvernance et limites

Cette correction renforce la qualité des métriques de capacité et l'analyse des risques de stockage. Elle contribue à la traçabilité d'architecture (ISO/IEC/IEEE 42010) et peut être pertinente pour un périmètre ISO 27040 ; TOGAF, ArchiMate et ITIL 4 servent de cadres d'alignement, sans certification revendiquée.

Aucun test sur baie physique, aucune modification de CMDB, aucune remédiation et aucune résolution individuelle des 225 symptômes historiques du run #39668811238 ne sont revendiqués.
