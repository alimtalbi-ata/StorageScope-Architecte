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

## Lot complémentaire V6.192 (commit `b5ad9a389`)

Sept autres contrats historiques ont été corrigés en **un seul commit atomique** : `test_v642_build_contract.py`, `test_v643_qualification_contract.py`, `test_v645_bootstrap_contract.py`, `test_v646_version_probe.py`, `test_v647_ci_contract.py`, `test_v648_installer_contract.py`, `test_v649_installer_smoke_contract.py`. Chaque contrôle conserve la version minimale historique et exige la cohérence avec la version courante. Les assertions fonctionnelles non liées aux numéros de version sont conservées (interpolation des chemins, SHA-256, code de sortie, préflight, version probe, présence du workflow, désinstallation, reporting et refus de publication sur échec).

**CI Windows intermédiaire #39947273516 : 1 409 tests, 41 failures, 0 errors ; 8 imbriqués PASS ; BUILD FAIL**. Le passage de 51 à 41 failures est confirmé par les journaux Windows. Les sept corrections supplémentaires doivent encore être validées par la CI native déclenchée sur `b5ad9a389`. L'exécution de la CI gouvernance ne suffit pas à qualifier Windows.

## Verdict Windows du second lot — confirmé

**CI #39948341875**, commit `b5ad9a3890577ef95e7d6e86a98c4fa272dc8f7d` : **1 409 tests, 33 failures, 0 errors ; 8 imbriqués PASS ; build FAIL**. Le nombre d'assertions en échec a baissé de 51 à 33 depuis `39941181003`, sur la même taille de suite (1 409). Les sept fichiers du second lot ont donc été évalués par la CI réelle. Les 33 défauts restants portent principalement sur les contrats historiques Windows build, CI, installation et publication ; **PyInstaller et Inno Setup non atteints**. Prochaine action : analyser les assertions des fichiers `test_windows_build_v568.py`, `test_windows_ci_v585.py`, `test_windows_release_v575.py` et corriger les contrats ou défauts fonctionnels sans désactivation.
