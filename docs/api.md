# VisionVault — Documentation API

Base URL: `http://localhost:5000/api/v1`

Toutes les réponses sont au format **JSON**. Toutes les routes (sauf `/auth/login` et `/auth/register`) nécessitent un **JWT Bearer token**.

---

## Table des matières

1. [Authentification](#1-authentification)
2. [Images](#2-images)
3. [Catégories](#3-catégories)
4. [Traitement d'images](#4-traitement-dimages)
5. [Descripteurs visuels](#5-descripteurs-visuels)
6. [Recherche CBIR](#6-recherche-cbir)
7. [Index & Import](#7-index--import)
8. [Analytiques](#8-analytiques)
9. [Codes d'erreur](#9-codes-derreur)

---

## 1. Authentification

### POST `/auth/login`

Authentification par email et mot de passe.

**Request :**
```json
{
  "email": "demo@visionvault.com",
  "password": "demo2024"
}
```

**Response (200) :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "email": "demo@visionvault.com",
    "role": "admin"
  }
}
```

**Errors :** `401` — Email ou mot de passe invalide

---

### POST `/auth/register`

Création d'un nouveau compte utilisateur.

**Request :**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (201) :**
```json
{
  "message": "User created successfully",
  "user": {
    "id": 2,
    "email": "user@example.com",
    "role": "user"
  }
}
```

**Errors :** `409` — Email déjà utilisé | `422` — Données invalides

---

### POST `/auth/refresh`

Renouvellement du token d'accès.

**Headers :** `Authorization: Bearer <refresh_token>`

**Response (200) :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

### GET `/auth/me`

Informations sur l'utilisateur courant.

**Headers :** `Authorization: Bearer <access_token>`

**Response (200) :**
```json
{
  "id": 1,
  "email": "demo@visionvault.com",
  "role": "admin",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### POST `/auth/logout`

Révocation du token.

**Headers :** `Authorization: Bearer <access_token>`

**Response (200) :**
```json
{
  "message": "Successfully logged out"
}
```

---

## 2. Images

### GET `/images`

Liste paginée des images avec filtres.

**Query Parameters :**

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `page` | int | 1 | Numéro de page |
| `per_page` | int | 25 | Résultats par page |
| `category_id` | int | — | Filtrer par catégorie |
| `search` | string | — | Recherche par nom de fichier |
| `sort_by` | string | `created_at` | Champ de tri : `created_at`, `filename`, `file_size` |
| `sort_order` | string | `desc` | Ordre : `asc` ou `desc` |

**Response (200) :**
```json
{
  "images": [
    {
      "id": 1,
      "filename": "10_5001.jpg",
      "thumbnail_url": "/api/v1/static/thumbnails/GHIM-10K/aircraft/10_5001.jpg",
      "image_url": "/api/v1/static/images/GHIM-10K/aircraft/10_5001.jpg",
      "category_id": 1,
      "category_name": "aircraft",
      "source_type": "dataset",
      "width": 640,
      "height": 480,
      "file_size": 125432,
      "created_at": "2024-01-01T00:00:00Z",
      "is_indexed": true
    }
  ],
  "total": 10000,
  "page": 1,
  "per_page": 25,
  "pages": 400
}
```

---

### POST `/images`

Upload d'une image.

**Request :** `multipart/form-data`

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `file` | file | ✅ | Fichier image (JPEG, PNG, WebP) |
| `category_id` | int | ❌ | ID de la catégorie |

**Response (201) :**
```json
{
  "message": "Image uploaded successfully",
  "image": {
    "id": 10001,
    "filename": "my_photo.jpg",
    "source_type": "upload",
    "width": 1920,
    "height": 1080,
    "file_size": 524288,
    "is_indexed": false
  }
}
```

**Errors :** `413` — Fichier trop volumineux (> 16 Mo) | `422` — Format non supporté

---

### GET `/images/{id}`

Détails d'une image.

**Response (200) :**
```json
{
  "id": 1,
  "filename": "10_5001.jpg",
  "thumbnail_url": "/api/v1/static/thumbnails/GHIM-10K/aircraft/10_5001.jpg",
  "image_url": "/api/v1/static/images/GHIM-10K/aircraft/10_5001.jpg",
  "category_id": 1,
  "category_name": "aircraft",
  "source_type": "dataset",
  "parent_image_id": null,
  "width": 640,
  "height": 480,
  "file_size": 125432,
  "content_hash": "a1b2c3d4...",
  "created_at": "2024-01-01T00:00:00Z",
  "is_indexed": true
}
```

**Errors :** `404` — Image non trouvée

---

### DELETE `/images/{id}`

Suppression d'une image (soft delete — ne supprime pas les fichiers du dataset).

**Response (200) :**
```json
{
  "message": "Image deleted successfully"
}
```

---

### POST `/images/bulk-upload`

Upload de plusieurs images.

**Request :** `multipart/form-data` avec plusieurs champs `files`

**Response (201) :**
```json
{
  "message": "Bulk upload completed",
  "uploaded": 5,
  "failed": 0,
  "images": [...]
}
```

---

### POST `/images/bulk-delete`

Suppression groupée.

**Request :**
```json
{
  "image_ids": [1, 2, 3, 4, 5]
}
```

**Response (200) :**
```json
{
  "message": "5 images deleted successfully",
  "deleted_count": 5
}
```

---

### GET `/images/{id}/download`

Téléchargement du fichier image.

**Response :** Fichier binaire avec `Content-Disposition: attachment`

---

### POST `/images/bulk-download`

Téléchargement d'une archive ZIP.

**Request :**
```json
{
  "image_ids": [1, 2, 3]
}
```

**Response :** Fichier ZIP

---

### POST `/images/{id}/move`

Déplacement d'une image vers une autre catégorie.

**Request :**
```json
{
  "category_id": 5
}
```

**Response (200) :**
```json
{
  "message": "Image moved successfully",
  "image": { "id": 1, "category_id": 5, "category_name": "dragon fly" }
}
```

---

## 3. Catégories

### GET `/categories`

Arbre hiérarchique des catégories.

**Response (200) :**
```json
{
  "categories": [
    {
      "id": 1,
      "name": "aircraft",
      "parent_id": null,
      "image_count": 500,
      "children": [],
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "name": "buildings",
      "parent_id": null,
      "image_count": 500,
      "children": []
    }
  ]
}
```

---

### POST `/categories`

Création d'une catégorie.

**Request :**
```json
{
  "name": "Nouvelle catégorie",
  "parent_id": null
}
```

**Response (201) :**
```json
{
  "message": "Category created",
  "category": { "id": 21, "name": "Nouvelle catégorie", "parent_id": null }
}
```

---

### PATCH `/categories/{id}`

Renommage d'une catégorie.

**Request :**
```json
{
  "name": "Nouveau nom"
}
```

**Response (200) :**
```json
{
  "message": "Category updated",
  "category": { "id": 1, "name": "Nouveau nom" }
}
```

---

### DELETE `/categories/{id}`

Suppression d'une catégorie.

**Response (200) :**
```json
{
  "message": "Category deleted"
}
```

**Errors :** `400` — Catégorie contient des images (préciser la gestion souhaitée)

---

## 4. Traitement d'images

### POST `/images/{id}/crop`

Recadrage d'une image. Crée une nouvelle image.

**Request :**
```json
{
  "x": 100,
  "y": 50,
  "width": 400,
  "height": 300
}
```

**Response (201) :**
```json
{
  "message": "Image cropped successfully",
  "image": {
    "id": 10002,
    "filename": "10_5001_cropped.jpg",
    "source_type": "transformed",
    "parent_image_id": 1,
    "width": 400,
    "height": 300
  }
}
```

---

### POST `/images/{id}/resize`

Redimensionnement.

**Request :**
```json
{
  "width": 800,
  "height": 600,
  "maintain_aspect": true
}
```

**Response (201) :**
```json
{
  "message": "Image resized successfully",
  "image": {
    "id": 10003,
    "source_type": "transformed",
    "parent_image_id": 1,
    "width": 800,
    "height": 600
  }
}
```

---

### POST `/images/{id}/transform`

Transformations multiples (rotation, flip).

**Request :**
```json
{
  "operations": [
    { "type": "rotate", "angle": 90 },
    { "type": "flip", "direction": "horizontal" }
  ]
}
```

**Response (201) :**
```json
{
  "message": "Image transformed successfully",
  "image": {
    "id": 10004,
    "source_type": "transformed",
    "parent_image_id": 1
  }
}
```

---

## 5. Descripteurs visuels

### GET `/images/{id}/features`

Vecteur de caractéristiques complet.

**Response (200) :**
```json
{
  "image_id": 1,
  "feature_dim": 93,
  "is_indexed": true,
  "groups": {
    "color_histogram": { "start": 0, "end": 47, "dim": 48 },
    "color_moments": { "start": 48, "end": 56, "dim": 9 },
    "dominant_colors": { "start": 57, "end": 76, "dim": 20 },
    "glcm": { "start": 77, "end": 82, "dim": 6 },
    "lbp": { "start": 83, "end": 92, "dim": 10 }
  }
}
```

---

### GET `/images/{id}/color-histogram`

Histogramme de couleur HSV.

**Response (200) :**
```json
{
  "image_id": 1,
  "h_hist": [0.05, 0.08, 0.12, ...],
  "s_hist": [0.03, 0.07, 0.15, ...],
  "v_hist": [0.01, 0.04, 0.09, ...],
  "params": { "h_bins": 16, "s_bins": 16, "v_bins": 16 }
}
```

---

### GET `/images/{id}/color-moments`

Moments de couleur (moyenne, écart-type, skewness).

**Response (200) :**
```json
{
  "image_id": 1,
  "moments": {
    "H": { "mean": 85.2, "std": 42.1, "skewness": -0.32 },
    "S": { "mean": 128.5, "std": 65.3, "skewness": 0.15 },
    "V": { "mean": 150.8, "std": 55.7, "skewness": -0.45 }
  }
}
```

---

### GET `/images/{id}/dominant-colors`

Couleurs dominantes extraites par K-Means.

**Response (200) :**
```json
{
  "image_id": 1,
  "colors": [
    { "rgb": [135, 180, 220], "hex": "#87B4DC", "percentage": 35.2 },
    { "rgb": [60, 90, 130], "hex": "#3C5A82", "percentage": 25.8 },
    { "rgb": [200, 210, 225], "hex": "#C8D2E1", "percentage": 18.5 },
    { "rgb": [40, 50, 70], "hex": "#283246", "percentage": 12.1 },
    { "rgb": [170, 150, 140], "hex": "#AA968C", "percentage": 8.4 }
  ]
}
```

---

### GET `/images/{id}/glcm`

Propriétés GLCM.

**Response (200) :**
```json
{
  "image_id": 1,
  "features": {
    "contrast": 125.45,
    "correlation": 0.92,
    "energy": 0.015,
    "homogeneity": 0.28,
    "dissimilarity": 7.83,
    "asm": 0.00023
  },
  "params": { "distances": [1], "angles": 4, "levels": 64 }
}
```

---

### GET `/images/{id}/lbp`

Histogramme LBP.

**Response (200) :**
```json
{
  "image_id": 1,
  "histogram": [0.05, 0.08, 0.12, 0.15, 0.10, 0.09, 0.11, 0.13, 0.07, 0.10],
  "params": { "P": 8, "R": 1, "method": "uniform", "n_bins": 10 }
}
```

---

## 6. Recherche CBIR

### POST `/cbir/search`

Lancer une recherche CBIR.

**Request :**
```json
{
  "query_image_id": 42,
  "num_results": 25
}
```

**Response (200) :**
```json
{
  "session_id": 1,
  "query_image": {
    "id": 42,
    "filename": "10_5042.jpg",
    "category_name": "aircraft"
  },
  "results": [
    {
      "rank": 1,
      "image_id": 42,
      "image": { "id": 42, "filename": "10_5042.jpg", "category_name": "aircraft", "thumbnail_url": "..." },
      "distance": 0.0
    },
    {
      "rank": 2,
      "image_id": 87,
      "image": { "id": 87, "filename": "10_5087.jpg", "category_name": "aircraft", "thumbnail_url": "..." },
      "distance": 0.142
    }
  ],
  "total_results": 25,
  "search_time_ms": 45,
  "iteration": 0,
  "weights": null
}
```

---

### POST `/cbir/search/upload`

Recherche avec une image uploadée (non présente dans la base).

**Request :** `multipart/form-data`

| Champ | Type | Description |
|-------|------|-------------|
| `file` | file | Image requête |
| `num_results` | int | Nombre de résultats (défaut: 25) |

**Response :** Même format que `POST /cbir/search`

---

### POST `/cbir/feedback`

Appliquer le Relevance Feedback (Re-weighting Type-1).

**Request :**
```json
{
  "session_id": 1,
  "iteration": 1,
  "relevant_ids": [42, 87, 103, 156],
  "non_relevant_ids": [201, 345, 567]
}
```

**Response (200) :**
```json
{
  "session_id": 1,
  "iteration": 1,
  "results": [
    {
      "rank": 1,
      "image_id": 87,
      "image": { "id": 87, "filename": "10_5087.jpg", "category_name": "aircraft", "thumbnail_url": "..." },
      "distance": 0.098
    }
  ],
  "weights": {
    "color_histogram": [1.2, 0.8, 1.5, ...],
    "color_moments": [2.1, 0.5, 1.0, ...],
    "dominant_colors": [0.9, 1.1, ...],
    "glcm": [3.2, 0.7, 1.4, 0.8, 1.1, 0.6],
    "lbp": [1.5, 0.9, ...]
  },
  "query_vector_updated": true,
  "num_relevant": 4,
  "num_non_relevant": 3,
  "precision_at_k": 0.72,
  "recall_at_k": 0.036,
  "search_time_ms": 52
}
```

**Errors :** `400` — Aucune image pertinente sélectionnée | `404` — Session non trouvée

---

### GET `/cbir/sessions/{id}`

Détails d'une session de recherche.

**Response (200) :**
```json
{
  "id": 1,
  "query_image": { "id": 42, "filename": "10_5042.jpg" },
  "iterations": [
    {
      "iteration_number": 0,
      "relevant_count": 0,
      "non_relevant_count": 0,
      "result_count": 25,
      "precision_at_k": 0.48,
      "recall_at_k": 0.024,
      "created_at": "2024-01-01T12:00:00Z"
    },
    {
      "iteration_number": 1,
      "relevant_count": 4,
      "non_relevant_count": 3,
      "result_count": 25,
      "precision_at_k": 0.72,
      "recall_at_k": 0.036,
      "created_at": "2024-01-01T12:01:30Z"
    }
  ],
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

### GET `/cbir/sessions/{id}/history`

Historique des itérations avec évolution des poids.

**Response (200) :**
```json
{
  "session_id": 1,
  "iterations": [
    {
      "iteration": 0,
      "weights": null,
      "precision_at_k": 0.48,
      "recall_at_k": 0.024
    },
    {
      "iteration": 1,
      "weights": { "color_histogram": [...], "glcm": [...], "lbp": [...] },
      "precision_at_k": 0.72,
      "recall_at_k": 0.036
    }
  ]
}
```

---

### DELETE `/cbir/sessions/{id}`

Suppression d'une session.

**Response (200) :**
```json
{
  "message": "Session deleted"
}
```

---

## 7. Index & Import

### POST `/index/import`

Lancer l'import du dataset GHIM-10K.

**Response (200) :**
```json
{
  "message": "Import started",
  "total_found": 10000,
  "already_imported": 0,
  "to_import": 10000
}
```

---

### POST `/index/rebuild`

Reconstruire l'index de caractéristiques.

**Response (200) :**
```json
{
  "message": "Index rebuild started",
  "total_images": 10000
}
```

---

### GET `/index/status`

Statut de l'index.

**Response (200) :**
```json
{
  "total_images": 10000,
  "indexed_count": 10000,
  "index_built": true,
  "last_updated": "2024-01-01T13:00:00Z"
}
```

---

## 8. Analytiques

### GET `/analytics/overview`

Vue d'ensemble des statistiques.

**Response (200) :**
```json
{
  "total_images": 10000,
  "categories": 20,
  "user_uploads": 5,
  "total_searches": 42,
  "index_status": {
    "indexed_count": 10000,
    "index_built": true
  },
  "category_distribution": [
    { "name": "aircraft", "count": 500 },
    { "name": "buildings", "count": 500 }
  ],
  "recent_activity": [
    {
      "type": "search",
      "query_image": "10_5042.jpg",
      "result_count": 25,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

---

### GET `/analytics/evaluation`

Métriques d'évaluation du CBIR.

**Response (200) :**
```json
{
  "total_sessions": 42,
  "avg_precision_at_k": 0.65,
  "avg_recall_at_k": 0.032,
  "avg_search_time_ms": 48,
  "precision_by_category": [
    { "category": "aircraft", "avg_precision": 0.72 },
    { "category": "buildings", "avg_precision": 0.58 }
  ]
}
```

---

### GET `/health`

Vérification de santé.

**Response (200) :**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "index": "loaded"
}
```

---

## 9. Codes d'erreur

Toutes les erreurs suivent le format :

```json
{
  "error": "ErrorType",
  "message": "Description lisible de l'erreur",
  "status_code": 400
}
```

| Code | Erreur | Description |
|------|--------|-------------|
| `400` | Bad Request | Requête malformée ou paramètres manquants |
| `401` | Unauthorized | Token JWT manquant, invalide ou expiré |
| `403` | Forbidden | Droits insuffisants |
| `404` | Not Found | Ressource non trouvée |
| `409` | Conflict | Conflit (ex: email déjà utilisé) |
| `413` | Payload Too Large | Fichier > 16 Mo |
| `422` | Unprocessable Entity | Données de validation invalides |
| `500` | Internal Server Error | Erreur serveur interne |

---

*Document rédigé dans le cadre du Mini-projet 1 — Multimedia Mining — Groupe G11 — AISD Master S3*
