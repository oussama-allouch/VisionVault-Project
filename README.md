# VisionVault — Intelligent Image Gallery & CBIR

> **Mini-projet 1** — Groupe G11 — AISD Master S3 — Multimedia Mining
>
> Méthode attribuée : **Re-weighting Type-1**
>
> Dataset : **GHIM-10K**

## 🏗️ Architecture

```
Frontend (React + TypeScript + Vite + Tailwind CSS)
  ↓ API REST (Axios → /api/v1)
Backend (Python Flask + Flask-RESTful)
  ↓ Services métiers
Module CBIR (OpenCV, scikit-image, scikit-learn, NumPy)
  ↓ Extraction descripteurs (93 dimensions)
Index de caractéristiques (NumPy .npz + joblib)
  ↓ Recherche par similarité (distance euclidienne pondérée)
Re-weighting Type-1 (Équation 5 — Renuka Devi SM, 2016)
  ↓ Résultats JSON
Visualisation frontend
```

## 📋 Descripteurs visuels (93 dimensions)

| Descripteur | Dimensions | Indices |
|---|---|---|
| Histogramme de couleur HSV | 48 | 0–47 |
| Moments de couleur (H, S, V) | 9 | 48–56 |
| Couleurs dominantes (K-Means) | 20 | 57–76 |
| GLCM (matrice de co-occurrence) | 6 | 77–82 |
| LBP (Local Binary Pattern) | 10 | 83–92 |

## 🚀 Installation et lancement (Windows)

### Prérequis

- **Python 3.11+** (ou Miniconda)
- **Node.js 18+** (avec npm)
- **Git**
- Dataset GHIM-10K téléchargé depuis [Kaggle](https://www.kaggle.com/datasets/mcpython/ghim-10k)

### 1. Cloner le projet

```bash
cd "votre-dossier"
git clone <url-du-repo> code
cd code
```

### 2. Préparer le dataset

Placer le dossier GHIM-10K dans `data/` :

```
code/
  data/
    GHIM-10K/
      aircraft/
      buildings/
      butterfly/
      ...
```

### 3. Backend (Python Flask)

```bash
cd backend

# Créer un environnement virtuel (recommandé)
python -m venv venv
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
copy .env.example .env
# Modifier .env si nécessaire

# Importer le dataset GHIM-10K
python scripts/import_dataset.py

# Construire l'index CBIR (peut prendre 10–30 minutes)
python scripts/build_index.py

# Lancer le serveur backend
python run.py
```

Le serveur démarre sur `http://localhost:5000`.

### 4. Frontend (React + Vite)

```bash
cd frontend

# Installer les dépendances
npm install

# Lancer le serveur de développement
npm run dev
```

Le frontend démarre sur `http://localhost:5173`.

### 5. Accéder à l'application

Ouvrir `http://localhost:5173` dans un navigateur.

**Compte de démonstration :** `demo@visionvault.com` / `demo2024`

## 📂 Structure du projet

```
code/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── config.py            # Configuration
│   │   ├── extensions.py        # Extensions Flask
│   │   ├── models/              # Modèles SQLAlchemy
│   │   ├── resources/           # API REST (Flask-RESTful)
│   │   ├── services/            # Logique métier
│   │   ├── cbir/                # Module CBIR
│   │   │   ├── color_features.py    # Histogramme, moments, couleurs dominantes
│   │   │   ├── glcm_features.py     # GLCM
│   │   │   ├── lbp_features.py      # LBP
│   │   │   ├── feature_extractor.py # Extraction unifiée (93 dim)
│   │   │   ├── normalization.py     # Min-Max normalization
│   │   │   ├── indexer.py           # Index de caractéristiques
│   │   │   ├── similarity.py        # Distance euclidienne pondérée
│   │   │   ├── reweighting_type1.py # Re-weighting Type-1 (Éq. 5)
│   │   │   ├── search_engine.py     # Moteur de recherche
│   │   │   ├── feedback.py          # Relevance feedback
│   │   │   └── evaluation.py        # Précision/Rappel@K
│   │   └── utils/               # Utilitaires
│   ├── scripts/
│   │   ├── import_dataset.py    # Import GHIM-10K
│   │   ├── build_index.py       # Construction de l'index
│   │   └── evaluate_cbir.py     # Évaluation CBIR
│   ├── requirements.txt
│   ├── run.py
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/               # Pages de l'application
│   │   ├── components/          # Composants réutilisables
│   │   ├── services/            # Services API (Axios)
│   │   ├── contexts/            # Contextes React
│   │   ├── types/               # Types TypeScript
│   │   └── utils/               # Utilitaires
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.app.json
├── data/                        # (non versionné)
│   ├── GHIM-10K/                # Dataset
│   ├── uploads/                 # Images téléversées
│   ├── thumbnails/              # Miniatures
│   └── index/                   # Index CBIR
└── README.md
```

## 🔬 Re-weighting Type-1 (Équation 5)

```
w_i^(k+1) = (ε + σ_Nr,i^k) / (ε + σ_rel,i^k)
```

- **ε = 0.0001** — constante de lissage
- **σ_Nr** — écart-type sur **tous** les résultats retournés
- **σ_rel** — écart-type sur les images **pertinentes** uniquement
- La requête est mise à jour : Q_new = moyenne des vecteurs des images pertinentes
- Distance : euclidienne pondérée (Éq. 3)

Référence : Renuka Devi SM, *"Reweighing Strategies for Relevance Feedback in CBIR"*, IJARCCE, 2016.

## 📊 Pages de l'application

| Page | Description |
|---|---|
| **Connexion** | Authentification JWT |
| **Tableau de bord** | Statistiques, graphiques, accès rapide |
| **Galerie** | Grille d'images, filtres, pagination, actions en lot |
| **Catégories** | Arbre hiérarchique, CRUD |
| **Upload** | Drag & drop, multi-fichiers, barre de progression |
| **Éditeur** | Recadrage, redimensionnement, rotation, miroir |
| **Descripteurs** | Visualisation des 5 types de descripteurs |
| **Recherche CBIR** | Recherche par similarité + Re-weighting Type-1 |
| **Analytiques** | Métriques, distribution, activité récente |

## ⚙️ Technologies

**Backend :** Python 3.11+, Flask, Flask-RESTful, Flask-SQLAlchemy, Flask-JWT-Extended, OpenCV, scikit-image, scikit-learn, NumPy, SciPy, Pillow

**Frontend :** React 19, TypeScript 7, Vite 8, Tailwind CSS 4, Recharts, Lucide React, Framer Motion, TanStack Query, React Router 7, React Hook Form, Zod

**Base de données :** SQLite (métadonnées + authentification)

**Index :** NumPy .npz + joblib (vecteurs de caractéristiques)

## 📝 Licence

Projet universitaire — AISD Master S3 — Multimedia Mining — 2024
