# StorageScope V6.173 — Windows historical CI

Auteur : Abdelhalim Talbi.

Le workflow Windows 39668811238 échoue : 958 tests, 52 échecs, 173 erreurs. Les causes comprennent les imports depuis 03-Sources, les chemins historiques, les assertions obsolètes et les connexions SQLite non fermées. Aucun binaire Windows qualifié n'a été produit. Les correctifs doivent être testés sur une branche dédiée sans désactiver la suite complète.
