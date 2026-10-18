StorageScope v6.50 — Gouvernance et pagination

Auteur : Abdelhalim Talbi

Périmètre : correction de l’interface Tkinter de revue humaine, sans modification des règles de décision ni fusion automatique.

Constat : une nouvelle analyse conservait le numéro de page précédent ; les sélections d’interface devenues obsolètes pouvaient être réutilisées.

Correction : page_bounds borne les pages après filtrage ; rechargement à la page 1 ; protection de la sélection avant lecture et décision ; titre actualisé.

Architecture : inventaire JSON → governance_service.assess → reconciliation + identity_policy → governance_desktop (filtrage, pagination, décision explicite) → review_registry_v622 (SQLite + audit).

Sécurité : les propositions BLOCKED_CONTRADICTION restent visibles mais non approuvables ; aucune fusion automatique.

Tests : sept nouveaux tests unitaires pour bornes, filtres, indices et blocage ; exécution Linux seulement.

Validation Windows : exécuter Construire-StorageScope.cmd, puis la qualification native et le test d’installation ; inspection humaine de la fenêtre Gouvernance nécessaire.

Captures : aucune capture réelle Windows disponible. Les descriptions ci-dessus ne sont pas des captures ni des preuves de recette graphique.