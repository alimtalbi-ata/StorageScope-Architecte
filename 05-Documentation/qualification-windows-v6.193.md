# StorageScope V6.193 — Installer rejection evidence / caller working directory

**Auteur : Abdelhalim Talbi**  
**Date : 23 octobre 2026**  
**Statut : correction publiée sur branche PR draft, qualification Windows complète en attente.**

## Preuve CI Windows et cause racine

Exécution GitHub Actions **39957669974**, sur le commit `9c80e8ee31bbd6177b40f454a0eae5acfdc84367` :

- Suite historique : **1 421 tests exécutés, PASS** (8 tests imbriqués PASS).
- PyInstaller et Inno Setup : compilation réalisée; installateur `StorageScope-Setup-v6.108.exe` généré.
- Vérification native : **PASS**.
- Qualification de rejet d'installation sur SQLite corrompu : le script annonce **PASS** et le rapport est écrit, mais le workflow échoue avec `Installer rejection evidence missing`.
- Tests d'installation/désinstallation nominale et portable : **non exécutés** après cet échec.
- **La CI Windows complète reste FAIL ; aucun binaire Windows qualifié.**

Le script `02-Compilation-Windows/qualifier-echec-installateur-windows.ps1` exécutait `Set-Location $PSScriptRoot`. En PowerShell, ce changement de répertoire persiste dans la session appelante. Le workflow, qui résout ensuite `02-Compilation-Windows/build-logs/installer-rejected-v6.108.json` relativement à la racine du dépôt, cherchait ainsi le fichier sous `02-Compilation-Windows/02-Compilation-Windows/build-logs/` au lieu de son emplacement réel.

## Correctif

- Suppression du changement de répertoire global dans le script ; les chemins internes sont déjà ancrés sur `$PSScriptRoot`.
- Aucun assouplissement du test de rejet : le refus, le code de sortie, l'absence d'installation, la conservation SHA-256 des données utilisateur et l'existence du journal restent exigés.
- Nouveau test `test_v6193_installer_gate_cwd.py` : contrats statiques des chemins et du workflow, plus reproduction PowerShell sur installateur volontairement inexistant (aucune installation réelle, aucune donnée utilisateur modifiée).

## Prochain jalon de qualification

Relancer la CI Windows depuis la PR draft. Exiger le passage du gate de rejet, puis des tests **réels** d'installation/désinstallation et du portable, du contrôle des binaires et de la consolidation de tous les rapports. Ne publier `StorageScope-Windows-QUALIFIED` qu'après PASS de la chaîne complète et validation des SHA-256.

**Traçabilité :** https://github.com/alimtalbi-ata/StorageScope-Architecte/actions/runs/39957669974 ; PR https://github.com/alimtalbi-ata/StorageScope-Architecte/pull/4.  
**Limites :** aucune capture UI native produite dans ce correctif ; ne pas substituer un exemple fictif à une preuve réelle.

## Validation native après correctif — CI #39958473015

**23 octobre 2026, 13:09 UTC — GitHub Actions : SUCCESS.** Ce verdict remplace le statut provisoire « en attente » ci-dessus pour le commit de qualification `587784d2d549c9fc0287f415e2d0659311cc9b83`.

- **1 424 tests principaux PASS ; 8 tests imbriqués PASS**. La ligne `FAILED (failures=1)` présente dans le journal concerne un **test synthétique volontairement défaillant** utilisé pour vérifier le runner ; la suite globale indique `HISTORICAL_SUITE_RESULT: PASS`.
- PyInstaller + Inno Setup : **PASS** ; release binaire `v6.108` (le correctif de qualification porte le numéro V6.193, distinct du numéro produit).
- Qualification native : **PASS**.
- Rejet de SQLite corrompu avec préservation des données : **PASS**, et lecture du JSON par le workflow : **PASS**.
- Installation/désinstallation, portable, contrôle de cinq artefacts, consolidation et gate de publication : **PASS**.
- Rapport `windows-release-qualification.json` : `status=PASS` avec `native=PASS`, `installer=PASS`, `portable=PASS`.
- Artefact GitHub `StorageScope-Windows-QUALIFIED` ID **12503118403**, archive ZIP SHA-256 **729d73775293431572cf2760bdb0db7c0cf99249a794bbccfe990283d7791ae2**.
- Empreinte de l'installateur `StorageScope-Setup-v6.108.exe` : **520e63b204c13042781726b9ef3ba77c099e5763c79c8b76214340d504a1067d**.
- Empreinte de `StorageScope.exe` : **41382ab3280e11c00b3630bf92069db680ecd085d829ad16b9912bc416539664**.

**Qualification acquise dans le périmètre automatisé Windows CI**, sans prétendre à une validation manuelle des écrans ni à des captures UI réelles. Aucune fusion sur `main` ; PR draft conservée.

Référence : https://github.com/alimtalbi-ata/StorageScope-Architecte/actions/runs/39958473015
