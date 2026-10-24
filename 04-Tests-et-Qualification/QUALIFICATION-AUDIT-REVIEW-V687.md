# StorageScope — audit de cohérence des décisions (itération v6.87)

Auteur : Abdelhalim Talbi.

## Objectif
Interdire l'affichage d'un historique SQLite lorsque les décisions et les événements de la chaîne d'audit divergent, même si les empreintes de la table audit restent cohérentes.

## Invariants
- Chaque clé de décision doit correspondre à un unique événement d'audit ; une décision manquante, dupliquée ou divergente invalide le registre.
- Identité, décision, réviseur, date, justification et preuves JSON doivent correspondre.
- Les consultations passent par une connexion SQLite lecture seule et n'initialisent jamais un registre absent.
- La décision est unique par candidate_key, sans fusion automatique de données source.
- SHA-256 en chaîne assure la détection locale d'altérations non recalculées ; sans ancrage externe, un adversaire capable de réécrire toute la base peut recalculer les empreintes.

## Tests ajoutés
Exécuter à la racine du dépôt :
```bash
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_review_registry_integrity_v687.py' -v
python -m unittest discover -s 04-Tests-et-Qualification -p 'test_review_registry_v622.py' -v
```
Scénarios : historique ciblé, empreinte complète, lecture sans mutation, DB absente, altération de statut, altération de justification, seconde décision interdite et historique multi-candidats.

## Qualification Windows restante
Sur un runner Windows : construire le binaire, lancer l'interface Tkinter, sélectionner un rapprochement valide, enregistrer une décision, consulter le détail, filtrer l'historique et vérifier le blocage si la base est altérée. Conserver captures et journaux **réels** ; aucun résultat GUI interactif n'est revendiqué par les tests Python ci-dessus.

## Statut
Modification proposée sur branche dédiée. Ne pas déclarer de ZIP Windows « qualifié » tant que les contrôles natifs et l'ensemble des workflows requis ne sont pas PASS pour le commit final.
