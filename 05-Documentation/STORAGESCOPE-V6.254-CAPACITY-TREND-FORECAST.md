# StorageScope V6.254 — prévision de capacité SAN/NAS

**Auteur : Abdelhalim Talbi**  
**Date : 26 octobre 2026**  
**Type : outil CLI en lecture seule, export JSON hors ligne**

## Objectif métier

V6.254 estime le temps avant franchissement des seuils d'avertissement et de criticité. Le rapport de risque existant signale l'utilisation courante ; ce nouvel outil analyse également une série temporelle. Il ne remplace pas les alertes courantes et n'effectue aucune action automatique.

## Format d'entrée

Le document UTF-8 utilise le schéma \`storagescope.capacity-history.v1\` avec deux tableaux :

- \`assets\` : inventaire courant contenant \`id\`, \`kind\` (\`storage_array\` ou \`nas\`) et \`total_gib\` ;
- \`samples\` : \`asset_id\`, \`observation_id\` unique dans le lot, \`source_ref\`, \`observed_at\` ISO 8601 avec fuseau, \`used_gib\` et \`total_gib\`.

Les références source et observation sont des libellés fournis par l'appelant : elles ne constituent pas une attestation cryptographique.

## Garde-fous et algorithme

- Les observations associées à un actif inconnu, ambigu ou non-stockage sont rejetées.
- Les nombres doivent être finis, non booléens et non négatifs ; la capacité totale doit être strictement positive et l'usage ne peut pas la dépasser.
- Les dates doivent avoir un décalage explicite. Les timestamps équivalents en UTC sont considérés comme doublons.
- Une seule ligne invalide ou un identifiant d'observation dupliqué met en quarantaine la série entière.
- Il faut au moins trois observations distinctes sur deux jours minimum.
- Toute variation de \`total_gib\` ou divergence avec la capacité courante suspend la prévision jusqu'à séparation des périodes avant/après extension.
- La pente est obtenue par régression linéaire des pourcentages d'utilisation. L'horizon est borné à 3 650 jours, avec 90 jours par défaut.
- Les seuils respectent \`0 < warning < critical <= 100\`. \`bool\`, chaînes, NaN, infinis et valeurs hors plage sont refusés.
- Aucune connexion réseau, écriture CMDB, réparation des données ni remédiation n'est effectuée. Le rapport porte \`automatic_changes: 0\`.

## Exemple d'utilisation

Commande depuis la racine du dépôt :

\`python 03-Sources/storage_capacity_forecast_v6254.py .\\capacity-history.json --warning-percent 85 --critical-percent 95 --horizon-days 90 --output .\\capacity-forecast.json\`

Code de sortie : \`0\` sans seuil prévu dans l'horizon, \`1\` si au moins un seuil est prévu, \`2\` en absence de données ou si l'historique est incomplet. Le rapport doit être consulté : un code 0 ne signifie pas qu'une baie est saine.

## Qualification et limites

\`test_storage_capacity_forecast_v6254.py\` couvre le scénario nominal, la stabilité d'ordre, les tendances nulles/décroissantes, les historiques insuffisants, les timestamps redondants, les changements de capacité, les collisions d'identifiants, les actifs orphelins, les valeurs invalides, la non-mutation et le CLI JSON.

Cette fonction contribue à la traçabilité des décisions de capacité (ISO/IEC/IEEE 42010), à l'analyse des risques de stockage (ISO/IEC 27040 selon le périmètre) et aux pratiques de capacité ITIL 4. TOGAF et ArchiMate peuvent représenter les actifs et services associés. Aucune certification ni validation sur baie physique n'est revendiquée.

**Limite explicite :** la régression linéaire est une aide de planification, pas une garantie. Les timestamps sont contrôlés syntaxiquement, mais leur fraîcheur n'est pas indépendamment attestée. Le CLI n'est pas encore exposé comme écran de l'interface graphique.
