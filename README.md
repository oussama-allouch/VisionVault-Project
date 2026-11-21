# VisionVault

Mini-projet 1 du groupe G11, Master Intelligence Artificielle et Sciences des Données (IASD), S3, année 2026–2027. Faculté des Sciences et Techniques de Tanger, Université Abdelmalek Essaâdi. Encadrant M'hamed AIT KBIR.

VisionVault permet de gérer une galerie authentifiée, d’organiser les images par catégories, de créer des dérivés et de rechercher des images similaires. React et Vite consomment une API Flask-RESTful. SQLite stocke les métadonnées. L’index NumPy et les fichiers images restent sur disque.

## Prérequis

Python 3.11 ou 3.12 avec `venv` et pip, Node.js 22.12+ ou 24 LTS avec npm, Git, environ 2 Gio libres pour le corpus et les fichiers générés. Sur Debian ou Ubuntu, installer le paquet `python3-venv` adapté au Python du système. Les commandes Linux ont été exécutées avec Python 3.12.3, Node 24.22.3 et npm 11.9.0. Les variantes PowerShell sont prévues pour Windows.

## Acquisition de GHIM-10K

Décompresser le [jeu demandé sur Kaggle](https://www.kaggle.com/datasets/mcpython/ghim-10k), si disponible, et placer les images dans `data/GHIM-10K`, un sous-dossier par classe. Le protocole de validation utilise la [copie publiée par le collecteur](https://github.com/liuguanghai009/datasets/tree/09f0e4378f7a5ec78fe6be358680413fa1b9d9d8/GHIM-10K). Ce dépôt contient directement des fichiers `classe_numéro.jpg`, avec des classes de 0 à 19. Le chargeur accepte les deux structures.

Depuis la racine de VisionVault, pour obtenir la copie documentée dans un répertoire voisin :

```sh
git clone --filter=blob:none --sparse https://github.com/liuguanghai009/datasets ../ghim-publisher
git -C ../ghim-publisher checkout 09f0e4378f7a5ec78fe6be358680413fa1b9d9d8
git -C ../ghim-publisher sparse-checkout set GHIM-10K
```

Définir ensuite `DATASET_PATH=../../ghim-publisher/GHIM-10K` dans `backend/.env`, ou indiquer un chemin absolu. Tous les chemins relatifs de ce fichier partent de `backend/`. Conserver le dossier du corpus à l’emplacement configuré après l’import.

## Installer le backend

**Linux**, depuis la racine du projet :

```sh
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

**Windows PowerShell**, depuis la racine du projet :

```powershell
Set-Location backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Dans `backend/.env`, choisir une adresse et un mot de passe privés pour `DEMO_EMAIL` et `DEMO_PASSWORD`. Ils créent un administrateur local au premier démarrage. Les valeurs vides désactivent l’amorçage de ce compte. Les clés peuvent être laissées vides pour une session locale avec clés aléatoires ou définies à l’aide de valeurs aléatoires longues pour conserver les connexions entre redémarrages. Une modification du mot de passe de démonstration ne réinitialise pas un compte SQLite existant.

Dans `backend/`, avec le Python de l’environnement virtuel :

```sh
python scripts/import_dataset.py
python scripts/build_index.py
python run.py
```

Sous PowerShell, remplacer chaque commande `python` par `.\.venv\Scripts\python.exe` si l’environnement n’est pas activé. Les tables SQLite sont créées automatiquement. Les scripts affichent les comptes, doublons SHA-256, formats réels, erreurs et vérification du rechargement. Pour un ancien index, lancer `build_index.py` à nouveau. Le démarrage s’effectue sur `127.0.0.1:5000`.

## Installer le frontend et ouvrir la galerie

Dans un second terminal, à la racine du projet :

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Ouvrir `http://127.0.0.1:5173` et utiliser le compte local configuré. Le proxy Vite transmet `/api/v1` au backend. La galerie est commune aux utilisateurs authentifiés. Les sessions de recherche et leurs analytiques sont propres au compte.

## Validation et expérience

Dans `backend/` :

```sh
python -m pytest -q -ra
python scripts/evaluate_cbir.py --output ../results --seed 20261121 --per-category 5 --dataset-revision 09f0e4378f7a5ec78fe6be358680413fa1b9d9d8
```

Les tests photo utilisent `DATASET_PATH`. Le test navigateur est opt-in sur une **copie jetable** et exige les deux serveurs, le jeu complet importé, un compte de test privé et Chromium. Installer Chromium avec `python -m playwright install chromium` ou fournir `VV_BROWSER` vers un Chromium compatible. Exporter `VV_E2E_URL=http://127.0.0.1:5173`, `DATASET_PATH`, `DEMO_EMAIL`, `DEMO_PASSWORD` et, pour conserver les PNG, `VV_EVIDENCE_DIR` et `VV_CAPTURE_DATE`. Exécuter `python -m pytest -q tests/test_browser_e2e.py`. Le test crée et supprime des images et catégories sur cette instance.

Dans `frontend/`, exécuter `npm run build` pour TypeScript et Vite, puis `npm run lint`.

L’évaluation nécessite une base dédiée au seul corpus GHIM-10K et utilise cinq requêtes par classe, cinq valeurs de K et cinq tours de retour simulé. Le protocole des livrables précise les mesures et le traitement des classements reconduits.

## Méthode et références

Le vecteur contient 48 composantes d’histogrammes HSV, 9 moments HSV, 20 composantes de couleurs dominantes, 6 propriétés GLCM et 10 fréquences LBP. Le classement initial emploie des poids uniformes. Re-weighting Type-1 recalcule les poids à partir de tous les résultats et des seuls positifs, puis place la requête au centroïde des positifs.

- Renuka Devi SM, « Reweighing Strategies for Relevance Feedback in CBIR », IJARCCE 5(11), novembre 2016, p. 549–555. [Article dans le dépôt](docs/references/Reweighing%20Strategies%20for%20Relevance%20%20Feedback%20in%20CBIR.pdf) · [DOI](https://doi.org/10.17148/IJARCCE.2016.511118).
- [Algorithmes](docs/algorithms.md) · [Architecture](docs/architecture.md) · [API](docs/api.md) · [Guide utilisateur](docs/user-guide.md) · [Guide des données](docs/dataset-guide.md).

## Dépannage

Vérifier `http://127.0.0.1:5000/api/v1/index/health` si Vite ne joint pas l’API. Un résultat d’import vide indique généralement un dossier enveloppe de trop. Après déplacement du corpus, réimporter dans une base dédiée ou restaurer le chemin configuré. Pour le test local, respecter 16 Mio par requête de téléversement, 24 mégapixels par image et 100 fichiers par lot.
