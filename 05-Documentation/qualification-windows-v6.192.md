# StorageScope V6.192 — Contrats de régression historiques Windows

**Auteur : Abdelhalim Talbi**  
**Date : 23 octobre 2026**  
**Statut : correction publiée, qualification native Windows en cours — ne pas fusionner automatiquement.**

## Situation vérifiée

La CI Windows `39941181003` (commit `ff352bab72e19b4dd3ccd9920ee7590dfb5054c8`) a exécuté **1 409 tests principaux : 51 failures, 0 errors**, plus **8 tests imbriqués PASS**. Le build a été interrompu avant PyInstaller et Inno Setup. L'exécution historique `39668811238` (958 tests, 52 failures, 173 errors) est une référence antérieure avec découverte de tests différente ; ces chiffres ne sont pas directement comparables.

## Cause racine corrigée dans ce cycle

Quatre fichiers de tests exigeaient des versions figées V6.29, V6.36, V6.37 et V6.38 alors que la version courante déclarée dans `07-Manifestes/VERSION`, `03-Sources/storagescope_windows.py` et `02-Compilation-Windows/StorageScope.iss` est V6.108. La logique de ces tests bloquait donc une montée de version légitime. Les contrats de sécurité n'ont pas été retirés :

- `test_v629_integration.py` : version minimale V6.29 et égalité source/manifeste ; navigation embarquée, syntaxe des modules et parent de fenêtre conservés.
- `test_release_v636.py` : version minimale V6.36, cohérence manifeste/source/Inno, présence et protections du preflight stable, fichiers de staging.
- `test_release_v637.py` : version minimale V6.37, noms d'artefacts calculés depuis VERSION, SHA-256, garde de code de sortie, preflight et rétention des diagnostics.
- `test_v638_stage_contract.py` : version minimale V6.38, cohérence source/Inno, lecture dynamique de VERSION, contrôles fail-closed et vérificateur Windows.

Ces modifications sont **des corrections de contrats de tests**, pas une démonstration que les fonctions natives Windows sont opérationnelles. Aucune assertion de sécurité ou de publication n'a été neutralisée.

## Chaîne de qualification exigée

1. `unittest` Windows : au moins 958 tests principaux, 8 imbriqués, zéro échec et zéro erreur, rapports et journaux intègres.
2. Compilation PyInstaller : exécutable et gate de mise à jour, contrôle des codes de sortie et de la version réelle.
3. Inno Setup : installateur versionné, refus d'installation sur données corrompues, conservation des données utilisateur.
4. Installation/désinstallation et portable : tests Windows réels, contrôles fonctionnels et manifestes SHA-256.
5. Publication seulement après qualification consolidée PASS. Captures réelles de l'interface : **absentes pour ce cycle**.

## CI déclenchée

Nouvelle exécution Windows déclenchée par les commits de ce cycle : `39947273516` sur `58011c045ccccdfa201b2047622221158f05489d`. **Verdict non encore connu au moment de cette documentation.** Ne pas interpréter une CI gouvernance verte comme une qualification Windows.

## Risques et prochaines actions

Examiner la liste exacte des assertions restantes après V6.192, distinguer attentes figées et défauts produit, puis corriger les vrais bugs et les contrats périmés sans affaiblissement. Les changements restent sur la branche de la PR draft #4 ; `main` est préservée. Pas de binaires Windows ni de captures réelles publiés.
