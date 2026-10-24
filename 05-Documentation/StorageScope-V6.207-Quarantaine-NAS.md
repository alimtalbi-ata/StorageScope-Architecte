# StorageScope V6.207 — Quarantaine des observations NAS malformées

**Auteur : Abdelhalim Talbi** · **Date : 24 octobre 2026** · **Statut : correction proposée, non fusionnée**

## Anomalie et impact

Le normaliseur hors ligne `03-Sources/vendor_snapshot_import_v6201.py` rejetait un élément de partage NAS qui n'était pas un objet JSON (par exemple `null`, nombre, texte ou tableau), mais conservait les autres partages du même équipement dans `topology.shares`. Le rapport global était `INCOMPLETE`, pourtant des relations NAS→partage pouvaient être interprétées à tort comme vérifiées.

**Cause racine :** la branche `not isinstance(entry, dict)` ajoutait une raison de rejet sans inscrire l'identifiant du NAS dans `quarantined_share_assets`.

## Correction et périmètre

Pour tout élément non objet, ajouter le NAS à `quarantined_share_assets`. Le filtrage final retire **tous** les partages de ce NAS, indépendamment de l'ordre des observations. Les partages d'un autre NAS valide restent disponibles. La ligne d'inventaire du NAS demeure visible, avec la quarantaine explicitée par `quarantined_share_asset_ids` et `rejected`.

Le contrat reste `storagescope.vendor-import-report.v1`. L'import reste **strictement hors ligne, en lecture seule** : aucune écriture CMDB, aucun fallback constructeur, aucune remédiation automatique. Le SHA-256 porte sur les octets exacts du snapshot; il ne prouve pas la véracité des déclarations du fournisseur.

## Qualification et critères de sortie

- Test `test_vendor_malformed_share_v6207.py` : 3 constructeurs (NetApp ONTAP, Dell PowerScale, Pure FlashBlade), 5 formes malformées, 2 ordres, NAS indépendant et cas positif.
- Régressions existantes V6.201–V6.206 : import, identités, quotas, provenance et non-écrasement.
- Workflow `vendor-snapshot-qualification.yml` : tests sur Linux et Windows.
- Workflow `windows-build.yml` : compilation PyInstaller/Inno Setup et scénario **exécutable figé** vérifiant quarantaine, préservation du NAS sain, absence de modification et empreinte source.
- Qualification native à établir uniquement sur un run complet **SUCCESS** au SHA exact : suite historique, installation/désinstallation, portable et SHA-256 binaires. Une CI gouvernance seule ne suffit pas.
- Captures d'interface réelles : **non réalisées**. Validation UX humaine : **non réalisée**.

## Architecture et gouvernance

Le flux reste : **snapshot fournisseur → validation stricte → normalisation → quarantaine → rapport de preuve → revue humaine → éventuelle réconciliation CMDB**. Ce comportement contribue à la traçabilité des décisions (ISO/IEC/IEEE 42010), à la gestion des configurations (ITIL 4) et à la protection de l'intégrité des inventaires (ISO 27001 / ISO 27040). Ces correspondances ne constituent pas une certification normative.

## Limites et suite

La version affichée par le produit demeure 6.108. Les snapshots sont fournis par l'opérateur, sans collecte directe via API constructeur. Prochain chantier : relation CMDB et services applicatifs avec provenance explicite et tests de résilience de la chaîne de dépendances.
