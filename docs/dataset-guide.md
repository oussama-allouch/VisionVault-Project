# VisionVault — Guide du Dataset GHIM-10K

## Table des matières

1. [Description du dataset](#1-description-du-dataset)
2. [Catégories](#2-catégories)
3. [Téléchargement](#3-téléchargement)
4. [Structure des répertoires](#4-structure-des-répertoires)
5. [Import dans VisionVault](#5-import-dans-visionvault)
6. [Indexation](#6-indexation)
7. [Remarques](#7-remarques)

---

## 1. Description du dataset

**GHIM-10K** (Generic Hierarchical Image dataset — 10,000 images) est un dataset d'images naturelles conçu pour l'évaluation des systèmes de recherche d'images par le contenu (CBIR).

| Propriété | Valeur |
|-----------|--------|
| Nombre total d'images | **10 000** |
| Nombre de catégories | **20** |
| Images par catégorie | **500** |
| Format | JPEG (.jpg) |
| Résolution | Variable |
| Source | Kaggle |

---

## 2. Catégories

Le dataset comprend **20 catégories** thématiques, chacune contenant exactement **500 images** :

| # | Catégorie | Nom du dossier | Images |
|---|-----------|----------------|--------|
| 1 | Avions | `aircraft` | 500 |
| 2 | Bâtiments | `buildings` | 500 |
| 3 | Papillons | `butterfly` | 500 |
| 4 | Voitures | `cars` | 500 |
| 5 | Libellules | `dragon fly` | 500 |
| 6 | Feux d'artifice | `fireworks` | 500 |
| 7 | Fleurs | `flowers` | 500 |
| 8 | Poules | `hen` | 500 |
| 9 | Chevaux | `horses` | 500 |
| 10 | Insectes | `insects` | 500 |
| 11 | Motos | `motorcycles` | 500 |
| 12 | Montagnes | `mountains` | 500 |
| 13 | Rivages | `sea shores` | 500 |
| 14 | Navires | `ships` | 500 |
| 15 | Couchers de soleil | `sunset` | 500 |
| 16 | Temples | `temples` | 500 |
| 17 | Arbres | `trees` | 500 |
| 18 | Vallées | `valleys` | 500 |
| 19 | Murs | `walls` | 500 |
| 20 | Yachts | `yacht` | 500 |

> **Note :** Les catégories servent de **vérité terrain (ground truth)** pour l'évaluation de la précision et du rappel du système CBIR.

---

## 3. Téléchargement

### Depuis Kaggle

1. Rendez-vous sur : [https://www.kaggle.com/datasets/mcpython/ghim-10k](https://www.kaggle.com/datasets/mcpython/ghim-10k)
2. Connectez-vous à votre compte Kaggle (créez-en un si nécessaire)
3. Cliquez sur **Download** pour télécharger l'archive ZIP
4. Extrayez le contenu dans le dossier `data/GHIM-10K/` du projet

### Vérification

Après extraction, vérifiez que la structure est correcte :

```powershell
# Depuis la racine du projet
Get-ChildItem -Path data\GHIM-10K -Directory | Measure-Object
# Résultat attendu : Count = 20

Get-ChildItem -Path data\GHIM-10K -Recurse -Filter "*.jpg" | Measure-Object
# Résultat attendu : Count = 10000
```

### Chemin personnalisé

Si vous placez le dataset ailleurs, modifiez la variable `DATASET_PATH` dans `backend/.env` :

```env
DATASET_PATH=C:\chemin\vers\GHIM-10K
```

---

## 4. Structure des répertoires

```
data/
└── GHIM-10K/
    ├── aircraft/
    │   ├── 10_5001.jpg
    │   ├── 10_5002.jpg
    │   ├── ...
    │   └── 10_5500.jpg     (500 images)
    ├── buildings/
    │   ├── 11_5001.jpg
    │   ├── ...
    │   └── 11_5500.jpg     (500 images)
    ├── butterfly/
    │   └── ...              (500 images)
    ├── cars/
    │   └── ...              (500 images)
    ├── dragon fly/
    │   └── ...              (500 images)
    ├── fireworks/
    │   └── ...              (500 images)
    ├── flowers/
    │   └── ...              (500 images)
    ├── hen/
    │   └── ...              (500 images)
    ├── horses/
    │   └── ...              (500 images)
    ├── insects/
    │   └── ...              (500 images)
    ├── motorcycles/
    │   └── ...              (500 images)
    ├── mountains/
    │   └── ...              (500 images)
    ├── sea shores/
    │   └── ...              (500 images)
    ├── ships/
    │   └── ...              (500 images)
    ├── sunset/
    │   └── ...              (500 images)
    ├── temples/
    │   └── ...              (500 images)
    ├── trees/
    │   └── ...              (500 images)
    ├── valleys/
    │   └── ...              (500 images)
    ├── walls/
    │   └── ...              (500 images)
    └── yacht/
        └── ...              (500 images)
```

> **Convention de nommage :** Les fichiers suivent le format `{catégorie_id}_{image_id}.jpg`.

---

## 5. Import dans VisionVault

L'import consiste à enregistrer les images du dataset dans la base de données de VisionVault **sans les copier** (les fichiers sont référencés in-place).

### Méthode 1 : Via l'API

```bash
# Authentification
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@visionvault.com", "password": "demo2024"}'

# Import du dataset
curl -X POST http://localhost:5000/api/v1/index/import \
  -H "Authorization: Bearer <votre_token>"
```

### Méthode 2 : Via le script CLI

```powershell
cd backend
.\venv\Scripts\activate
python scripts/import_dataset.py
```

### Processus d'import

1. **Scan** du dossier `DATASET_PATH` pour trouver tous les fichiers `.jpg`
2. **Création des catégories** à partir des noms de dossiers
3. **Enregistrement des images** dans la base de données :
   - `stored_path` pointe vers l'emplacement original
   - `source_type = "dataset"`
   - Calcul du hash SHA256 pour déduplication
   - Détection des dimensions (largeur × hauteur)
4. **Génération des miniatures** (200×200 px, JPEG quality=85) dans `data/thumbnails/`
5. **Dédoublonnage** : les images déjà importées (même hash ou chemin) sont ignorées

> **Note :** L'import ne copie pas les fichiers — il les référence in-place. Ne déplacez pas le dossier GHIM-10K après l'import.

---

## 6. Indexation

L'indexation consiste à extraire les descripteurs visuels de chaque image et à construire l'index de recherche.

### Méthode 1 : Via l'API

```bash
curl -X POST http://localhost:5000/api/v1/index/rebuild \
  -H "Authorization: Bearer <votre_token>"
```

### Méthode 2 : Via le script CLI

```powershell
cd backend
.\venv\Scripts\activate
python scripts/build_index.py
```

### Processus d'indexation

1. **Extraction** du vecteur de 93 dimensions pour chaque image (voir [algorithmes](algorithms.md))
2. **Ajustement** du `MinMaxScaler` sur l'ensemble des vecteurs
3. **Normalisation** de tous les vecteurs dans l'intervalle [0, 1]
4. **Sauvegarde** de l'index sur disque :
   - `data/index/features.npz` — matrice de caractéristiques
   - `data/index/normalizer.joblib` — paramètres du scaler

### Vérification du statut

```bash
curl http://localhost:5000/api/v1/index/status \
  -H "Authorization: Bearer <votre_token>"
```

Réponse attendue :
```json
{
  "total_images": 10000,
  "indexed_count": 10000,
  "index_built": true,
  "last_updated": "2024-..."
}
```

### Durée estimée

L'indexation de 10 000 images peut prendre de **10 à 30 minutes** selon la puissance de la machine, en raison des calculs intensifs (K-Means pour chaque image, GLCM, LBP, etc.).

---

## 7. Remarques

- **Espace disque :** Le dataset GHIM-10K occupe environ **1,5 Go**. Les miniatures ajoutent environ **200 Mo**. L'index occupe environ **10 Mo**.
- **Ne pas commiter :** Le dossier `data/GHIM-10K/` est exclu du dépôt Git via `.gitignore`.
- **Ground truth :** La structure en catégories du dataset est utilisée comme vérité terrain pour le calcul de Precision@K et Recall@K.
- **Qualité :** Les images sont de résolutions et de qualités variables, ce qui constitue un défi réaliste pour le système CBIR.

---

*Document rédigé dans le cadre du Mini-projet 1 — Multimedia Mining — Groupe G11 — AISD Master S3*
