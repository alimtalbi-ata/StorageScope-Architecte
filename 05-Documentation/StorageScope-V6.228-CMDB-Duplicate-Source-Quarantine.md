# StorageScope V6.228 — quarantaine des doublons CMDB intra-source

**Auteur : Abdelhalim Talbi — 25 octobre 2026.**

## Défaut reproduit et impact

Deux observations du même collecteur (par exemple `NetApp` et ` netapp `) avec le même numéro de série étaient classées `REVIEW_REQUIRED`, comme s'il s'agissait de deux sources indépendantes. Dans une chaîne de réconciliation, cette fausse indépendance pouvait masquer un doublon d'export, puis contaminer les propositions associées à la CMDB. Cinq tests de non-régression ont reproduit le défaut avant correction (2 échecs et 3 erreurs).

## Correctif métier

Le moteur rapproche les sources par `strip().casefold()` **uniquement pour détecter les doublons**, sans modifier la provenance originale. Un candidat partageant un identifiant fort et provenant de la même source devient `QUARANTINE_DUPLICATE_SOURCE_OBSERVATION`. En présence d'une contradiction forte de série/WWN/UUID/type, la priorité reste `QUARANTINE_IDENTITY_CONFLICT`. La quarantaine se propage à tout le composant connexe des identités, y compris les rapprochements avec une CMDB externe. Le rapport expose `duplicate_source_indices` et `same_source_duplicate`; l'interface de revue indique explicitement les doublons intra-source. Deux sources distinctes continuent à produire `REVIEW_REQUIRED` en l'absence de conflit. Aucune fusion automatique ni écriture CMDB.

## Parcours utilisateur (données fictives, pas de capture réelle)

Entrée : `[{"source":"NetApp","serial":"S1"},{"source":" netapp ","serial":"s1"},{"source":"CMDB","serial":"S1"}]`.

Résultat attendu : `assessment=INCOMPLETE`, `duplicate_source_indices=[0,1]`, `quarantined_indices=[0,1,2]`, `propagated_quarantine_indices=[2]`. Les rapprochements CMDB liés sont bloqués jusqu'à revue humaine. Pour un snapshot indépendant `NetApp` + `CMDB`, l'évaluation reste `REVIEW_REQUIRED`.

Commande de revue, **en lecture seule** : `StorageScope.exe --cmdb-review-file <inventaire.json> <rapport-nouveau.json>`. La sortie doit être un nouveau fichier ; jamais d'écrasement d'une preuve existante.

## Qualification

- `test_cmdb_same_source_duplicate_v6228.py` : cinq scénarios synthétiques (doublon normalisé, priorité des contradictions, propagation, sources indépendantes, visibilité desktop).
- `qualify_frozen_cmdb_duplicate_v6228.py` : deux scénarios exécutés dans le binaire PyInstaller Windows via `--cmdb-review-file`.
- Tests historiques CMDB inchangés, contrôles CI gouvernance Linux/Windows et compilation native Windows maintenus.
- **Statut à la rédaction :** tests ciblés locaux Linux réussis ; **qualification native Windows V6.228 en attente de GitHub Actions**. Ne pas considérer une CI gouvernance verte comme qualification de l'installateur.

## Limites et référentiels

Un identifiant fort répété au sein d'une source peut correspondre à une duplication légitime de données techniques : la quarantaine déclenche une revue, sans suppression. La normalisation ne remplace pas une gouvernance des identifiants par constructeur ni une authentification des collecteurs. Pas de captures réelles, de tests sur baie physique, de validation UX humaine ou de certification.

Alignement : **ITIL 4** (qualité de la CMDB, gestion des changements), **ISO 42010** (traçabilité des décisions de rapprochement), **ISO 27001/27040** (intégrité et provenance des inventaires), **TOGAF/ArchiMate** (relations d'actifs et impacts). Ces référentiels sont des repères de conception, non une certification.
