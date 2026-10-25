# StorageScope V6.232 — Quarantaine des identités CMDB liées aux observations invalides

**Auteur : Abdelhalim Talbi.** Évolution de sécurité métier ; tests synthétiques.

## Défaut et impact
Dans V6.231, un enregistrement mal formé (ex. `uuid` numérique ou `vendor` non textuel) était exclu des candidats. Pourtant, son `serial` valide pouvait correspondre à deux observations valides proposées en `REVIEW_REQUIRED` sans avertissement sur ce lien suspect.

## Contrat V6.232
1. Les observations invalides ne créent jamais de paires de candidats ni de preuve indépendante.
2. Leurs identifiants textuels valides `serial`, `wwn`, `uuid` servent uniquement de signaux de quarantaine.
3. Les liens respectent le même champ ; placeholders, valeurs absentes et non textuelles ne créent pas de lien.
4. La quarantaine se propage dans la composante connexe des candidats valides, sans bloquer les composantes indépendantes.
5. Rapport : `invalid_identity_origin_indices`, `invalid_identity_link_indices`, `propagated_quarantine_indices` et `QUARANTINE_LINKED_INVALID_RECORD`. Les conflits directs gardent leur priorité.
6. Aucune écriture CMDB ni fusion automatique ; SHA-256 exact des octets sources préservé. Limites : 10 000 observations et 50 000 paires.

## Qualification
Tests V6.232 et régressions V6.231/V6.230/V6.228/V6.209/V6.210. CI gouvernance Linux/Windows puis **CI Windows native** : suite historique, PyInstaller, exécutable figé, Inno Setup, installation/désinstallation, portable, SHA-256. CI gouvernance seule insuffisante pour qualifier Windows. Captures réelles, UX humaine et équipements physiques : non testés.

## Référentiels
Traçabilité (ISO/IEC/IEEE 42010), sécurité des identités (ISO/IEC 27001 et 27040), configurations (ITIL 4), dépendances (TOGAF et ArchiMate). Alignement conceptuel, aucune certification revendiquée.
