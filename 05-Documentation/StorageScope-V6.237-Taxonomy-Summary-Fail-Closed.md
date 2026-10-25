# StorageScope V6.237 — validation fail-closed du résumé unittest

**Auteur : Abdelhalim Talbi**  
**Périmètre : outil de diagnostic de qualification Windows, pas correction fonctionnelle du moteur de stockage.**

## Défaut corrigé

Le classificateur historique pouvait considérer les nombres d'anomalies observées comme cohérents lorsque les lignes de synthèse du journal étaient absentes. Cette valeur par défaut risquait de donner un faux résultat positif à un journal tronqué. Des exécutions unittest concaténées pouvaient aussi être interprétées comme une seule suite, la dernière synthèse écrasant les précédentes.

## Comportement V6.237

Le parseur exige désormais exactement une ligne `Ran <n> tests` et exactement une synthèse finale `FAILED (...)` ou `OK`. Il vérifie que les totaux annoncés correspondent aux enregistrements `FAIL` et `ERROR`, et que le nombre déclaré de tests n'est pas inférieur au nombre d'anomalies extraites. L'absence, la duplication ou l'incohérence des synthèses force `counts_match_summary=false` et un code de sortie non nul.

L'option `--expected-tests N` permet d'imposer un nombre historique attendu. Pour le journal de qualification #39668811238, la commande de contrôle devient :

```powershell
python tools/classify_windows_regression_log.py .\windows-39668811238.log --run-id 39668811238 --expected-tests 958 --json-output .\taxonomy.json --markdown-output .\taxonomy.md
if ($LASTEXITCODE -ne 0) { throw "Journal incomplet ou incohérent : revue manuelle obligatoire" }
```

Le journal doit être un export UTF-8 d'une seule invocation unittest. Si un export de job contient plusieurs invocations, il faut segmenter leurs sorties avant de les qualifier ; le parseur refuse volontairement de les agréger silencieusement.

## Régressions ajoutées

Le nouveau module `test_historical_failure_taxonomy_v6237.py` couvre : synthèse valide, synthèse absente, totaux contradictoires, invocations concaténées, test-count attendu de 958, rendu du rapport incomplet et code de sortie CLI sur journal tronqué.

La suite est intégrée à la CI de gouvernance et au workflow Windows natif. Aucune suite historique n'est désactivée et aucune anomalie n'est annoncée comme corrigée sur la seule base de sa classification.

## Qualification et limites

La qualification native Windows V6.237 doit être lue sur le workflow exécuté pour le HEAD exact de cette branche. Un succès de gouvernance ou un succès sur V6.236/V6.235 ne qualifie pas à lui seul V6.237. Le build Windows automatisé peut utiliser le numéro interne de binaire canonique présent dans `07-Manifestes/VERSION`; ce numéro n'est pas automatiquement le numéro de cette branche de correction.

Cette modification ne reconstitue pas les causes racines par elle-même : elle rend explicites les preuves manquantes. Les catégories du journal 39668811238 restent des classifications heuristiques, et les 13 contrats build/packaging laissés en revue manuelle demeurent ouverts jusqu'à leur reproduction et correction individuelles. Les captures UX réelles, essais SAN/NAS physiques et validation humaine ne sont pas couverts.

## Référentiels d'architecture et de contrôle

- ISO/IEC/IEEE 42010 : traçabilité des décisions, hypothèses et limites de la preuve.
- ITIL 4 : séparation incident, cause probable, action corrective et vérification.
- ISO/IEC 27001 : qualité et intégrité des éléments de preuve de qualification.
- TOGAF et ArchiMate : correspondance entre exigence de qualité, processus de vérification et livrable ; aucun modèle de conformité certifié n'est revendiqué.
- ISO/IEC 27040 : non applicable directement à ce parseur de journaux, mais pertinent aux contrôles de stockage couverts ailleurs par StorageScope.

