# StorageScope V6.217 — précision des seuils de capacité SAN/NAS

**Auteur : Abdelhalim Talbi** · 24 octobre 2026 · évolution cumulative V6.216 → V6.217.

## Défaut reproductible et impact

Le moteur `storage_path_risk_v6194.assess` arrondissait les pourcentages de capacité et de quota à deux décimales **avant** de choisir le niveau de risque. Une baie ou un NAS à `94.9999 %` était donc déclaré `CAPACITY_CRITICAL` (95 %) alors qu'il se situait sous le seuil critique. De même, `84.9999 %` déclenchait à tort `CAPACITY_WARNING` (85 %). Le même défaut touchait `SHARE_QUOTA_WARNING` et `SHARE_QUOTA_CRITICAL`.

Cette erreur produit des escalades injustifiées, peut fausser les tableaux de bord et les priorités de remédiation, et compromet l'explicabilité des décisions de capacité.

## Correction fonctionnelle

Les comparaisons `warning_percent` / `critical_percent` portent désormais sur le ratio **non arrondi** `used / total * 100` ou `used / quota * 100`. Les seuils restent inclusifs : exactement 85 % déclenche `WARNING`, exactement 95 % déclenche `CRITICAL`. Le champ de preuve conserve la valeur numérique calculée sans arrondi artificiel à deux décimales. Les valeurs invalides (booléen, NaN, négatif, dépassement, dénominateur nul) restent rejetées par les contrôles existants.

| Valeur observée | Ancien comportement | Nouveau comportement |
| --- | --- | --- |
| 84.9999 % | WARNING erroné | Aucun seuil franchi |
| 85 % | WARNING | WARNING |
| 94.9999 % | CRITICAL erroné | WARNING |
| 95 % | CRITICAL | CRITICAL |

Le même tableau s'applique à la capacité globale NAS/baie et au quota des partages NFS/SMB. Il ne modifie ni les observations SAN, ni la politique de fraîcheur V6.216, ni la CMDB. Aucun changement automatique ni accès à un système réel.

## Qualification et gouvernance

Le nouveau module `test_storage_capacity_threshold_precision_v6217.py` comporte sept tests synthétiques : quatre régressions de franchissement artificiel, deux tests des frontières inclusives et un test de déterminisme/non-mutation. Avant correction : **4 échecs sur 7** reproduits localement. Après correction : **7/7 PASS** localement, plus les 24 tests historiques du moteur de risques **PASS**. Au total, 99 tests locaux ciblés et de régression ont été exécutés avec succès. Ces résultats locaux ne remplacent pas la qualification Windows native.

Les workflows gouvernance Linux/Windows exécutent explicitement les sept tests. La CI Windows native inclut un scénario de l'exécutable PyInstaller avec valeurs de part et d'autre des deux seuils, en plus de la suite historique, de l'installateur et du portable. Ne déclarer la version Windows qualifiée qu'après réussite effective de ces contrôles et vérification des artefacts SHA-256.

**Traçabilité architecture :** ISO/IEC/IEEE 42010 (hypothèses et preuves de calcul), ITIL 4 (priorisation d'incidents et capacité), ISO 27001/27040 (qualité des décisions de risque et de stockage). TOGAF/ArchiMate : impact de capacité sur les dépendances techniques, sans déduction automatique de criticité applicative.

**Limites :** précision binaire des nombres flottants, métriques sources non authentifiées, absence de tests sur baies physiques, pas de captures UI réelles ni de qualification UX humaine. Version interne du logiciel : 6.108 jusqu'à décision de versionnement produit distincte.
