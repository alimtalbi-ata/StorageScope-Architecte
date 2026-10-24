# StorageScope V6.198 — Revue CMDB native Windows

**Auteur : Abdelhalim Talbi** — 23 octobre 2026. **Statut : PR draft, qualification CI requise.**

## Objectif et usage

Le diagnostic Windows propose désormais **Réconcilier un inventaire CMDB (JSON)…**. Le traitement est local, en lecture seule : il charge un tableau JSON, exige une provenance `source` pour participer aux rapprochements, compare les identifiants forts (`serial`, `wwn`, `uuid`) et affiche les candidats et quarantaines. Aucune découverte réseau, fusion ou modification de CMDB n'est réalisée.

La commande exécutable `StorageScope.exe --cmdb-review-file ENTREE.json RAPPORT.json` écrit un rapport JSON **uniquement si le fichier de destination n'existe pas**. Une entrée malformée doit provoquer un code de sortie non nul, sans rapport créé. Le code de sortie 0 de cette commande signifie que l'export s'est correctement déroulé, **pas** que les données sont sans risque : lire `assessment`, `invalid_records` et `quarantined_indices` dans le rapport.

## Contrats de sécurité

Entrée UTF-8 avec BOM facultatif, limite de 8 Mio ; clés JSON dupliquées, `NaN`, `Infinity`, erreurs d'encodage et JSON invalide sont rejetés. Le moteur V6.197 conserve sa limite de 10 000 enregistrements et 50 000 paires candidates. Les enregistrements sans provenance ou identifiant fort ne sont pas rapprochés ; les contradictions d'identifiants sont placées en quarantaine. La présentation est limitée à 100 candidats et 100 invalides, mais affiche systématiquement les totaux et les lignes omises.

## Qualification reproductible

- `python -m unittest discover -s 04-Tests-et-Qualification -p 'test_cmdb_review_desktop_v6198.py' -v`
- CI gouvernance : tests Linux et Windows, incluant l'intégration CLI et la fermeture des imports PyInstaller.
- CI Windows native : construction PyInstaller et Inno Setup, test de l'exécutable gelé avec deux identifiants contradictoires, contrôle du rapport et refus d'une clé JSON dupliquée ; conserver les contrôles historiques d'installation, désinstallation, portable et SHA-256.

## Limites et preuves

Le schéma logique est **Inventaire JSON → parseur borné → réconciliation V6.197 → quarantaines + preuves → vue Diagnostic / rapport JSON**. Il s'agit d'un schéma conceptuel, pas d'une capture réelle. Aucun test d'ergonomie humaine ou capture de l'interface Windows n'est disponible à ce stade. Ne pas annoncer une qualification Windows V6.198 tant que la CI native de cette branche n'a pas conclu SUCCESS.

**Référentiels :** ISO 42010 (traçabilité des vues et décisions), ITIL 4 (qualité des données de configuration), ISO 27001/27040 (intégrité et protection des preuves) ; les alignements sont indicatifs, non des certifications.
