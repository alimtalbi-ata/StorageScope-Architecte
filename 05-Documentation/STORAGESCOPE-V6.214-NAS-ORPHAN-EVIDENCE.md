# StorageScope V6.214 — NAS orphan share evidence

**Auteur : Abdelhalim Talbi — 24 octobre 2026.** Statut : changement proposé, validation Windows sur commit exact requise. Les fixtures sont **synthétiques**.

## Cause racine et impact métier

Le moteur `storage_dependency_impact_v6199.py` ignorait silencieusement les observations de partages NAS sans identité fiable : partage sans ID, NAS inconnu, protocole non pris en charge, identifiant de partage dupliqué ou enregistrement non objet. Un autre partage sain pouvait conserver un NAS en statut `OBSERVED` sans que la cartographie signale ces observations rejetées. Le moteur de risques signalait certaines erreurs, mais le rapport de dépendances ne conservait ni compteur global ni attribution par NAS.

## Correctif et contrat

- `unresolved_share_observations` au niveau du rapport : nombre d'observations de partages non résolues, y compris enregistrements non objets.
- `assets[].unresolved_share_observations` : nombre attribuable uniquement à une identité NAS unique et fiable.
- Un partage NFS/SMB avec ID unique et NAS de confiance reste dans `verified_share_ids`. Les autres ne deviennent **jamais** des relations vérifiées.
- L'évaluation globale passe à `INCOMPLETE` dès qu'une observation de partage reste non résolue ; un NAS sain indépendant reste isolé de l'incident.
- Les compteurs sont indépendants de l'ordre des observations. Les entrées ne sont pas modifiées. Aucune écriture CMDB ni remédiation automatique.
- Le Diagnostic Windows affiche `Observations de partages sans relation résolue` et `partages_orphelins` par équipement.

**Limite :** une relation de partage vérifiée ne garantit pas la validité des métriques de quota, ni la disponibilité applicative. Les métriques de quota sont évaluées séparément. Une observation sans NAS de confiance reste comptabilisée uniquement au niveau global ; aucune relation n'est inventée.

## Qualification reproductible

Depuis la racine du dépôt :

```shell
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_dependency_orphan_shares_v6214.py' -v
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_storage_dependency*.py' -v
```

Les cinq tests V6.214 reproduisaient **5 erreurs** avant correction, puis ont passé sous Linux après correction. Le workflow gouvernance exécute les tests sous Linux et Windows ; le workflow Windows natif vérifie également les compteurs sur l'exécutable PyInstaller construit et conserve les gates installateur, désinstallation, portable et SHA-256. **Ne pas déclarer Windows qualifié avant la réussite du workflow sur le HEAD exact et la vérification des artefacts.**

## Architecture et gouvernance

- **ISO/IEC/IEEE 42010** : limites explicites de la vue de dépendances.
- **TOGAF / ArchiMate** : séparation des relations observées et non établies ; pas de dépendance applicative inférée.
- **ITIL 4** : inventaire incertain signalé avant réconciliation CMDB.
- **ISO 27001 / 27040** : intégrité des observations, lecture seule, aucune action destructive.

## Captures et preuves

Aucune capture réelle de l'interface Windows n'est fournie pour ce changement. Les tests locaux sont exécutés sous Linux ; les résultats GitHub Actions et binaires Windows sont à joindre seulement après vérification réelle. Aucun exemple synthétique n'est présenté comme une capture d'exécution réelle.
