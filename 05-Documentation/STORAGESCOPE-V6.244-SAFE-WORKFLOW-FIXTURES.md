# StorageScope V6.244 — staging sûr des fixtures de workflows

**Auteur : Abdelhalim Talbi**  
**Branche : `feature/storagescope-v6.244-safe-workflow-fixtures-20261026`**  
**Base : V6.243 — capture stricte des sorties de sous-processus**

## Constat

Le runner historique `scripts/run_historical_windows_suite.py` copiait les workflows actifs avec `shutil.copytree(..., dirs_exist_ok=True)` vers `04-Tests-et-Qualification/.github`. Avec `dirs_exist_ok=True`, un fichier existant à destination pouvait être remplacé par les octets du dépôt actif sans comparaison préalable. Cela met en danger les fixtures qui conservent intentionnellement un contrat historique.

## Correction V6.244

La copie permissive est remplacée par `stage_workflow_fixtures(source_root, target_root)` :

- les fixtures absentes sont copiées dans un fichier temporaire puis promues par renommage ;
- le contenu copié est comparé octet par octet avant promotion ;
- un fichier déjà présent et identique est laissé en place (opération idempotente) ;
- un fichier existant divergent est refusé sans modification de ses octets ;
- les collisions fichier/répertoire, les liens symboliques et les entrées non régulières sont refusés ;
- les erreurs identifient le chemin relatif de la fixture en cause.

Aucun contrôle n'est désactivé. Le runner doit continuer à échouer en présence d'une collision non approuvée plutôt que d'écraser silencieusement un témoin historique.

## Tests de régression

Ajout : `04-Tests-et-Qualification/test_historical_workflow_fixture_staging_v6244.py`.

Cinq scénarios couvrent la copie byte-for-byte, l'idempotence, la collision avec conservation de la fixture, la collision fichier/répertoire et l'absence de source.

Commande :

```powershell
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_historical_workflow_fixture_staging_v6244.py' -v
```

Cette suite est ajoutée aux jobs de gouvernance Linux et Windows. La qualification native Windows demeure un contrôle distinct et doit réussir sur le HEAD exact avant de qualifier un nouveau paquet binaire.

## Portée et limites

Cette correction protège l'intégrité de l'arbre de tests et la répétabilité du diagnostic ; elle ne répare pas à elle seule les 225 anomalies de la baseline `#39668811238` (958 tests, 52 failures, 173 errors). Les étiquettes de cause racine restent des hypothèses tant que chaque enregistrement n'est pas relié à un correctif et à une régression.

Aucun test sur baie SAN/NAS physique, aucune écriture CMDB, aucun déploiement, aucune capture GUI réelle ni certification ISO n'est revendiqué. `main` reste préservée et la PR doit rester en draft.

## Référentiels

- **ISO/IEC/IEEE 42010** : expliciter l'hypothèse de reproductibilité des preuves de qualification.
- **ITIL 4** : conserver la traçabilité des changements et des preuves de vérification.
- **ISO/IEC 27001 / 27040** : limiter les modifications non autorisées des éléments de preuve et des fixtures.
- **TOGAF / ArchiMate** : relier le contrôle à la vue de cycle de vie et au processus de qualification ; ce correctif ne vaut pas attestation de conformité.
