# StorageScope V6.246 — traçabilité des 13 contrats historiques de faible confiance

**Auteur : Abdelhalim Talbi**  
**Branche : feature/storagescope-v6.246-low-confidence-closure-20261026**  
**Base : V6.245 — frontières sûres des fixtures historiques**

## Objectif

Le run Windows historique 39668811238 exécutait 958 tests et terminait avec 52 failures et 173 errors. La taxonomie de son journal comporte 225 enregistrements répartis en huit catégories. Treize enregistrements ont été classés RELEASE_BUILD_OR_SOURCE_CONTRACT avec une confiance faible.

V6.246 rend ces 13 enregistrements exécutables et vérifiables séparément à travers huit sélecteurs unittest actuels. La taxonomie de référence demeure historique et immuable.

## Mécanisme

- scripts/unittest_discover_with_result.py accepte --test-selector de manière répétable. Un sélecteur invalide devient un échec unittest au lieu d'être ignoré.
- scripts/run_historical_windows_suite.py --focus-low-confidence-contracts-only prépare un checkout temporaire selon les règles de staging existantes, puis lance huit sélecteurs dans des sous-processus réels.
- Chaque sortie est capturée en octets, conservée et décodée avec le décodeur strict existant. Le rapport lie chaque enregistrement historique à son sélecteur et au résultat réel.
- Une méthode test_bootstrap_files_exist couvre six noms via des subTests ; elle n'est PASS que si tous les subTests passent.
- Le mode ciblé est intégré à la CI Linux/Windows de gouvernance et au workflow Windows natif. Le rapport et les journaux des huit sélecteurs sont publiés comme artefacts.

## Cartographie

| IDs | Enregistrements historiques | Sélecteur actuel |
|---|---|---|
| LC-001 | test_real_native_schema_passes | test_qualification_v699.QualificationV699.test_real_native_schema_passes |
| LC-002 | test_scripts | test_release_contract_v635.ReleaseContract.test_scripts |
| LC-003 à LC-008 | test_bootstrap_files_exist : Construire-StorageScope.cmd, build-all-windows.ps1, StorageScope.spec, StorageScope.iss, requirements-build.txt, verify-windows-build.py | test_release_package_v615.TestReleaseV615.test_bootstrap_files_exist (subTests nommés) |
| LC-009 | test_preflight | test_release_v636.ReleaseContracts.test_preflight |
| LC-010 | test_cumulative_packaging | test_windows_embedded_campaign_v564.EmbeddedCampaignTests.test_cumulative_packaging |
| LC-011 | test_script_present | test_windows_install_v576.WindowsInstallQualificationV578.test_script_present |
| LC-012 | test_installer_files | test_windows_packaging_v563.TestWindowsPackaging563.test_installer_files |
| LC-013 | test_complete_success | test_windows_v694.ReleaseQualification.test_complete_success |

La référence versionnée est 04-Tests-et-Qualification/windows-historical-failure-taxonomy-v39668811238.json. Le test V6.246 vérifie que les 13 clés couvrent exactement les 13 cas de manual_follow_up_tests et que les huit sélecteurs existent dans les sources actuelles.

## Critères de contrôle

- Treize enregistrements de baseline, sans omission ni doublon, et huit sélecteurs.
- Chaque sélecteur doit retourner un statut unittest OK, un compte positif et un code retour zéro.
- Un sélecteur absent, un échec ou un résumé incomplet fait échouer le rapport.
- Le rapport conserve historical_root_cause_linkage = NOT_ESTABLISHED et root_cause_resolution_proven = false.
- La qualification native, PyInstaller, Inno Setup, installation/désinstallation, portable et SHA-256 restent des contrôles séparés. Le mode ciblé ne qualifie pas les binaires à lui seul.

## Commandes

    python -m unittest discover -s 04-Tests-et-Qualification -p 'test_historical_low_confidence_closure_v6246.py' -v
    python scripts/run_historical_windows_suite.py --repo . --focus-low-confidence-contracts-only --report TEMP_DIR/report.json

Les journaux de chaque sous-processus sont enregistrés à côté du rapport pour permettre la revue des preuves.

## Limites

PASS signifie uniquement que les tests actuels correspondants passent sur ce HEAD et dans le staging présenté par le runner. Cela ne reconstitue pas automatiquement le code exact à l'origine de chaque échec le 21 octobre et ne prouve pas la réparation individuelle des 225 anomalies historiques. Le run #39668811238 reste une baseline en échec immuable.

Aucun test sur baies SAN/NAS physiques, aucune capture d'interface réelle et aucune certification ISO ne sont revendiqués. La traçabilité contribue à la gouvernance des preuves et des changements (ITIL 4, ISO/IEC 27001/27040, ISO/IEC/IEEE 42010). TOGAF et ArchiMate peuvent référencer ce contrôle dans les vues de processus et d'architecture ; aucune conformité certifiée n'est affirmée.
