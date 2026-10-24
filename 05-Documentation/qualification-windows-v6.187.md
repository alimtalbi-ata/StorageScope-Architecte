# StorageScope V6.187 — qualification Windows : correction SQLite et CI

**Auteur : Abdelhalim Talbi — 23 octobre 2026.**

## Preuves GitHub

- PR draft #4, branche `feature/storagescope-v6.186-wire-historical-suite-20261023` ; `main` reste inchangée.
- Windows CI #39668811238 (21/10) : **958 tests, 52 failures, 173 errors**.
- Windows CI #39919380864 (23/10) : **1 382 tests, 81 failures, 39 errors** pour la suite principale; **8 tests imbriqués, 6 errors**. Le build reste **FAIL** et PyInstaller/Inno Setup ne s'exécutent pas.
- CI gouvernance #39919380979 : PASS, sans valeur de qualification binaire.

## Causes racines et corrections

La correction V6.186 active réellement le runner isolé, conserve les fixtures historiques et écrit un rapport JSON FAIL/PASS. La nouvelle CI révèle que les imports/chemins ont beaucoup progressé, mais expose les défauts résiduels suivants :

1. **SQLite Windows / WinError 32** : plusieurs tests et `review_registry_v621.py` utilisaient `with sqlite3.connect(...)`, qui ne ferme pas la connexion à la sortie du bloc. Remplacement par `with closing(sqlite3.connect(...)) as db, db:` pour conserver commit/rollback et fermeture déterministe, y compris sur refus de décision dupliquée. Huit modules de tests historiques ont reçu la même correction de fixture.
2. **Assertions historiques figées** : versions 6.17/6.37/6.38 et chaînes de scripts dépassées. À corriger selon le contrat fonctionnel actuel, sans désactiver les tests.
3. **Encodage** : attentes littérales mal décodées (caractère U+FFFD) dans des tests historiques. Revoir le chargement UTF-8 avant d'ajuster les assertions.
4. **Publication/chemins** : certains tests utilisent d'anciennes positions de fichiers et ancres de scripts. Corriger les chemins de fixtures et la sémantique, sans supprimer les contrôles.
5. **Vrais bugs** : analyser individuellement les autres exceptions après réduction des erreurs SQLite.

## Tests nouveaux

- `test_review_registry_closure_v6187.py` : deux tests de vraie base SQLite avec suivi explicite des fermetures, commit d'audit et refus immuable.
- `test_windows_historical_gate_v6187.py` : quatre contrôles de liaison runner/CI, seuils 958+8 et JSON FAIL sur exception fatale.
- Tests locaux sur arborescence isolée Linux : **6/6 PASS**. Ces tests ne prouvent ni Windows ni les binaires.

## Conditions obligatoires avant publication

La suite Windows complète et les tests imbriqués doivent être verts. Puis PyInstaller, Inno Setup, installation/désinstallation, portable, manifestes SHA256, preuves réelles et captures UI doivent être vérifiés. Ne jamais fusionner automatiquement. Aucun installateur ni portable n'est présenté comme qualifié à ce stade.

**Captures réelles** : absentes. Schémas de principe : illustratifs et explicitement identifiés.
