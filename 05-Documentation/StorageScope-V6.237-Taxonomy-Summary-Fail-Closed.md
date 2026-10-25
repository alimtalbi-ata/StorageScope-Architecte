# StorageScope V6.237 — validation fail-closed du résumé unittest

**Auteur : Abdelhalim Talbi**  
**Périmètre : outil de diagnostic de qualification Windows, pas correction fonctionnelle du moteur de stockage.**

## Défaut corrigé

Le classificateur historique pouvait considérer les nombres d'anomalies observées comme cohérents lorsque les lignes de synthèse du journal étaient absentes. Cette valeur par défaut risquait de donner un faux résultat positif à un journal tronqué. Des exécutions unittest concaténées pouvaient aussi être interprétées comme une seule suite, la dernière synthèse écrasant les précédentes.

## Comportement V6.237

Le parseur exige désormais exactement une ligne `Ran <n> tests` et exactement une synthèse finale `FAILED (...)` ou `OK`. Il vérifie que les totaux annoncés correspondent aux enregistrements `FAIL` et `ERROR`, et que le nombre déclaré de tests n'est pas inférieur au nombre d'anomalies extraites. Une synthèse `FAILED` qui annonce zéro échec et zéro erreur est impossible pour une sortie unittest cohérente et est rejetée. Tout contenu non vide après la synthèse finale est aussi refusé, car l'entrée doit contenir une invocation isolée, pas un journal concaténé avec la sortie d'une autre étape. L'absence, la duplication, la sortie terminale supplémentaire ou l'incohérence des synthèses force `counts_match_summary=false` et un code de sortie non nul.

L'option `--expected-tests N` permet d'imposer un nombre historique attendu. Pour le journal de qualification #39668811238, la commande de contrôle devient :

```powershell
python tools/classify_windows_regression_log.py .\windows-39668811238.log --run-id 39668811238 --expected-tests 958 --json-output .\taxonomy.json --markdown-output .\taxonomy.md
if ($LASTEXITCODE -ne 0) { throw "Journal incomplet ou incohérent : revue manuelle obligatoire" }
```

Le journal doit être un export UTF-8 d'une seule invocation unittest. Si un export de job contient plusieurs invocations, il faut segmenter leurs sorties avant de les qualifier ; le parseur refuse volontairement de les agréger silencieusement.

## Régressions ajoutées

Le module `test_historical_failure_taxonomy_v6237.py` couvre les cas positifs, synthèses absentes ou contradictoires, invocations concaténées, `--expected-tests 958`, code de sortie CLI, comptes `FAILED` nuls et contenu terminal inattendu.

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


## Durcissement additionnel V6.238 — intégrité terminale

Deux faux positifs étaient encore possibles : une ligne arbitraire ajoutée après `OK` pouvait être ignorée, et un résumé `FAILED (failures=0, errors=0)` pouvait être marqué cohérent si aucun enregistrement n'était extrait. V6.238 rejette ces cas, expose `trailing_output_lines`, valide la grammaire des synthèses `OK` (seulement `skipped=N` et `expected failures=N` non dupliqués), rend la synthèse incomplète et conserve un code retour non nul. Les nouveaux tests couvrent ces deux contre-exemples ; ils s'exécutent dans les mêmes jobs de gouvernance et de qualification Windows natifs.
