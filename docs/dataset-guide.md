# Corpus GHIM-10K

Le lien du sujet est [mcpython/ghim-10k](https://www.kaggle.com/datasets/mcpython/ghim-10k). Lors de la validation en local, le téléchargement a répondu HTTP 404. Le benchmark a utilisé [la distribution du collecteur](https://github.com/liuguanghai009/datasets/tree/09f0e4378f7a5ec78fe6be358680413fa1b9d9d8/GHIM-10K), révision `09f0e4378f7a5ec78fe6be358680413fa1b9d9d8`. Voir [README](../README.md) pour son acquisition.

Le dossier plat encode la classe par son préfixe numérique (ex. `0_1.jpg`). Le nom d’une classe affichée est alors `Classe 00` à `Classe 19`. Un dossier à un niveau de sous-dossiers, un par classe, est également accepté. L’extension peut masquer le format réel. L’import valide le décodage, inventorie le format, calcule SHA-256, déduplique les fichiers identiques et prépare les miniatures. L’original reste dans le dossier de données, avec son chemin enregistré en SQLite.

L’import CLI fournit les comptes observés et les fichiers écartés. `build_index.py` construit ensuite un fichier `features.npz` avec les descripteurs bruts, les IDs et les coefficients Min-Max, puis vérifie son rechargement et la correspondance avec SQLite. Toute erreur de décodage ou d’extraction doit être expliquée avant l’évaluation. Les données, miniatures, index et bases SQLite sont exclus des archives de code.
