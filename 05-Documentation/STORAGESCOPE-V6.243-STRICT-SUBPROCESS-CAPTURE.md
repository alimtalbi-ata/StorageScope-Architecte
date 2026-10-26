# StorageScope V6.243 — capture stricte des sorties de sous-processus

**Auteur : Abdelhalim Talbi**  
**Branche : feature/storagescope-v6.243-strict-subprocess-capture-20261026**  
**Base de travail : V6.242 — décodage strict du journal GitHub Actions**

## Défaut repris

V6.242 rend strict le décodage des journaux téléchargés via GitHub Actions, mais le runner scripts/run_historical_windows_suite.py capturait encore les sorties unittest avec encoding="utf-8", errors="replace". En présence d'octets invalides, le runner remplaçait l'information avant d'analyser la synthèse, et le fichier de preuve était réencodé depuis le texte déjà altéré.

## Correction V6.243

- subprocess.run capture maintenant des octets (stdout=PIPE, stderr=STDOUT) sans mode texte.
- La sortie brute est écrite atomiquement dans le journal d'évidence avant tout décodage ; son SHA-256 et sa taille décrivent les octets exacts capturés.
- tools/strict_subprocess_output.py impose UTF-8 strict et rejette les octets invalides et les NUL. Il ne tente aucune autodétection d'encodage, conversion cp1252 ou substitution.
- Si le décodage échoue, la suite devient FAIL, la synthèse est marquée UNKNOWN et le journal n'est pas soumis au parseur unittest. Le rapport conserve l'erreur, l'offset et le hash ; il ne transforme pas le défaut en simple échec de test classifiable.
- Pour les sorties valides, la provenance du décodage (algorithme, taille, SHA-256 et absence de décodage avec perte) est jointe au rapport JSON.

## Vérifications

Tests ajoutés dans 04-Tests-et-Qualification/test_historical_subprocess_output_v6243.py :

1. Conservation exacte d'une sortie UTF-8 multilingue et rapprochement du hash.
2. Rejet d'octets UTF-8 invalides avec offset/hash.
3. Rejet d'une sortie cp1252 non UTF-8 sans heuristique de réparation.
4. Rejet d'un contenu contenant NUL.
5. Conservation d'une sortie vide pour que la porte de synthèse existante la refuse.
6. Test d'intégration du runner : sortie invalide => FAIL, octets bruts préservés et hash concordant.
7. Test d'intégration : marqueur terminal de l'invocation attendu en UTF-8 => PASS.

Commande ciblée :

    python -m unittest discover -s 04-Tests-et-Qualification -p 'test_historical_subprocess_output_v6243.py' -v

La suite historique native Windows reste obligatoire ; une réussite des tests ciblés ne qualifie pas le binaire Windows. Les contrôles, minima, détection des erreurs et publication conditionnelle ne sont pas diminués.

## Limites et sécurité

- Les erreurs d'encodage sont maintenant visibles et provoquent un refus fermé ; si un sous-processus non Python émet réellement du cp1252, il faut définir explicitement son contrat de sortie à la source plutôt que d'inférer l'encodage.
- La conservation du journal brut est une preuve d'octets reçus, pas une signature du fournisseur.
- Aucun test sur baie SAN/NAS physique, aucun changement CMDB, aucune capture UI réelle ni certification ISO ne sont revendiqués.
- main reste intacte et la PR est laissée en draft.

## Référentiels d'architecture et de contrôle

La traçabilité des octets et des décisions de qualification contribue à la gouvernance des preuves et à la gestion des risques (ITIL 4, ISO 27001/27040) ; ce correctif est un contrôle technique ciblé, pas une déclaration de conformité. Les vues d'architecture peuvent être reliées aux décisions de cycle de vie et de qualification sous ISO/IEC/IEEE 42010, TOGAF et ArchiMate.
