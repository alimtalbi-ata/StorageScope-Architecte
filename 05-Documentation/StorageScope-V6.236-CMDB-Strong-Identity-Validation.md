# StorageScope V6.236 — Validation des identités fortes CMDB

**Auteur :** Abdelhalim Talbi  
**Statut :** cycle de développement, pas une version produit publiée  
**Version produit :** reste 6.108 tant qu'une release dédiée ne l'a pas modifiée.

## Risque traité

La réconciliation V6.235 durcissait la provenance des collecteurs, mais une valeur d'identité forte (serial, WWN ou UUID) pouvait encore contenir des caractères de contrôle ou dépasser une longueur raisonnable. De plus, un placeholder Unicode pleine largeur tel que `Ｎ／Ａ` n'était pas reconnu comme équivalent de `N/A`.

## Comportement V6.236

- Normaliser les glyphes de compatibilité Unicode en NFKC avant la comparaison des identités.
- Reconnaître les placeholders après normalisation, sans les utiliser comme clés de rapprochement.
- Rejeter un enregistrement entier si un identifiant fort fourni est non textuel, contient des caractères Unicode de catégorie contrôle/format/surrogate, des séparateurs de ligne/paragraphe, ou dépasse 512 caractères.
- Distinguer `invalid_identity_type:<field>` de `invalid_identity_value:<field>` dans les rapports.
- Ne pas ignorer silencieusement un identifiant fort mal formé lorsqu'un autre champ pourrait créer un faux rapprochement.
- Conserver la propagation de quarantaine vers les observations valides liées par les autres identifiants forts.
- Maintenir les garanties : lecture seule, aucune fusion automatique, aucune écriture CMDB.

## Tests de régression

Les tests synthétiques ajoutés couvrent le placeholder pleine largeur, un caractère de contrôle intégré à un identifiant, une identité surdimensionnée, la quarantaine des observations liées et l'absence de fusion automatique.

La qualification CI sur la tête exacte de branche est requise avant de considérer ce changement qualifié. Ces tests n'attestent pas une validation sur une baie physique ou une CMDB de production.
