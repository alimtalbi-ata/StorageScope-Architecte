# StorageScope V6.257 — intégrité des rapports de qualification

**Auteur : Abdelhalim Talbi**  
**Date : 27 octobre 2026**  
**Branche :** `feature/storagescope-v6.257-strict-qualification-json-20261027`  
**Base :** V6.256 — rejet du JSON ambigu dans l'historique de capacité

## Constat

L'inspection du consolidateur natif `02-Compilation-Windows/consolidate-qualification.py` a révélé que les rapports native, installateur et portable étaient chargés via le parseur JSON permissif standard. Un objet JSON peut contenir des noms de propriété dupliqués ; le parseur standard de Python conserve alors une valeur et masque l'autre. Des tokens non standards comme `NaN` et `Infinity` étaient également acceptés, même dans un champ d'extension ignoré par le consolidateur.

Ces propriétés sont inacceptables à la frontière qui décide si des binaires Windows peuvent être qualifiés.

## Correction V6.257

Le consolidateur charge désormais chaque rapport avec un seul lecteur strict partagé :

- encodage UTF-8 strict, avec BOM UTF-8 optionnel accepté pour compatibilité avec les rapports PowerShell ;
- rejet des clés JSON dupliquées à tous les niveaux, y compris dans les objets imbriqués ;
- rejet des constantes numériques non conformes `NaN`, `Infinity` et `-Infinity` ;
- maintien du refus fermé : un rapport mal formé produit un statut `FAIL`, et ne peut pas contribuer à un résultat global `PASS`.

Les exigences de qualification existantes restent inchangées : version cohérente, liste de contrôles native complète et unique, preuve d'installation/désinstallation, preuve de portable. Aucun contrôle n'a été retiré et aucune version produit n'a été modifiée.

## Tests ciblés

Fichier : `04-Tests-et-Qualification/test_qualification_evidence_json_strict_v6257.py`

Les tests couvrent un ensemble de rapports valides, les doublons de statut au niveau racine et au niveau imbriqué, les doublons dans le rapport installateur, `NaN`, `Infinity`, l'UTF-8 invalide et la présence de la suite dans les workflows de gouvernance et de qualification native.

Commande :

```powershell
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_qualification_evidence_json_strict_v6257.py' -v
```

## Qualification et limites

La PR doit passer les workflows de gouvernance et le workflow natif Windows sur son HEAD exact. La réussite de la seule CI de gouvernance ne qualifie pas le binaire, l'installateur ou le portable.

Cette correction réduit un risque d'intégrité de l'évidence ; elle ne clôt pas automatiquement les 225 symptômes du run historique `39668811238` (958 tests, 52 failures, 173 errors). Leur correspondance individuelle avec une cause démontrée, un commit correctif et un test de non-régression reste un chantier séparé.

L'approche améliore la traçabilité et l'intégrité des preuves dans l'esprit de la gouvernance de sécurité (ISO 27001/27040 selon l'applicabilité du contexte). Elle ne constitue pas une certification ni une attestation de conformité.
