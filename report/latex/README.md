# Rapport LaTeX de VisionVault G11

Compiler la racine de ce dossier avec LuaLaTeX et Biber. Toutes les figures nécessaires sont incluses.

- En local, avec une installation TeX Live comprenant LuaLaTeX, latexmk, biblatex/Biber et les paquets référencés dans `preamble.tex`, lancer `latexmk -lualatex main.tex`. Le PDF produit est `main.pdf`.
- Dans Overleaf, importer le ZIP source, choisir `main.tex` comme document principal et sélectionner **LuaLaTeX** dans les paramètres de compilation. `latexmk` gère les passes et la bibliographie. La compilation utilise les figures et la bibliographie livrées dans l'archive.
- Modifier les informations d'identification dans `metadata.tex`, puis compiler à nouveau.

## Provenance des figures

Les PNG sont des cadrages des captures Playwright prises sur l'application VisionVault réellement exécutée le 21 novembre 2026. Les originaux de la campagne restent dans les archives internes du groupe.

| Fichier LaTeX | Capture originale |
|---|---|
| `connexion.png`, `fiche-image.png` | 01 Connexion, 06 Détail |
| `galerie-lot.png`, `televersement.png`, `categories.png` | 07 Sélection ZIP, 05 Téléversement, 04 Catégories |
| `selection-crop.png` | 08 Recadrage |
| `histogramme-hsv.png`, `moments-hsv.png`, `dominantes.png` | 11 Histogramme HSV, 12 Moments, 13 Couleurs dominantes |
| `glcm.png`, `lbp.png` | 14 GLCM, 15 LBP |
| `recherche-simple.png`, `retour-pertinence.png` | 17 Recherche initiale, 21 Poids |

`transformations.jpg` assemble l'original GHIM-10K `0_1.jpg` et les deux dérivés enregistrés et téléchargés pendant ce parcours. `topk-avant.jpg` et `topk-apres.jpg` reproduisent les premiers rangs réellement obtenus pour la requête GHIM-10K `7_3690.jpg` à K = 25. Les deux vues sont extraites des planches produites d'après les journaux des tours 0 et 5. `precision-k25.tsv` reprend les six moyennes de précision à K = 25, contrôlées dans la synthèse CSV et JSON, converties en pourcentage. Le graphique est rendu en vectoriel par PGFPlots au moment de la compilation. Le diagramme d'architecture est rendu par TikZ.

Les images de la collection sont attribuées à la [distribution utilisée](https://github.com/liuguanghai009/datasets/tree/09f0e4378f7a5ec78fe6be358680413fa1b9d9d8/GHIM-10K). Cette version ne déclare aucune licence de redistribution des photographies.
