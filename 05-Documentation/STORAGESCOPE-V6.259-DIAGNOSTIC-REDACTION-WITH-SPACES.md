# StorageScope V6.259 — diagnostic redaction when paths or secrets contain spaces

**Auteur : Abdelhalim Talbi**  
**Date : 27 octobre 2026**  
**Branche : feature/storagescope-v6.259-diagnostic-redaction-spaces-20261027**  
**Base : V6.258 — preuves diagnostiques bornées pour les anomalies historiques**

## Défaut corrigé

La revue du sanitiseur V6.258 a identifié une fuite résiduelle : les expressions des chemins absolus excluaient les espaces, et la redaction de token, password, secret ou api_key ne capturait que les valeurs sans espace. Un chemin Windows contenant « Program Files » ou un secret cité sur plusieurs mots pouvait donc laisser un suffixe visible dans le message d'exception publié.

## Correction

- Les racines absolues Windows et POSIX sont remplacées en incluant les composants et noms de fichiers contenant des espaces.
- La reconnaissance des valeurs sensibles comprend les chaînes entre guillemets simples ou doubles.
- Pour un chemin non cité, le sanitiseur privilégie la confidentialité : le reste de la ligne peut être masqué avec le chemin afin de ne pas laisser fuiter un suffixe ambigu.
- L'empreinte SHA-256 continue d'être calculée à partir du détail d'entrée normalisé du parseur ; elle ne remplace pas le contrôle d'accès et ne publie aucun détail brut.
- Aucun test existant n'est retiré ; la correction est ajoutée à la gouvernance Linux/Windows et à la qualification native Windows.

## Vérification

Commande ciblée à exécuter :

    python -m unittest discover -s 04-Tests-et-Qualification -p 'test_historical_diagnostic_redaction_v6259.py' -v

Les six cas synthétiques couvrent les chemins Windows/POSIX cités ou non cités avec espaces, les secrets multi-mots et la conservation de la redaction Bearer historique. La qualification Windows doit être jugée sur le HEAD exact de cette PR, y compris PyInstaller, Inno Setup, installation/désinstallation, portable et SHA-256.

## Limites

La donnée historique reste le run #39668811238 : 958 tests, 52 failures et 173 errors. La liaison des 225 symptômes à une cause racine prouvée, un commit et un test de non-régression reste NOT_ESTABLISHED. Cette PR améliore l'hygiène des preuves ; elle ne prétend pas résoudre ces 225 cas. Les fixtures sont synthétiques. Aucun test sur baie physique ni aucune certification ISO/IEC, TOGAF, ArchiMate ou ITIL n'est revendiqué.

La mesure s'aligne sur la minimisation de divulgation des journaux et la traçabilité de la preuve (orientation ISO/IEC 27001/27040 et ISO/IEC 42010), sans revendication de conformité certifiée.
