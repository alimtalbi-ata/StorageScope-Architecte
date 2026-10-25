# StorageScope V6.234 — Fermeture déterministe des fixtures SQLite historiques

**Auteur : Abdelhalim Talbi**  
**Périmètre : tests de pagination V6.466 et curseurs V6.467**  
**Statut : correctif publié sur branche dédiée ; qualification CI de ce commit requise.**

## Diagnostic reproduit

Le lanceur historique V6.233 exécutait 1 738 tests (un test ignoré) et les 8 tests imbriqués ; la suite se terminait avec succès, mais émettait huit avertissements de ressources SQLite. Le journal attribuait ces avertissements à des connexions non fermées, sans faire échouer le code retour du processus.

La recherche du cycle de vie a isolé deux fixtures :
- `test_v466.py / SqlPaginationTests.setUp` créait `Governance(':memory:')` pour chacun de ses quatre tests et n'appelait pas `Governance.close()`.
- `test_v467.py / CursorTests.setUp` faisait de même pour quatre autres tests.

Le gestionnaire de contexte standard de `sqlite3.Connection` valide ou annule la transaction ; il ne ferme pas le handle. Les huit avertissements concordent donc avec les huit instances de fixtures. Le module de portfolio utilise `g.db` prêté par `Governance` et n'est pas propriétaire de cette connexion : aucun code métier de production n'a été modifié pour masquer l'avertissement.

## Correction

Les deux fixtures enregistrent maintenant `self.g.close` avec `unittest.TestCase.addCleanup`. Le nettoyage est exécuté après chaque méthode, y compris quand une assertion échoue. Aucun test n'a été supprimé ou désactivé ; aucun contrat fonctionnel n'a été modifié.

Les workflows Linux, Windows de gouvernance et Windows natif exécutent les deux fichiers avec les avertissements de ressource activés, une trace d'allocation sur Windows et une inspection explicite des journaux. Cette inspection est nécessaire car un `ResourceWarning` produit par un destructeur peut être affiché comme « Exception ignored in » tout en laissant le processus terminer avec le code zéro.

## Vérifications locales effectuées après correction

Commandes appliquées aux deux fichiers, séparément :

```sh
PYTHONPATH=03-Sources python -W error::ResourceWarning -m unittest discover -s 04-Tests-et-Qualification -p 'test_v466.py' -v
PYTHONPATH=03-Sources python -W error::ResourceWarning -m unittest discover -s 04-Tests-et-Qualification -p 'test_v467.py' -v
```

Résultat observé : **4/4 PASS** pour V6.466 et **4/4 PASS** pour V6.467 ; aucune ligne `ResourceWarning`, `unclosed database` ou `Exception ignored in:` dans les journaux capturés.

La suite historique complète n'a pas été recomptée après cette modification locale ; la qualification exacte-head est laissée aux workflows déclenchés par cette PR. La réussite d'un test ciblé ne vaut pas qualification Windows complète.

## Contrat de livraison et limites

- Aucun changement des données utilisateur ou des bases existantes.
- Aucun accès à un équipement SAN/NAS réel ; les essais restent synthétiques.
- Pas de captures d'interface réelles ni de qualification UX humaine dans ce cycle.
- La version applicative embarquée reste `6.108` ; V6.234 désigne le correctif de cette branche.
- La qualification finale exige les jobs Windows natifs, PyInstaller, Inno Setup, rejet installateur, installation/désinstallation, portable et vérification SHA-256 sur le HEAD exact.

Cette correction relève de la maintenabilité et de la reproductibilité des tests (ITIL 4 / assurance qualité), tout en renforçant la documentation des cycles de vie et la fiabilité des contrôles de données (ISO/IEC/IEEE 42010, ISO/IEC 27001/27040).
