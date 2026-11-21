# VisionVault — Guide d'utilisation

> Ce guide est rédigé en **français** pour les utilisateurs de l'application VisionVault.

---

## Table des matières

1. [Connexion](#1-connexion)
2. [Dashboard (Tableau de bord)](#2-dashboard-tableau-de-bord)
3. [Galerie d'images](#3-galerie-dimages)
4. [Upload d'images](#4-upload-dimages)
5. [Éditeur d'images](#5-éditeur-dimages)
6. [Descripteurs visuels](#6-descripteurs-visuels)
7. [Recherche CBIR](#7-recherche-cbir)
8. [Relevance Feedback](#8-relevance-feedback)
9. [Analytiques](#9-analytiques)

---

## 1. Connexion

### Accès à l'application

1. Ouvrez votre navigateur et accédez à **http://localhost:5173**
2. La page de connexion s'affiche

### Identifiants par défaut

| Champ | Valeur |
|-------|--------|
| Email | `demo@visionvault.com` |
| Mot de passe | `demo2024` |

### Procédure

1. Saisissez votre **adresse email** dans le champ dédié
2. Saisissez votre **mot de passe**
3. Cliquez sur **Se connecter**
4. En cas de succès, vous êtes redirigé vers le **Dashboard**

> **Note :** Les identifiants par défaut sont configurables dans le fichier `.env` du backend.

---

## 2. Dashboard (Tableau de bord)

Le tableau de bord offre une vue d'ensemble de votre galerie VisionVault.

### Éléments affichés

- **Cartes de statistiques :**
  - Nombre total d'images
  - Nombre de catégories
  - Nombre d'images uploadées par l'utilisateur
  - Nombre de recherches effectuées

- **Statut de l'index CBIR :**
  - Nombre d'images indexées
  - État de l'index (construit ou non)

- **Graphique de distribution :**
  - Répartition des images par catégorie (diagramme circulaire)

- **Activité récente :**
  - Dernières recherches effectuées

- **Actions rapides :**
  - Accès direct à la Galerie, l'Upload et la Recherche CBIR

---

## 3. Galerie d'images

La galerie permet de parcourir, filtrer et gérer toutes les images.

### Navigation

1. Cliquez sur **Galerie** dans la barre latérale
2. Les images s'affichent sous forme de grille responsive

### Filtrage et tri

- **Recherche :** Tapez un nom de fichier dans la barre de recherche
- **Catégorie :** Sélectionnez une catégorie dans le menu déroulant
- **Tri :** Par date, nom ou taille (croissant/décroissant)
- **Vue :** Basculez entre la vue grille et la vue liste

### Actions sur une image

Cliquez sur une image pour ouvrir le **détail** :
- Voir l'image en pleine résolution
- Consulter les métadonnées (dimensions, taille, catégorie, date)
- **Télécharger** l'image
- **Éditer** l'image (ouvre l'éditeur)
- **Rechercher** des images similaires (lance une recherche CBIR)
- **Supprimer** l'image (après confirmation)

### Actions groupées

1. Cochez plusieurs images via les cases à cocher
2. La barre d'actions groupées apparaît :
   - **Supprimer** la sélection
   - **Télécharger** en archive ZIP
   - **Déplacer** vers une catégorie

### Pagination

Naviguez entre les pages en bas de la galerie.

---

## 4. Upload d'images

### Accès

Cliquez sur **Upload** dans la barre latérale ou sur le bouton d'action rapide depuis le Dashboard.

### Procédure

1. **Glissez-déposez** des images dans la zone de dépôt (bordure pointillée)
   - Ou cliquez sur **Parcourir** pour sélectionner des fichiers
2. **Formats acceptés :** JPEG, PNG, WebP
3. Sélectionnez une **catégorie** pour les images (optionnel)
4. Visualisez les **aperçus** des fichiers sélectionnés
5. Cliquez sur **Uploader tout**
6. Suivez la **barre de progression** pour chaque fichier
7. Un message de succès ✅ ou d'erreur ❌ s'affiche pour chaque fichier

> **Taille maximale :** 16 Mo par fichier.

---

## 5. Éditeur d'images

L'éditeur permet de transformer une image et de sauvegarder le résultat comme nouvelle image.

### Accès

- Depuis la galerie : cliquez sur une image → **Éditer**
- URL directe : `/editor/{id_de_l_image}`

### Outils disponibles

| Outil | Description |
|-------|-------------|
| **Recadrage (Crop)** | Sélectionnez interactivement la zone à conserver |
| **Redimensionnement** | Modifiez la largeur et/ou la hauteur, avec option de maintien du ratio |
| **Rotation** | Pivotez de 90° dans le sens horaire ou anti-horaire |
| **Retournement (Flip)** | Retournez horizontalement ou verticalement |

### Procédure

1. L'image originale s'affiche à **gauche**
2. L'aperçu du résultat s'affiche à **droite**
3. Appliquez les transformations souhaitées
4. Cliquez sur **Réinitialiser** pour annuler toutes les modifications
5. Cliquez sur **Enregistrer comme nouvelle image** pour sauvegarder
6. La nouvelle image est ajoutée à la galerie avec la mention `source_type = "transformed"`

> **Note :** L'image originale n'est **jamais modifiée**. Chaque transformation crée une nouvelle image.

---

## 6. Descripteurs visuels

Cette page permet de visualiser les caractéristiques visuelles extraites d'une image.

### Accès

- Depuis la galerie : cliquez sur une image → **Descripteurs**
- URL directe : `/features/{id_de_l_image}`

### Descripteurs affichés

#### Histogramme de couleur HSV
- Graphique en barres montrant la distribution des valeurs pour les canaux **H** (teinte), **S** (saturation) et **V** (valeur)
- 16 bins par canal

#### Moments de couleur
- Tableau avec pour chaque canal (H, S, V) :
  - **Moyenne** (1er moment)
  - **Écart-type** (2e moment)
  - **Asymétrie / Skewness** (3e moment)

#### Couleurs dominantes
- Affichage de **5 rectangles de couleur** représentant les couleurs dominantes
- Pour chaque couleur : valeur **hexadécimale** et **pourcentage**

#### GLCM (Matrice de co-occurrence)
- Tableau des propriétés : Contraste, Corrélation, Énergie, Homogénéité, Dissimilarité, ASM

#### LBP (Local Binary Pattern)
- Graphique en barres de l'histogramme LBP (10 bins)

### Résumé du vecteur

- **Dimension totale :** 93
- Répartition par groupe de descripteurs

---

## 7. Recherche CBIR

La recherche par le contenu (CBIR — Content-Based Image Retrieval) permet de trouver des images visuellement similaires.

### Étape 1 : Sélection de l'image requête

1. Cliquez sur **Recherche** dans la barre latérale
2. Choisissez une image requête :
   - **Depuis la galerie :** Ouvrez le sélecteur et choisissez une image existante
   - **Par upload :** Uploadez une nouvelle image comme requête

### Étape 2 : Paramétrage

- **Nombre de résultats :** Choisissez 10, 20, 25 (par défaut) ou 50

### Étape 3 : Lancement de la recherche

1. Cliquez sur **Rechercher**
2. Les résultats s'affichent sous forme de grille :
   - **Rang** de chaque image
   - **Miniature** de l'image
   - **Nom** du fichier
   - **Catégorie** d'appartenance
   - **Distance** au vecteur requête
3. Le **temps de recherche** est affiché

---

## 8. Relevance Feedback

Le Relevance Feedback permet d'améliorer les résultats de recherche de manière itérative.

### Principe

Après une recherche CBIR, vous pouvez indiquer au système quelles images sont **pertinentes** (similaires à ce que vous cherchez) et lesquelles ne le sont **pas**. Le système recalcule alors les poids des descripteurs et la requête pour affiner les résultats.

### Procédure

1. **Après une recherche**, évaluez les résultats :
   - ✅ Cliquez pour marquer une image comme **pertinente**
   - ❌ Cliquez pour marquer une image comme **non pertinente**
   - ⬜ Laissez vide si vous n'avez pas d'avis

2. **Résumé du feedback :**
   - Le panneau affiche : X pertinentes, Y non pertinentes, Z non évaluées

3. **Appliquer le Re-weighting Type-1 :**
   - Cliquez sur **Appliquer Re-weighting Type-1**
   - Le bouton est désactivé si aucune image n'est marquée pertinente

4. **Nouveaux résultats :**
   - Les résultats mis à jour s'affichent
   - Le numéro d'itération s'incrémente
   - Le panneau des **poids** affiche les changements

5. **Visualisation des poids :**
   - Graphique en barres des poids par groupe de descripteurs
   - Comparaison avant/après (à partir de la 2e itération)
   - Formule appliquée avec les valeurs courantes

6. **Itérations successives :**
   - Répétez les étapes 1 à 4 autant de fois que souhaité
   - L'historique des itérations est consultable

7. **Réinitialisation :**
   - Cliquez sur **Nouvelle recherche** pour recommencer
   - Ou **Réinitialiser le feedback** pour revenir à l'itération initiale

### Résultat attendu

À chaque itération, les résultats devraient s'améliorer : les images similaires remontent dans le classement et les images non pertinentes descendent.

---

## 9. Analytiques

La page Analytiques fournit des métriques d'évaluation du système CBIR.

### Métriques affichées

- **Precision@K** à travers les itérations de feedback (graphique linéaire)
- **Recall@K** quand la vérité terrain est disponible
- **Statistiques de recherche :**
  - Nombre total de recherches
  - Temps moyen de recherche
  - Nombre moyen de résultats
- **Évaluation par catégorie :**
  - Précision moyenne par catégorie du dataset
- **Comparaison avant/après feedback :**
  - Tableau montrant l'amélioration des métriques entre la recherche initiale et après feedback

### Export

Cliquez sur **Exporter CSV** pour télécharger les données d'évaluation.

---

*Guide d'utilisation VisionVault — Mini-projet 1 — Multimedia Mining — Groupe G11 — AISD Master S3*
