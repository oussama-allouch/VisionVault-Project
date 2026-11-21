# VisionVault — Architecture du système

## Table des matières

1. [Architecture globale](#1-architecture-globale)
2. [Communication Frontend–Backend](#2-communication-frontendbackend)
3. [Schéma de la base de données](#3-schéma-de-la-base-de-données)
4. [Pipeline CBIR](#4-pipeline-cbir)
5. [Stratégie de stockage](#5-stratégie-de-stockage)

---

## 1. Architecture globale

VisionVault suit une architecture **client-serveur** classique avec un frontend SPA et un backend API REST.

```mermaid
graph TB
    subgraph "Frontend (React + TypeScript)"
        UI["Interface Utilisateur<br/>React + Tailwind CSS"]
        RQ["TanStack Query<br/>Cache & State"]
        AX["Axios Client<br/>JWT Interceptor"]
    end

    subgraph "Backend (Flask + Python)"
        API["API REST<br/>Flask-RESTful"]
        AUTH["Authentification<br/>Flask-JWT-Extended"]
        SVC["Services<br/>Business Logic"]
        CBIR["Module CBIR<br/>OpenCV + scikit-image"]
        ORM["ORM<br/>Flask-SQLAlchemy"]
    end

    subgraph "Stockage"
        DB["SQLite<br/>visionvault.db"]
        FS["Système de fichiers<br/>Images & Thumbnails"]
        IDX["Index CBIR<br/>.npz + .joblib"]
    end

    UI --> RQ --> AX
    AX -->|"HTTP REST<br/>JSON + JWT"| API
    API --> AUTH
    API --> SVC
    SVC --> CBIR
    SVC --> ORM
    ORM --> DB
    SVC --> FS
    CBIR --> IDX
    CBIR --> FS
```

### Stack technologique

| Couche | Technologies |
|--------|-------------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts |
| **Backend** | Python 3.11+, Flask, Flask-RESTful, Flask-SQLAlchemy, Flask-JWT-Extended |
| **Vision par ordinateur** | OpenCV, scikit-image, scikit-learn, NumPy, SciPy |
| **Base de données** | SQLite (via SQLAlchemy) |
| **Stockage fichiers** | Système de fichiers local |

---

## 2. Communication Frontend–Backend

### Architecture REST

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant F as Frontend (React)
    participant A as API (Flask)
    participant S as Service
    participant D as Base de données

    U->>F: Interaction UI
    F->>A: HTTP Request + JWT
    A->>A: Vérification JWT
    A->>S: Appel service
    S->>D: Requête SQLAlchemy
    D-->>S: Résultat
    S-->>A: Données
    A-->>F: JSON Response
    F-->>U: Mise à jour UI
```

### Endpoints principaux

| Groupe | Préfixe | Description |
|--------|---------|-------------|
| Auth | `/api/v1/auth/*` | Connexion, inscription, refresh token |
| Images | `/api/v1/images/*` | CRUD images, upload, download |
| Catégories | `/api/v1/categories/*` | Gestion des catégories |
| Traitement | `/api/v1/images/{id}/crop,resize,transform` | Transformations d'images |
| Descripteurs | `/api/v1/images/{id}/features,color-histogram,...` | Extraction de caractéristiques |
| CBIR | `/api/v1/cbir/*` | Recherche et feedback |
| Index | `/api/v1/index/*` | Import et indexation |
| Analytiques | `/api/v1/analytics/*` | Statistiques et évaluation |

### Authentification JWT

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API

    C->>A: POST /auth/login {email, password}
    A-->>C: {access_token, refresh_token}
    
    Note over C: Stockage tokens (localStorage)
    
    C->>A: GET /images (Authorization: Bearer <access>)
    A-->>C: 200 {images: [...]}
    
    Note over C,A: Token expiré
    
    C->>A: GET /images (Authorization: Bearer <expired>)
    A-->>C: 401 Unauthorized
    C->>A: POST /auth/refresh (Authorization: Bearer <refresh>)
    A-->>C: {access_token: <new>}
    C->>A: GET /images (Authorization: Bearer <new>)
    A-->>C: 200 {images: [...]}
```

### Proxy Vite (Développement)

En mode développement, Vite (port 5173) proxifie les requêtes `/api` vers Flask (port 5000) :

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:5000'
  }
}
```

---

## 3. Schéma de la base de données

```mermaid
erDiagram
    User {
        int id PK
        string email UK
        string password_hash
        string role
        datetime created_at
    }

    Category {
        int id PK
        string name
        int parent_id FK
        datetime created_at
    }

    Image {
        int id PK
        string filename
        string stored_path
        string thumbnail_path
        int category_id FK
        string source_type
        int parent_image_id FK
        int width
        int height
        int file_size
        string content_hash
        datetime created_at
        bool is_indexed
    }

    ImageTransformation {
        int id PK
        int source_image_id FK
        int result_image_id FK
        string operation
        json parameters
        datetime created_at
    }

    SearchSession {
        int id PK
        int user_id FK
        int query_image_id FK
        datetime created_at
    }

    FeedbackIteration {
        int id PK
        int session_id FK
        int iteration_number
        json relevant_image_ids
        json non_relevant_image_ids
        json weights
        json query_vector
        json result_image_ids
        float precision_at_k
        float recall_at_k
        datetime created_at
    }

    SearchHistory {
        int id PK
        int user_id FK
        int session_id FK
        string search_type
        int result_count
        int duration_ms
        datetime created_at
    }

    User ||--o{ SearchSession : "effectue"
    User ||--o{ SearchHistory : "historique"
    Category ||--o| Category : "parent"
    Category ||--o{ Image : "contient"
    Image ||--o| Image : "parent_image"
    Image ||--o{ ImageTransformation : "source"
    Image ||--o{ ImageTransformation : "résultat"
    SearchSession ||--o{ FeedbackIteration : "itérations"
    SearchSession ||--o{ SearchHistory : "logs"
    Image ||--o{ SearchSession : "image requête"
```

### Description des tables

| Table | Rôle |
|-------|------|
| **User** | Comptes utilisateurs avec authentification par email/mot de passe hashé (werkzeug) |
| **Category** | Catégories hiérarchiques (auto-référence via `parent_id`) |
| **Image** | Métadonnées des images (dataset, uploads, transformées). `source_type` ∈ {dataset, upload, transformed} |
| **ImageTransformation** | Journal des transformations (crop, resize, rotate, flip) |
| **SearchSession** | Session de recherche CBIR liée à une image requête |
| **FeedbackIteration** | Itération de feedback : poids, requête, résultats, métriques |
| **SearchHistory** | Log de toutes les recherches pour les analytiques |

---

## 4. Pipeline CBIR

### Indexation

```mermaid
flowchart LR
    A["Images<br/>du dataset"] --> B["Extraction<br/>des descripteurs"]
    B --> C["Vecteur 93-D<br/>par image"]
    C --> D["Ajustement<br/>MinMaxScaler"]
    D --> E["Normalisation<br/>[0, 1]"]
    E --> F["Sauvegarde<br/>Index .npz"]
    D --> G["Sauvegarde<br/>Scaler .joblib"]
```

### Recherche simple

```mermaid
flowchart LR
    Q["Image<br/>requête"] --> EX["Extraction<br/>descripteurs"]
    EX --> NR["Normalisation<br/>(scaler existant)"]
    NR --> DIST["Calcul distances<br/>Euclidiennes"]
    IDX["Index<br/>chargé"] --> DIST
    DIST --> SORT["Tri par<br/>distance"]
    SORT --> RES["Top-K<br/>résultats"]
```

### Relevance Feedback

```mermaid
flowchart TD
    R1["Résultats<br/>initiaux"]
    R1 --> FB["Feedback<br/>utilisateur"]
    FB --> REL["Images<br/>pertinentes ✅"]
    FB --> NREL["Images<br/>non pertinentes ❌"]
    
    REL --> SIGMA_R["σ_rel,i<br/>Écart-type<br/>pertinentes"]
    R1 --> SIGMA_NR["σ_Nr,i<br/>Écart-type<br/>tous résultats"]
    
    SIGMA_R --> W["Nouveaux poids<br/>w_i = (ε+σ_Nr)/(ε+σ_rel)"]
    SIGMA_NR --> W
    
    REL --> QNEW["Nouvelle requête<br/>Q = mean(pertinentes)"]
    
    W --> SEARCH["Nouvelle recherche<br/>pondérée"]
    QNEW --> SEARCH
    
    SEARCH --> R2["Résultats<br/>améliorés"]
    R2 -.-> FB
```

---

## 5. Stratégie de stockage

### Structure des fichiers

```
data/
├── GHIM-10K/              # Dataset original (non modifié, non copié)
│   ├── aircraft/
│   ├── buildings/
│   ├── ...
│   └── yacht/
├── uploads/                # Images uploadées par les utilisateurs
│   └── {uuid}_{filename}
├── thumbnails/             # Miniatures 200×200 (toutes les images)
│   ├── GHIM-10K/
│   │   ├── aircraft/
│   │   └── ...
│   └── uploads/
└── index/                  # Index CBIR
    ├── features.npz        # Matrice de caractéristiques + IDs
    └── normalizer.joblib   # Scaler ajusté
```

### Principes

| Principe | Description |
|----------|-------------|
| **Référence in-place** | Les images du dataset ne sont jamais copiées. La base stocke le chemin vers l'original |
| **Miniatures séparées** | Les thumbnails 200×200 sont générés dans un dossier dédié |
| **Index persistant** | L'index CBIR est sérialisé sur disque et rechargé au démarrage |
| **Isolation uploads** | Les uploads utilisateur sont stockés séparément avec un UUID |
| **Pas de commit data** | Tout le dossier `data/` est exclu de Git via `.gitignore` |

### URLs de service

| Type | URL |
|------|-----|
| Image complète | `GET /api/v1/static/images/{path}` |
| Miniature | `GET /api/v1/static/thumbnails/{path}` |
| Téléchargement | `GET /api/v1/images/{id}/download` |

---

*Document rédigé dans le cadre du Mini-projet 1 — Multimedia Mining — Groupe G11 — AISD Master S3*
