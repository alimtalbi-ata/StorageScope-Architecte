# StorageScope Architecte — v6.106

Sources Python, tests métier et outils de fabrication Windows d'Abdelhalim Talbi.

Python 3.12 avec Tkinter et SQLite suffit au développement métier.
Depuis la racine du dépôt :

```sh
LOCALAPPDATA=/tmp/storagescope-dev python3 03-Sources/storagescope_windows.py --self-test
python3 scripts/run_tests.py --pattern test_architecture_decisions_v536.py
python3 scripts/run_tests.py --pattern test_qualification_freshness_v6100.py
python3 scripts/run_tests.py
```

Le lanceur copie les fichiers dans un dossier temporaire pour les tests historiques
qui attendent leurs sources à côté d'eux. Il ne modifie pas le dépôt et restitue
le code d'échec des tests. Sans filtre, il exécute toute la suite, y compris les
contrats Windows historiques qui ne correspondent plus à la version courante.
Un échec ne doit pas être interprété comme une qualification réussie.

Pour l'interface, lancer `python3 03-Sources/storagescope_windows.py` avec un
affichage disponible. Sur Windows : `02-Compilation-Windows/Construire-StorageScope.cmd`.
Les exécutables et l'installation doivent encore être qualifiés sur Windows.
