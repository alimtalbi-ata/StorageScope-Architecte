# StorageScope V6.212 — SAN fabric absent : préservation de l'incertitude

**Auteur : Abdelhalim Talbi** — 24 octobre 2026 — PR draft, sans fusion de `main`.

## Cause racine

Dans `storage_dependency_impact_v6199.py`, un chemin SAN ayant un hôte et une baie valides mais un identifiant de fabric absent ou invalide était ignoré avant la construction des relations. Si un autre chemin du même couple était actif, la vue de dépendances annonçait une relation vérifiée sans conserver l'observation incomplète. Le rapport de risques contenait `INVALID_PATH`, mais la projection des dépendances perdait cette preuve.

## Correctif

Lorsque les deux extrémités sont identifiables et de catégories compatibles, une observation sans fabric est classée dans les relations **non vérifiées** du couple hôte/baie. Un autre chemin actif reste visible comme preuve vérifiée ; les deux catégories peuvent coexister. `mixed_evidence_host_relationships` signale cette situation et `assessment=INCOMPLETE`. Les chemins dont les extrémités sont inconnues restent des anomalies globales sans attribution arbitraire. Aucun changement de CMDB, de configuration SAN, ni remédiation automatique.

## Scénarios synthétiques

| Scénario | Vérifiées | Non vérifiées | Mixtes | Évaluation |
| --- | ---: | ---: | ---: | --- |
| Fabric B actif + chemin sans fabric | 1 | 1 | 1 | INCOMPLETE |
| Chemin sans fabric uniquement | 0 | 1 | 0 | INCOMPLETE |
| Fabric vide, blanc, numérique ou null + B actif | 1 | 1 | 1 | INCOMPLETE |
| Autre couple hôte/baie sain | 1 (indépendant) | 0 (indépendant) | 0 (indépendant) | isolé |

Cinq tests couvrent aussi l'ordre des observations, l'absence de mutation et l'affichage Diagnostic. Les workflows Linux/Windows exécutent ces tests. Le workflow natif Windows teste le binaire PyInstaller et bloque la publication si les compteurs attendus sont absents.

## Qualification et limites

Avant correction locale Linux : cinq méthodes exécutées, sept assertions défaillantes (quatre sous-cas). Après correction : **5/5 tests nouveaux, 23/23 tests de dépendances et 157/157 tests ciblés Linux réussis**. Les workflows natifs Windows, l'installateur Inno Setup, le portable, les empreintes SHA-256 et les captures réelles doivent être confirmés par leurs journaux et artefacts. Ne pas déclarer ces éléments qualifiés avant confirmation.

## Alignement

ISO/IEC/IEEE 42010 : limites de preuve explicites ; ArchiMate : distinguer lien technique et dépendance de service ; TOGAF : séparer constat, décision et remédiation ; ITIL 4 : conserver les anomalies d'observabilité ; ISO 27001/27040 : intégrité des preuves, lecture seule.

## Suite

Vérifier la CI native Windows et les artefacts exact-head, puis enrichir les dépendances applicatives et la provenance temporelle des observations SAN.
