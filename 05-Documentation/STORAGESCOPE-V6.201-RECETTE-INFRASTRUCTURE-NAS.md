# StorageScope — Recette Infrastructure NAS hors ligne (branche V6.201)

**Auteur : Abdelhalim Talbi**  
**Statut : documentation de recette, non certification exhaustive**  
**Application livrée :** version indiquée dans `07-Manifestes/VERSION` (ne pas confondre avec le numéro de branche V6.201).

## Objectif et limites

Le parcours Infrastructure importe un **fichier JSON local fourni par l'opérateur** ; il ne se connecte ni aux baies, ni à la CMDB et ne modifie aucun équipement. Les adaptateurs acceptent explicitement `netapp_ontap`, `dell_powerscale` et `pure_flashblade`. L'interface affiche les équipements et leurs partages NFS/SMB, puis exporte le tableau en CSV.

Les snapshots sont des **preuves déclaratives hors ligne** : leur présence ne prouve pas la connectivité, la fraîcheur des données ou les droits effectifs sur les partages.

## Procédure de recette Windows

1. Installer `StorageScope-Setup-*.exe` ou extraire `StorageScope-Portable-*.zip` depuis `01-Application-Windows`. Vérifier les empreintes SHA-256 publiées avec la livraison.
2. Démarrer StorageScope et ouvrir **Infrastructure**. Vérifier le tableau initial vide et le message invitant à choisir un snapshot.
3. Cliquer **Exporter le tableau en CSV** avant tout import : l'application doit prévenir qu'aucun inventaire n'est chargé et ne doit créer aucun fichier.
4. Cliquer **Importer un snapshot** puis annuler : l'inventaire doit rester inchangé.
5. Importer un JSON conforme à `storagescope.vendor-snapshot.v1`. Vérifier fournisseur, nom, identifiant, capacité utilisée/totale et nombre de partages.
6. Sélectionner un équipement : les détails NFS/SMB correspondants doivent apparaître dans la zone inférieure.
7. Exporter le tableau en CSV vers un chemin neuf : ouvrir le fichier et vérifier les valeurs et l'encodage. Répéter l'export en annulant la boîte de dialogue : aucun fichier ne doit être créé et aucune erreur ne doit être affichée.
8. Réimporter un JSON invalide : une erreur doit apparaître et **l'inventaire précédent doit être conservé**.
9. Réexporter vers le CSV existant : l'opération doit être refusée et le fichier initial préservé.
10. Répéter sur les trois formats fournisseur et sur les versions installée et portable. Pour chaque fournisseur, inclure dans le même système un partage NFS et un partage SMB ; vérifier que les deux protocoles apparaissent dans les détails et qu'aucune modification d'équipement ou de CMDB n'est effectuée.

## Gestion des données partielles

Pour chacun des trois fournisseurs, répéter l'import avec un partage dont `quota_bytes` vaut `-1`, puis avec un partage dont `protocol` vaut `FTP` (protocole non pris en charge), et enfin avec `used_bytes` supérieur à `quota_bytes` (par exemple 21 GiB utilisés pour 20 GiB de quota). Résultat attendu : le système NAS valide reste visible, le partage incorrect est rejeté, le rapport signale une observation `INCOMPLETE` et aucune modification automatique n'est exécutée. Le rejet d'un partage ne doit jamais être présenté comme un inventaire complet. Tester également un **système** déclarant 101 GiB utilisés pour 100 GiB de capacité totale : le système et tous ses partages doivent être écartés, avec un rejet « inconsistent capacity » et une évaluation `INCOMPLETE`.

## Exemple synthétique (fictif — non issu d'une baie réelle)

```json
{
  "schema": "storagescope.vendor-snapshot.v1",
  "vendor": "netapp_ontap",
  "source_ref": "qualification-lab",
  "collected_at": "2026-10-24T10:00:00Z",
  "systems": [{
    "serial_number": "LAB-NAS-001",
    "cluster_name": "nas-lab",
    "capacity_used_bytes": 1073741824,
    "capacity_total_bytes": 10737418240,
    "volumes": [{
      "uuid": "vol-lab",
      "protocol": "NFS",
      "used_bytes": 1073741824,
      "quota_bytes": 2147483648
    }]
  }]
}
```

**Résultat attendu :** un équipement NetApp et un partage NFS ; capacité utilisée de 1 GiB, capacité totale de 10 GiB. Cette illustration ne constitue **pas** une capture réelle.

## Preuves automatiques et limites

- `04-Tests-et-Qualification/test_windows_infrastructure_gui_smoke_v6201.py` instancie les véritables widgets Tkinter et invoque les boutons d'import et d'export. Les boîtes de dialogue de fichiers sont simulées pour la reproductibilité.
- La qualification Windows inclut également la compilation, les contrôles de packaging et des essais installateur/portable. Consulter les fichiers JSON de qualification inclus dans le ZIP.
- Ces tests ne remplacent pas une recette manuelle avec de véritables équipements, de gros inventaires, les réglages DPI, l'accessibilité clavier et les systèmes Windows cibles.

## Critères de rejet

Refuser une livraison si l'application ne démarre pas, si le tableau ne se remplit pas après un import valide, si la sélection n'affiche pas les partages, si un JSON malformé détruit l'inventaire précédent, si un export écrase un fichier existant ou si le ZIP ne contient pas les sources exactes et les preuves de qualification.
