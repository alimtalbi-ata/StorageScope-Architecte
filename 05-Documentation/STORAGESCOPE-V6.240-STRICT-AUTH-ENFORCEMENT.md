# StorageScope V6.240 — configuration fail-closed de l’authentification d’observations

**Auteur : Abdelhalim Talbi**  
**Branche :** `feature/storagescope-v6.240-auth-enforcement-strict-20261025`  
**Base :** V6.239, commit `6c291a39f21c7903f9f1dff0ee96227c315b45f8`  
**Périmètre :** politique d’authentification HMAC SAN/NAS, lecture seule ; données de qualification synthétiques.

## Défaut reproduit par inspection du code

`load_auth_policy` vérifiait que `STORAGESCOPE_REQUIRE_OBSERVATION_AUTH_V2` valait `0` ou `1` uniquement lorsque la politique était absente. Lorsqu’un snapshot contenait déjà une politique, une valeur invalide telle que `true`, `2` ou une chaîne vide n’était pas rejetée. La valeur pouvait donc masquer une erreur de configuration opérateur au lieu d’échouer immédiatement.

## Correction

- Lire et valider les deux commutateurs avant toute branche liée au contenu du snapshot.
- Seules les valeurs textuelles exactes `0` et `1` sont acceptées.
- Une exigence V2 continue de rejeter une politique V1 et accepte une politique V2 correctement structurée.
- Aucun secret n’est journalisé ; aucun appel réseau, changement d’infrastructure ou écritures CMDB ne sont ajoutés.
- La compatibilité V1 reste explicite lorsque l’opérateur désactive le mode V2.

## Tests de régression

Le fichier `04-Tests-et-Qualification/test_storage_auth_policy_enforcement_v6240.py` couvre :
1. valeurs V2 invalides avec une politique présente ;
2. valeurs V2 invalides sans politique ;
3. compatibilité V1 et exigence stricte V2 ;
4. validation du commutateur principal.

Commande ciblée :

```powershell
python -m unittest discover -s 04-Tests-et-Qualification -p test_storage_auth_policy_enforcement_v6240.py -v
```

La qualification finale dépend des workflows sur le HEAD exact ; ce document ne préjuge pas de leur résultat.

## Traçabilité d’architecture et limites

- **ISO 27001 / 27040 :** échec fermé sur configuration de sécurité ambiguë ; intégrité et contrôle des observations.
- **ISO/IEC/IEEE 42010 / ArchiMate :** décision et comportement du composant documentés explicitement.
- **ITIL 4 :** configuration d’un contrôle exploitable et diagnostiquer un écart sans transformer une donnée non vérifiée en preuve positive.
- **TOGAF :** la règle d’application reste dans la frontière du composant d’authentification.

HMAC atteste la possession d’une clé partagée et l’intégrité du payload ; elle n’établit pas à elle seule l’identité indépendante du collecteur, l’horloge de collecte ou la validation d’équipements physiques.
