# StorageScope V6.242 — décodage strict des journaux historiques

**Auteur : Abdelhalim Talbi**  
**Branche : feature/storagescope-v6.242-strict-job-log-decoding-20261026**  
**Base : V6.241 — extraction bornée du journal Windows historique**

## Constat

Le job de gouvernance récupère le journal historique #39668811238 depuis GitHub Actions. Le script inline utilisait `decode("utf-8", errors="replace")` aussi bien pour le ZIP que pour le flux brut. Ce mode remplace silencieusement les octets invalides par U+FFFD, puis le classificateur opère sur un texte altéré. Les totaux 958 / 52 / 173 empêchent certaines incohérences, mais ne démontrent pas que le détail des traces est resté intact.

## Correction V6.242

Le nouveau module `tools/strict_job_log_payload.py` sélectionne un unique membre `.txt`/`.log` lorsqu'un ZIP est renvoyé, décode en UTF-8 strict avec prise en charge optionnelle du BOM, et refuse les séquences invalides ou les caractères NUL. Il ne modifie pas le parseur de synthèses ni ses exigences fail-closed.

Un manifeste JSON compagnon établit la taille et le SHA-256 du téléchargement et du journal extrait, indique le nom du membre ZIP, le décodeur, la longueur décodée et confirme que le mode de remplacement n'a pas été utilisé. Les empreintes décrivent les octets effectivement reçus ; elles ne constituent pas une signature cryptographique du fournisseur.

## Régressions

La suite `test_historical_job_log_decoding_v6242.py` comprend 8 cas : Unicode et séquences ANSI conservés, BOM UTF-8, UTF-8 invalide brut, journal valide et invalide dans un ZIP, archive à plusieurs candidats, entrée binaire avec NUL, et entrée vide / mauvais type.

Commande locale :
```bash
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_historical_job_log_decoding_v6242.py' -v
```

Le job Linux publie le manifeste de décodage dans le même artefact de taxonomie. Les tests ciblés sont intégrés aux jobs de gouvernance Linux et Windows ; le workflow Windows natif existant reste requis pour la qualification produit.

## Limites

Cette correction sécurise l'intégrité du diagnostic, pas les 225 anomalies historiques elles-mêmes. La taxonomie antérieure reste une heuristique : 13 enregistrements de faible confiance demandent toujours une revue des contrats build/source. Aucun contrôle n'est désactivé, aucune donnée CMDB ou infrastructure ne change. Pas de baie SAN/NAS physique, de capture GUI réelle ou de certification ISO revendiquée.
