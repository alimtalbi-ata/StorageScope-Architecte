# StorageScope V6.258 — preuve de diagnostic pour les 225 anomalies historiques

**Auteur : Abdelhalim Talbi**  
**Date : 27 octobre 2026**  
**Branche :** \`feature/storagescope-v6.258-historical-diagnostic-evidence-20261027\`  
**Base :** V6.257 — validation stricte des preuves de qualification Windows

## Objectif

Rendre le triage historique contrôlable test par test sans exporter les traceback complets, les lignes de code ou des éventuels secrets. Le rapport V2 conserve, par FAIL/ERROR, le type et le message d'exception après assainissement, jusqu'à huit frames relatives, la longueur du détail source et son empreinte SHA-256. Le détail brut n'est jamais recopié dans le rapport.

Le classement de catégorie reste heuristique. Une catégorie attribuée à chaque symptôme ne signifie pas que sa cause racine est prouvée, ni que le symptôme est corrigé.

## Référence d'origine — run 39668811238

L'artefact de diagnostic du run Windows contient le résumé cohérent : **958 tests, 52 failures, 173 errors**, soit **225 enregistrements**. Le job a échoué à l'étape de build Windows ; la qualification native, l'installation/désinstallation et le test portable avaient été ignorés dans ce run. Ce résultat historique ne doit pas être réécrit à la lumière des exécutions récentes.

La taxonomie publiée pour ce run répartit les enregistrements ainsi :

| Catégorie probable | Échecs | Erreurs | Total |
|---|---:|---:|---:|
| Arborescence de test / répertoire courant | 1 | 99 | 100 |
| Racine d'import / chemin source | 0 | 50 | 50 |
| Attente de version historique devenue obsolète | 29 | 0 | 29 |
| Cycle de vie des handles SQLite / fichiers sous Windows | 0 | 17 | 17 |
| Contrat source historique | 9 | 4 | 13 |
| Contrat de build / livraison (confiance faible) | 13 | 0 | 13 |
| Structure de fixture / exécutable Windows | 0 | 2 | 2 |
| Dépendance de test manquante (Pillow) | 0 | 1 | 1 |
| **Total** | **52** | **173** | **225** |

Le log d'origine confirme des erreurs d'import telles que \`ModuleNotFoundError: No module named 'storagescope_windows'\` et des imports de modules historiques (par exemple \`windows_accessibility_v610\`). Il contient aussi un \`FileNotFoundError\` pour un fichier sous \`04-Tests-et-Qualification\`. Ces extraits expliquent pourquoi les familles « racine d'import » et « arborescence/chemin » méritent une priorité de correction, mais ne suffisent pas à prouver une cause unique pour chaque ligne.

## Amélioration V6.258

Le classificateur \`tools/classify_windows_regression_log.py\` publie désormais le schéma \`storagescope.windows-historical-failure-taxonomy.v2\`. Chaque ligne possède \`diagnostics\` avec :

- \`exception_type\` et \`exception_message\` assaini, limités à 500 caractères ;
- au plus huit frames avec chemin relatif au dépôt, numéro de ligne et nom de fonction ; aucun extrait de code ;
- \`detail_sha256\` et \`detail_chars\` permettant de distinguer les entrées ;
- \`raw_detail_retained: false\`.

Les messages sont nettoyés des principaux motifs de secrets (tokens GitHub, Bearer, champs token/password/secret/API key) et des racines de chemins absolus. Cette réduction diminue l'exposition mais n'est pas une garantie que toute chaîne secrète inconnue puisse être détectée ; le rapport ne doit pas contenir de détail brut.

## Validation de non-régression

Commande ciblée :

\`\`\`powershell
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_historical_failure_diagnostic_evidence_v6258.py' -v
\`\`\`

Le test utilise des fixtures synthétiques : exception/import, chemins Windows vers chemins relatifs, limites de taille, redaction, fingerprint SHA-256 et rendu Markdown. Il ne prétend pas rejouer les 225 anomalies historiques.

Le nouveau fichier est raccordé à la gouvernance Linux/Windows et au workflow natif Windows. Le résultat de qualification de cette PR doit être examiné sur son HEAD exact : une CI de gouvernance verte à elle seule ne qualifie ni l'exécutable, ni Inno Setup, ni le portable.

## Dette non clôturée

Sur le parent V6.257, le workflow Windows natif a exécuté avec succès le build PyInstaller, les contrôles frozen, le rejet d'un installateur invalide, l'installation/désinstallation, le portable et la vérification SHA-256. La suite actuelle Windows rapporte 1 874 tests réussis sur ce HEAD parent. Cette donnée est une preuve actuelle séparée, pas une modification du run de référence.

La correspondance individuelle des 225 enregistrements avec (1) une cause racine démontrée, (2) un commit correctif et (3) un test de non-régression demeure **NOT_ESTABLISHED**. V6.258 rend les détails diagnostiques auditables pour entreprendre ce travail. Priorité de suivi : les 17 incidents SQLite, les 29 attentes de version, les 13 contrats source et les 13 contrats de build à confiance faible ; conserver aussi la revue des chemins/imports, des deux fixtures et de Pillow. Aucun test ni contrôle n'est désactivé.

Aucun test sur baie physique, aucune capture réelle d'interface et aucune certification ISO/IEC, TOGAF, ArchiMate ou ITIL ne sont revendiqués.
