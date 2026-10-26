# StorageScope V6.256 — parsing JSON strict pour les historiques de capacité

**Auteur : Abdelhalim Talbi**  
**Date : 26 octobre 2026**  
**Périmètre : entrée CLI du moteur de prévision SAN/NAS V6.254–V6.255**

## Problème et cause racine

Le chargeur CLI utilisait `json.loads` avec ses réglages par défaut. La bibliothèque Python accepte alors des membres JSON dupliqués en ne conservant que la dernière occurrence et reconnaît `NaN`, `Infinity` et `-Infinity`, qui ne sont pas des nombres JSON standard. Une entrée ambiguë pouvait ainsi être interprétée différemment d'un validateur strict ou masquer une valeur antérieure. Les extensions inconnues sont également analysées avant que le moteur métier ne les ignore.

## Correction

- Utiliser un `object_pairs_hook` récursif qui refuse un nom de membre dupliqué dans tout objet, y compris les extensions imbriquées.
- Refuser explicitement les constantes numériques non standard avec `parse_constant`.
- Lire le fichier en UTF-8 strict ; aucune conversion de caractères invalides n'est effectuée.
- Ne produire aucun rapport lorsque le document d'entrée ne peut pas être analysé.
- Préserver le schéma, les validations métier, l'ordre déterministe du rapport et le comportement en lecture seule pour les fichiers conformes.

La validation s'applique au chargeur CLI. Un appel Python direct à `forecast(dict)` reçoit déjà un objet décodé : il ne peut pas reconstituer les membres qui auraient été écrasés avant l'appel. Les intégrations qui décodent elles-mêmes le JSON doivent appliquer la même règle stricte.

## Tests de non-régression

Le module `test_storage_capacity_json_strict_v6256.py` couvre les JSON valides avec Unicode, les clés dupliquées à la racine et dans des objets imbriqués, les trois constantes numériques non standard, l'UTF-8 invalide et le refus CLI sans fichier de rapport. Il vérifie également que la suite ciblée est raccordée à la CI de gouvernance et à la qualification native Windows.

## Sécurité et qualité des données

Ce changement protège l'intégrité sémantique de l'entrée utilisée pour prévoir les seuils de capacité. Il ne prouve ni l'identité du collecteur, ni l'authenticité des mesures, ni la fraîcheur des observations. Aucun accès réseau, écriture CMDB ou remédiation automatique n'est ajouté. Les jeux de tests sont synthétiques et hors ligne.

## Référentiels

Le contrôle aide à conserver une chaîne de preuve d'architecture cohérente avec l'approche de traçabilité ISO/IEC/IEEE 42010 et les pratiques ITIL 4 de gestion de capacité et de risque. Il ne constitue pas une certification TOGAF, ArchiMate, ISO 27001 ou ISO 27040.

**Statut :** PR draft. La CI native Windows et ses artefacts exact-HEAD doivent réussir avant de déclarer la version qualifiée.
