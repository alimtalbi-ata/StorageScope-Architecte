# StorageScope V6.196 — Revue SAN/NAS dans la console Windows

**Auteur : Abdelhalim Talbi** — 23 octobre 2026  
**Statut : PR draft ; revue et qualification de la branche requises avant diffusion.**

## Besoin et périmètre

Le moteur SAN/NAS introduit en V6.194/V6.195 fonctionnait en bibliothèque/CLI sans preuve de présence dans le produit Windows compilé. V6.196 expose son analyse dans **Diagnostic local** et dans une commande non interactive du même exécutable, afin de permettre une vérification du *binaire livré* et pas uniquement des sources.

**Parcours utilisateur** : StorageScope → Diagnostic → « Analyser une topologie SAN/NAS (JSON)… » → sélectionner un instantané local → lire l'état `INCOMPLETE`, `RISKS_FOUND` ou `NO_FINDINGS_IN_ASSESSED_SCOPE`, les preuves et les actions recommandées. Le bouton « Actualiser le diagnostic » revient au diagnostic système local. L'analyse ne se connecte à aucun équipement et ne modifie ni CMDB ni inventaire.

**Commande Windows** (le chemin de sortie doit être inexistant) :

```powershell
StorageScope.exe --storage-risk-file "C:\temp\topology.json" "C:\temp\risk-report.json"
```

La sortie est un JSON `storagescope.storage-risk.v1` avec `automatic_changes=0`. L'exécutable ne doit pas renvoyer un succès sur un JSON ambigu ou invalide. L'analyse est un **instantané**, sans découverte réseau, ni confirmation indépendante des états des chemins.

## Contrôles de confiance

- **Borne d'entrée** : maximum 8 MiB ; UTF-8 ou UTF-8 BOM.
- **JSON fail-closed** : clés dupliquées refusées, valeurs NaN/Infinity refusées, encodage et structure invalides refusés.
- **Non-destruction** : aucune écriture dans la source ; export exclusivement vers un fichier nouveau (`open('x')`), aucun écrasement silencieux.
- **Moteur inchangé** : les identifiants d'actifs/partages dupliqués restent en quarantaine ; une seule fabric active ne prouve pas la résilience ; absence d'inventaire signifie `INCOMPLETE`.
- **Preuves lisibles** : criticité, code, objet, preuve et recommandation. Le rendu limite l'affichage à 200 constats et signale explicitement les constats supplémentaires.
- **Intégration PyInstaller** : import statique du module adaptateur, lui-même dépendant de `storage_path_risk_v6194`, visible dans `windows_module_inventory.reachable_modules`.

## Qualification prévue et limites

Les tests ciblés de l'adaptateur valident les erreurs d'entrée, le mode lecture seule, les exports non écrasants et les conclusions de risque. Deux tests supplémentaires vérifient l'entrée CLI du shell Windows et la fermeture statique des imports PyInstaller. Le workflow natif ajoute un **smoke test sur l'exécutable réellement compilé**, avec cas positif (capacité critique + fabric unique) et cas négatif (clé JSON dupliquée rejetée). Les contrôles historiques 958 + 8, PyInstaller, Inno Setup, installation/désinstallation, portable et SHA-256 restent obligatoires et ne sont pas désactivés.

**Ne pas assimiler CI verte à une validation UX manuelle.** Aucune capture d'écran réelle de la nouvelle fenêtre n'est disponible dans ce cycle ; aucune capture synthétique ne sera présentée comme réelle. Les collecteurs multi-constructeurs et la réconciliation automatique CMDB restent hors périmètre V6.196.

## Référentiels et suites

La traçabilité des constats contribue à ISO 42010 (préoccupations/vues d'architecture), TOGAF (évaluation d'écarts), ArchiMate (relations et dépendances), ITIL 4 (gestion des actifs et incidents), ISO 27001/27040 (intégrité des preuves, résilience et contrôle des données). Il s'agit d'un **alignement de conception**, pas d'une certification.

Prochaine étape : revue humaine de la PR empilée, démonstration graphique sur Windows réel, captures horodatées, puis collecte NetApp/Dell EMC/Pure/IBM/HPE et réconciliation CMDB avec provenance et règles d'identité explicites. Ne jamais fusionner automatiquement dans `main`.
