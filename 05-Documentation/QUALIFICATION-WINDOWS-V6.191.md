# StorageScope — qualification Windows V6.191 (23 octobre 2026)

**Auteur : Abdelhalim Talbi**  
**État : travaux en cours, aucune qualification Windows délivrée.**  
**Branche :** `feature/storagescope-v6.186-wire-historical-suite-20261023` ; PR draft #4 ; `main` préservée.

## Évidence de départ

- Run Windows `39933148185` : 1 399 tests principaux, **59 échecs, 0 erreur** ; huit tests imbriqués réussis. Le build natif s'arrête avant PyInstaller.
- La suite plus ancienne `39668811238` (958 tests, 52 échecs et 173 erreurs) n'est pas directement comparable à la suite élargie.
- Les journaux montrent des tests historiques demandant littéralement `6.17`, `6.33`, `6.41`, `6.87` et `6.88`, alors que le manifeste actuel du checkout indique `6.108`. C'est une cause identifiée pour **au moins sept assertions**, pas pour les 59 échecs.

## Correction de cette itération

Les tests `test_binary_v687.py`, `test_binary_v688.py`, `test_release_contract_v641.py`, `test_release_package_v615.py` et `test_release_v633.py` gardent leurs contrôles historiques : seuil minimal de version, présence des garde-fous de publication, absence de faux exécutables, vérification de staging et d'installation.

Les comparaisons figées avec l'ancienne version sont remplacées par des assertions de non-régression et de **cohérence stricte de la version courante**. Le contrôle indépendant `test_release_version_consistency_v6191.py` ajoute dix scénarios, dont des refus explicites de manifeste invalide, version rétrogradée, doublons, divergence application/installateur, build codé en dur et fichier manquant. Les tests ne sont ni désactivés ni exclus.

## Critères de qualification non négociables

1. Exécuter sur Windows les **958 tests minimum** du runner historique, plus **8 imbriqués minimum**, et vérifier le rapport JSON ainsi que les journaux complets.
2. Corriger toutes les erreurs et assertions restantes ; aucune réussite partielle n'autorise un build publié.
3. Produire les exécutables par PyInstaller puis l'installateur par Inno Setup ; vérifier l'exécution autonome, la version, les sorties, la protection des données, les empreintes SHA-256 et les refus d'installation dangereux.
4. Tester installation, désinstallation et archive portable sur un runner Windows éphémère, avec preuves horodatées. Une CI gouvernance verte n'est pas une qualification native.
5. Conserver `main` inchangée et ne jamais fusionner la PR automatiquement.

## Prochaine analyse

Récupérer le nouveau journal Windows du dernier commit, regrouper les échecs par fichier et contrat, traiter d'abord les assertions figées restantes et les divergences de version, puis les vrais défauts applicatifs. Éviter les modifications de tests qui affaiblissent la sémantique métier.

## Limites et provenance

Les tests exécutés sur le runner Windows sont la seule preuve de qualification Windows. Les fixtures synthétiques des dix nouveaux scénarios ne sont **pas** des captures réelles d'interface. Aucun installateur, binaire portable ni capture réelle n'est fourni à cette étape.
