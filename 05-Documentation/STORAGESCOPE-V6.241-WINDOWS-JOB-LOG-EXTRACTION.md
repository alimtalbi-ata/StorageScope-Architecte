# StorageScope V6.241 — extraction bornée des journaux CI Windows

**Auteur : Abdelhalim Talbi**  
**Branche : feature/storagescope-v6.241-job-log-bounded-extraction-20261025**  
**Base : StorageScope V6.240**  
**Périmètre :** diagnostic des échecs historiques ; aucun changement du produit ni des contrôles de qualification.

## Reproduction sur le run historique

Le run #39668811238, job Windows 119460870039, a été relu depuis son journal Actions complet. La sortie contient exactement 225 enregistrements unittest : **52 FAIL et 173 ERROR**, avec un unique résumé « Ran 958 tests » suivi de « FAILED (failures=52, errors=173) ».

Le journal continue ensuite avec les erreurs PowerShell de construction et de consolidation. Le classificateur V6.237/V6.238 fonctionne en mode strict sur une invocation isolée ; appliqué à tout le journal du job, il marque à juste titre la présence de texte après le résumé comme ambiguë. Ce comportement est sécurisant pour l’éligibilité d’une preuve isolée, mais n’offre pas de mode explicite pour extraire l’invocation historique à partir du journal complet.

## Correction V6.241

Ajout de l’option --extract-failed-unittest-block à tools/classify_windows_regression_log.py.

- Exige une seule ligne « Ran N tests » et une seule synthèse terminale.
- N’accepte cette extraction que pour une invocation échouée ; une sortie OK se traite avec le parseur ordinaire.
- Refuse plusieurs invocations, les enregistrements FAIL/ERROR après la synthèse ou l’absence d’enregistrements.
- Extrait uniquement l’intervalle test allant du premier enregistrement FAIL/ERROR à la synthèse terminale.
- Conserve le parseur strict d’origine : le texte de wrapper après la synthèse reste rejeté en mode normal.
- Ajoute la provenance de l’extraction (lignes source, résumé, nombre d’enregistrements et lignes de wrapper écartées) au rapport JSON et à son rendu Markdown.

## Vérification attendue

    python -m unittest discover -s 04-Tests-et-Qualification -p test_historical_job_log_extraction_v6241.py -v
    python tools/classify_windows_regression_log.py windows-job.log --run-id 39668811238 --expected-tests 958 --extract-failed-unittest-block --json-output taxonomy-v6241.json --markdown-output taxonomy-v6241.md

Le test local synthétique vérifie la délimitation et les refus fail-closed. La qualification automatique ciblée doit passer sur Linux et Windows. Le run historique réel ne doit pas être requalifié en vert rétroactivement : il s’agit d’un diagnostic de son journal, non d’une modification du run.

## Interprétation de cause racine

Les lignes d’exception du journal comprennent des erreurs d’import (ImportError/ModuleNotFoundError), des chemins/fichiers absents (FileNotFoundError), des PermissionError et des assertions historiques. Ces lignes peuvent se chevaucher dans un même traceback ; elles ne doivent pas être additionnées comme s’il s’agissait de causes distinctes. La classification doit compter les 225 enregistrements unittest une seule fois, sur la signature terminale de chaque détail, et marquer les causes sans signature suffisante pour revue manuelle.

Cette évolution ne corrige pas à elle seule toutes les anomalies originales. Elle rend leur classement reproductible à partir d’un journal Actions complet, sans masquer les contrôles. Aucun test désactivé, aucune donnée réelle touchée, aucun secret ajouté. Pas de qualification de baie physique ni de certification ISO revendiquée.
