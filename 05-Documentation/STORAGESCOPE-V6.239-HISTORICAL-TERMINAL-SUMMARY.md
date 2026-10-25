# StorageScope V6.239 — résultat terminal fiable de la suite historique

Auteur : Abdelhalim Talbi  
Branche : feature/storagescope-v6.239-historical-terminal-summary-20261025  
Base : V6.238 46e486cd9e58c3228c353831eb687d64eb50b862  
Statut de qualification : tests ciblés locaux exécutés ; qualification native Windows propre à ce HEAD à attendre dans GitHub Actions.

## Cause racine

La suite historique contient des tests qui lancent volontairement des sous-processus unittest en échec afin de vérifier les portes négatives. Le lanceur parent fusionne stdout et stderr. Comme les tests écrivent généralement sur stdout tandis que unittest.TextTestRunner écrit son résultat sur stderr, le buffering peut réordonner les lignes fusionnées : la synthèse OK de la suite parente peut apparaître avant la sortie FAILED du contrôle imbriqué. Un parseur qui choisit simplement la dernière ligne OK ou FAILED peut donc annoncer à tort l’état de la suite parente.

## Correction V6.239

- Ajout de scripts/unittest_discover_with_result.py, qui lance la découverte unittest sans désactiver de test et émet une seule ligne JSON STORAGESCOPE_UNITTEST_RESULT après vidage explicite des flux.
- scripts/run_historical_windows_suite.py consomme cette ligne comme résultat autoritatif, valide les champs requis, les types et les comptes, et refuse les marqueurs dupliqués, incomplets ou suivis de données non vides.
- Le journal brut demeure conservé avec son empreinte SHA-256. captured_output_symptom_counts reste un diagnostic de toute la sortie capturée, pouvant inclure des contrôles négatifs imbriqués ; ce compteur ne remplace pas le résultat terminal de la suite.
- La voie de compatibilité qui lit les anciens journaux standards reste testée.

## Vérification locale

Commandes exécutées depuis la racine du dépôt :

python -m py_compile scripts/run_historical_windows_suite.py scripts/unittest_discover_with_result.py 04-Tests-et-Qualification/test_historical_suite_summary_v6239.py
PYTHONPATH=03-Sources:04-Tests-et-Qualification:scripts python -m unittest discover -s 04-Tests-et-Qualification -p test_historical_suite_summary_v6239.py -q
PYTHONPATH=03-Sources:04-Tests-et-Qualification:scripts python -m unittest discover -s 04-Tests-et-Qualification -p test_historical_runner_evidence_v6190.py -q
PYTHONPATH=03-Sources:04-Tests-et-Qualification:scripts python -m unittest discover -s 04-Tests-et-Qualification -p test_historical_failure_taxonomy_v6236.py -q
PYTHONPATH=03-Sources:04-Tests-et-Qualification:scripts python -m unittest discover -s 04-Tests-et-Qualification -p test_historical_failure_taxonomy_v6237.py -q
PYTHONPATH=03-Sources:04-Tests-et-Qualification:scripts python -m unittest discover -s 04-Tests-et-Qualification -p test_windows_historical_gate_v6187.py -q
PYTHONPATH=03-Sources:04-Tests-et-Qualification:scripts python -m unittest discover -s 04-Tests-et-Qualification -p test_runner_utf8_v6188.py -q
PYTHONPATH=03-Sources:04-Tests-et-Qualification:scripts python -m unittest discover -s 04-Tests-et-Qualification -p test_historical_runner_legacy_workflow_v6189.py -q
python 02-Compilation-Windows/audit-build-contract.py

La preuve locale inclut un sous-processus unittest réellement en échec, volontairement lancé par un test parent réussi. Le résultat autoritatif du parent doit rester OK ; la sortie de l'enfant reste disponible dans le journal capturé.

## Portée et limites

Cette correction rend la décision de réussite du runner de suite plus fiable ; elle ne corrige pas par elle-même les 225 anomalies du run historique de référence 39668811238 (52 failures, 173 errors). L'ancien journal et sa taxonomie sont conservés comme preuve historique. Le prochain build Windows exact-HEAD doit confirmer la suite historique complète, PyInstaller, Inno Setup, rejet d'installateur corrompu, installation/désinstallation, portable et manifestes SHA-256.

Le numéro produit reste 6.108 ; V6.239 identifie ce cycle de développement. Les tests SAN/NAS de la CI sont synthétiques et en lecture seule : aucune validation physique de baie, capture d'écran réelle ou qualification UX humaine n'est revendiquée. Aucune donnée CMDB n'est modifiée et aucune fusion automatique n'est autorisée.
