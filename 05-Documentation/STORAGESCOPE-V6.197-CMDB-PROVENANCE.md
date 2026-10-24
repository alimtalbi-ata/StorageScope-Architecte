# StorageScope V6.197 — Réconciliation CMDB avec provenance et quarantaine

**Auteur : Abdelhalim Talbi** — 23 octobre 2026
**État : branche de développement / PR draft ; validation Windows CI et revue humaine obligatoires.**

## Problème corrigé

La réconciliation historique V6.19 rapprochait des enregistrements sur serial, wwn ou uuid même lorsque la provenance source était absente. Elle ne signalait pas les contradictions entre identifiants forts : un numéro de série identique associé à deux WWN différents pouvait être présenté comme un candidat ordinaire. L'export CLI pouvait écraser un rapport existant.

V6.197 **n'effectue aucune fusion ni modification de CMDB**. Elle réduit les faux rapprochements, rend les contradictions explicites et protège les preuves de revue.

## Contrat fonctionnel

Entrée : tableau JSON d'enregistrements avec source, serial/wwn/uuid et collected_at facultatif. Source est obligatoire et doit être une chaîne non vide. Au moins un identifiant fort exploitable est requis. Les valeurs unknown, n/a, na, none, null, not available et - ne constituent jamais une preuve d'identité. La normalisation des identifiants applique strip et casefold ; elle ne prétend pas remplacer les règles propres à chaque constructeur.

Les enregistrements sans source ou sans identifiant fort sont signalés dans invalid_records et **exclus du rapprochement**. Les paires ne sont proposées que si elles partagent au moins un identifiant fort. Si un autre identifiant fort est présent des deux côtés et contradictoire, la paire reçoit QUARANTINE_IDENTITY_CONFLICT, la liste identity_conflicts et des quarantined_indices. Une correspondance non contradictoire reçoit REVIEW_REQUIRED, jamais une approbation automatique.

Chaque candidat conserve indices, sources, provenance (source et collected_at tel que fourni, ou null), identity_evidence, conflits d'attributs et contradictions d'identité. Aucun horodatage, score de confiance ou inventaire constructeur n'est inventé. Le rapport conserve le schéma storagescope.reconciliation.v1 pour compatibilité et ajoute assessment (INCOMPLETE, REVIEW_REQUIRED, NO_CANDIDATES). automatic_merges=0 et destructive_changes=0 restent invariants.

## Sécurité et bornes

- Maximum **10 000 enregistrements** par analyse ; au-delà, refus explicite.
- Maximum **50 000 paires candidates** ; au-delà, refus explicite plutôt qu'explosion quadratique silencieuse.
- Export JSON exclusivement dans un **nouveau fichier** (mode x) : un rapport préexistant ne peut pas être remplacé.
- Code de sortie CLI 2 pour un résultat incomplet, 0 pour une revue valide sans action destructive ; une exception entraîne un code non nul.
- Les données source ne sont jamais modifiées ; aucun accès réseau, écriture CMDB ou action de remédiation.

## Exemple de commande

    python 03-Sources/inventory_reconcile_v619.py inventaires.json --output revue-cmdb.json

Exemple **fictif** : deux entrées de sources NetApp et CMDB ont le même serial=S1, mais des WWN différents. La sortie doit signaler identity_evidence=["serial"], identity_conflicts sur le champ wwn, action=QUARANTINE_IDENTITY_CONFLICT et assessment=INCOMPLETE. Ce scénario est couvert par un test automatisé réel ; ce paragraphe n'est pas une capture d'exécution d'un équipement.

## Architecture et gouvernance

Inventaires fournisseurs / CMDB (JSON) → validation provenance + identités → index des identifiants forts → candidats bornés → comparaison des identifiants contradictoires → rapport de revue protégé contre l'écrasement → validation humaine ultérieure.

Ce processus soutient la traçabilité des décisions (ISO 42010), l'évaluation des écarts (TOGAF), les relations entre composants (ArchiMate), la qualité des actifs de configuration (ITIL 4) et la protection des preuves de revue (ISO 27001 / ISO 27040). Il ne constitue pas une certification.

## Qualification et limites

Les **21 tests locaux Linux** (8 tests historiques V6.19 + 13 nouveaux tests V6.197) ont été exécutés et ont réussi le 23 octobre 2026. Ils vérifient provenance absente, faux identifiants, contradictions série/WWN/UUID, déterminisme, non-mutation, bornes, refus d'écrasement et codes de sortie CLI. Les workflows GitHub Linux/Windows et la chaîne native Windows complète doivent encore confirmer la branche exacte ; **ne pas déclarer Windows V6.197 qualifié avant leurs résultats**.

La nouvelle logique s'applique au module de réconciliation historique et à son CLI Python. Elle ne prouve **pas** encore une intégration au panneau SAN/NAS de l'exécutable Windows V6.196. Les collecteurs NetApp, Dell EMC, Pure, IBM, HPE, Cisco et Brocade, l'authenticité des identités, les liens de dépendance et la validation UX manuelle restent à développer/qualifier. Aucune capture réelle d'interface n'est disponible pour ce cycle.
