# StorageScope V6.255 — détection des seuils de capacité déjà atteints

**Auteur : Abdelhalim Talbi**  
**Date : 26 octobre 2026**  
**Périmètre : moteur de prévision SAN/NAS V6.254, correction métier V6.255**

## Cause racine

La branche de prévision V6.254 étiquetait toute série dont la dernière utilisation dépassait le seuil d'avertissement comme `CURRENT_THRESHOLD_ALREADY_REACHED`, mais ajoutait ensuite le résultat sans créer de finding. De plus, le raccourci `NON_GROWING` précédait ce contrôle : une baie déjà au seuil mais dont la consommation diminuait pouvait être classée `NON_GROWING` sans risque courant. Dans les deux cas, le rapport pouvait omettre un dépassement de capacité qui existe maintenant.

## Correction

- Évaluer le seuil de criticité puis celui d'avertissement avant la branche `NON_GROWING`.
- Émettre `CAPACITY_CRITICAL_THRESHOLD_CURRENT` au niveau **HIGH** lorsque l'utilisation courante est supérieure ou égale au seuil critique.
- Émettre `CAPACITY_WARNING_THRESHOLD_CURRENT` au niveau **MEDIUM** lorsque le seuil d'avertissement est atteint, sans encore atteindre le seuil critique.
- Pour un avertissement courant avec une tendance positive, conserver l'estimation du délai jusqu'au seuil critique. Ne pas extrapoler ce délai lorsque la pente est nulle ou négative.
- Faire compter ces findings dans l'évaluation : le code de sortie du CLI devient `1` pour un risque courant détecté. Le rapport reste déterministe et en lecture seule ; `automatic_changes` reste à zéro.

Les codes `CURRENT_WARNING_THRESHOLD_REACHED` et `CURRENT_CRITICAL_THRESHOLD_REACHED` distinguent explicitement un seuil déjà atteint d'un franchissement seulement prévu.

## Tests de non-régression

`test_storage_capacity_current_threshold_v6255.py` couvre quatre cas synthétiques : seuil d'avertissement déjà dépassé avec hausse de tendance et échéance critique estimée ; seuil critique atteint sur une tendance décroissante ; égalité exacte au seuil d'avertissement malgré une tendance décroissante ; utilisation à 100 %. Ces cas sont raccordés à la CI de gouvernance et à la qualification native Windows.

## Limites et gouvernance

Le moteur n'interroge pas les baies et n'écrit pas la CMDB. Les échantillons sont synthétiques ; les étiquettes source ne sont pas une attestation indépendante. La régression linéaire reste un indicateur de planification, pas une garantie. Cette évolution alimente les pratiques de gestion de capacité ITIL 4 et l'analyse de risques ; elle ne constitue aucune certification TOGAF, ArchiMate, ISO/IEC/IEEE 42010, ISO 27001 ou ISO 27040.

**Statut de qualification :** le test cible sera qualifié sur le nouveau HEAD par les workflows GitHub. La qualification native des binaires Windows (PyInstaller, Inno Setup, installation/désinstallation, portable, empreintes et artefacts) reste une preuve distincte et doit réussir sur ce HEAD exact avant tout statut Windows qualifié.
