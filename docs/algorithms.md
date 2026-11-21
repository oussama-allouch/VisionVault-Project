# VisionVault — Algorithmes & Descripteurs Visuels

Ce document détaille les algorithmes d'extraction de caractéristiques, la construction du vecteur de descripteurs, la mesure de similarité et le mécanisme de Relevance Feedback utilisés dans le moteur CBIR de VisionVault.

---

## Table des matières

1. [Vue d'ensemble du pipeline](#1-vue-densemble-du-pipeline)
2. [Descripteurs de couleur](#2-descripteurs-de-couleur)
3. [Descripteurs de texture GLCM](#3-descripteurs-de-texture-glcm)
4. [Descripteurs de texture LBP](#4-descripteurs-de-texture-lbp)
5. [Construction du vecteur de caractéristiques](#5-construction-du-vecteur-de-caractéristiques)
6. [Normalisation](#6-normalisation)
7. [Mesure de similarité](#7-mesure-de-similarité)
8. [Relevance Feedback — Re-weighting Type-1](#8-relevance-feedback--re-weighting-type-1)
9. [Métriques d'évaluation](#9-métriques-dévaluation)

---

## 1. Vue d'ensemble du pipeline

```
Image → Extraction de caractéristiques → Vecteur 93-D → Normalisation → Indexation
                                                                          ↓
Requête → Extraction → Normalisation → Distance Euclidienne pondérée → Résultats triés
                                              ↑
                                   Relevance Feedback (Re-weighting Type-1)
```

Chaque image est représentée par un vecteur de **93 dimensions** combinant des descripteurs de couleur et de texture.

---

## 2. Descripteurs de couleur

### 2.1 Histogramme de couleur (HSV)

L'image est d'abord convertie de l'espace RGB vers l'espace **HSV** (Hue, Saturation, Value), plus robuste aux variations d'éclairage.

**Paramètres :**
- Nombre de bins par canal : H = 16, S = 16, V = 16

**Algorithme :**
1. Conversion BGR → HSV via `cv2.cvtColor(image, cv2.COLOR_BGR2HSV)`
2. Calcul de l'histogramme par canal avec `cv2.calcHist()`
3. Normalisation L1 de chaque histogramme (somme = 1)
4. Concaténation des 3 histogrammes

**Formule de normalisation L1 :**

$$h_{\text{norm}}[i] = \frac{h[i]}{\sum_{j=0}^{B-1} h[j]}$$

où $B$ est le nombre de bins.

**Dimension de sortie : 48** (16 + 16 + 16)

---

### 2.2 Moments de couleur

Les moments statistiques capturent la distribution des couleurs de manière compacte.

Pour chaque canal C ∈ {H, S, V} :

**Moment d'ordre 1 — Moyenne :**

$$\mu_C = \frac{1}{N} \sum_{i=1}^{N} p_{C,i}$$

**Moment d'ordre 2 — Écart-type :**

$$\sigma_C = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (p_{C,i} - \mu_C)^2}$$

**Moment d'ordre 3 — Asymétrie (Skewness) :**

$$s_C = \frac{\frac{1}{N} \sum_{i=1}^{N} (p_{C,i} - \mu_C)^3}{\sigma_C^3}$$

Calculé via `scipy.stats.skew()`.

où $p_{C,i}$ est la valeur du pixel $i$ dans le canal $C$ et $N$ le nombre total de pixels.

**Dimension de sortie : 9** (3 canaux × 3 moments)

---

### 2.3 Couleurs dominantes (K-Means)

Les couleurs dominantes sont extraites par clustering K-Means dans l'espace RGB.

**Paramètres :**
- Nombre de clusters : $K = 5$
- `random_state = 42` (reproductibilité)

**Algorithme :**
1. Reformatage de l'image en matrice $(N, 3)$ de pixels RGB
2. K-Means sur au plus 5 000 pixels échantillonnés avec la graine 42. Le nombre de clusters est limité au nombre de couleurs distinctes.
3. Tri par fréquence décroissante, puis par centroïde RVB en cas d’égalité. Les slots absents sont complétés de zéros.
4. Pour chaque cluster : extraction du centroïde RGB et du pourcentage

**Vecteur de sortie :** Pour chaque couleur dominante $k$ :

$$\mathbf{v}_k = \left[\frac{R_k}{255},\ \frac{G_k}{255},\ \frac{B_k}{255},\ \text{pct}_k\right]$$

**Dimension de sortie : 20** (5 couleurs × 4 valeurs)

---

## 3. Descripteurs de texture GLCM

La matrice de co-occurrence des niveaux de gris (GLCM — Gray-Level Co-occurrence Matrix) capture les relations spatiales entre les pixels.

### 3.1 Construction de la GLCM

**Définition :** La GLCM $P_{d,\theta}(i, j)$ compte le nombre de paires de pixels ayant les niveaux de gris $i$ et $j$, séparés par une distance $d$ dans la direction $\theta$.

$$P_{d,\theta}(i, j) = \#\{((r_1, c_1), (r_2, c_2)) : I(r_1, c_1) = i,\ I(r_2, c_2) = j\}$$

**Paramètres :**
- Distances : $d = [1]$
- Angles : $\theta = [0°, 45°, 90°, 135°]$ soit $[0, \frac{\pi}{4}, \frac{\pi}{2}, \frac{3\pi}{4}]$
- Niveaux de gris : $L = 64$. Un gris entier $g$ est quantifié par $\lfloor 64g/256 \rfloor$. La matrice est symétrique et normalisée.

**Implémentation :** `skimage.feature.graycomatrix()`

### 3.2 Propriétés extraites

Les propriétés sont calculées via `skimage.feature.graycoprops()` puis moyennées sur les 4 angles :

| Propriété | Formule |
|-----------|---------|
| **Contraste** | $\sum_{i,j} (i-j)^2 \cdot P(i,j)$ |
| **Corrélation** | $\sum_{i,j} \frac{(i - \mu_i)(j - \mu_j) \cdot P(i,j)}{\sigma_i \cdot \sigma_j}$ |
| **Énergie** | $\sqrt{\sum_{i,j} P(i,j)^2}$ |
| **Homogénéité** | $\sum_{i,j} \frac{P(i,j)}{1 + (i-j)^2}$ |
| **Dissimilarité** | $\sum_{i,j} |i-j| \cdot P(i,j)$ |
| **ASM** | $\sum_{i,j} P(i,j)^2$ |

**Dimension de sortie : 6** (6 propriétés moyennées sur 4 angles)

---

## 4. Descripteurs de texture LBP

Le Local Binary Pattern (LBP) est un opérateur de texture robuste qui décrit la structure locale autour de chaque pixel.

### 4.1 Algorithme LBP

**Paramètres :**
- $P = 8$ points voisins
- $R = 1$ rayon
- Méthode : `uniform`

**Formule :**

$$\text{LBP}_{P,R}(x_c, y_c) = \sum_{p=0}^{P-1} s(g_p - g_c) \cdot 2^p$$

où :
- $g_c$ = valeur du pixel central
- $g_p$ = valeur du pixel voisin $p$
- $s(x) = \begin{cases} 1 & \text{si } x \geq 0 \\ 0 & \text{sinon} \end{cases}$

### 4.2 Motifs uniformes

Un motif LBP est dit **uniforme** s'il contient au plus 2 transitions bitwise (0→1 ou 1→0). Avec $P = 8$ :
- Nombre de motifs uniformes : $P \times (P - 1) + 2 = 58$
- Mais regroupés en $P + 2 = 10$ bins (incluant un bin pour les non-uniformes)

**Implémentation :** `skimage.feature.local_binary_pattern(image, P=8, R=1, method='uniform')`

### 4.3 Histogramme

L'histogramme LBP est calculé sur l'image transformée puis normalisé (L1) :

$$h_{\text{LBP}}[b] = \frac{\#\{(x,y) : \text{LBP}(x,y) = b\}}{\sum_b \#\{(x,y) : \text{LBP}(x,y) = b\}}$$

**Dimension de sortie : 10** ($P + 2 = 10$ bins)

---

## 5. Construction du vecteur de caractéristiques

Le vecteur final de **93 dimensions** est construit par concaténation :

| Groupe | Indices | Dimension | Description |
|--------|---------|-----------|-------------|
| Histogramme de couleur | 0 – 47 | 48 | Histogrammes H, S, V (16 bins chacun) |
| Moments de couleur | 48 – 56 | 9 | Moyenne, écart-type, skewness × 3 canaux |
| Couleurs dominantes | 57 – 76 | 20 | 5 couleurs × (R, G, B normalisés + pourcentage) |
| GLCM | 77 – 82 | 6 | Contraste, corrélation, énergie, homogénéité, dissimilarité, ASM |
| LBP | 83 – 92 | 10 | Histogramme LBP uniforme (P=8, R=1) |
| **Total** | **0 – 92** | **93** | |

**Validation :**
- Remplacement des valeurs NaN/Inf par 0
- Vérification de la dimension constante (93) pour toute image

---

## 6. Normalisation

### MinMaxScaler

La normalisation Min-Max ramène chaque composante du vecteur dans l'intervalle $[0, 1]$ :

$$x'_i = \frac{x_i - \min_i}{\max_i - \min_i}$$

où $\min_i$ et $\max_i$ sont les valeurs minimale et maximale de la composante $i$ sur l'ensemble du dataset.

**Points critiques :**
- Le scaler est ajusté sur les images de l’instantané à chaque construction ou mise à jour de l’index.
- Une requête est transformée avec les mêmes coefficients, sans nouvel ajustement. Un fichier externe peut sortir de l’intervalle.
- L’échelle et le décalage sont sauvegardés avec les vecteurs bruts dans `features.npz`.

---

## 7. Mesure de similarité

### Distance Euclidienne Pondérée — Équation (3)

$$D(X, Y) = \sqrt{\frac{\sum_{i=1}^{D} w_i \cdot (x_i - y_i)^2}{\sum_{i=1}^{D} w_i}}$$

où :
- $X = (x_1, x_2, \ldots, x_D)$ et $Y = (y_1, y_2, \ldots, y_D)$ sont deux vecteurs de caractéristiques normalisés
- $w_i$ est le poids de la composante $i$
- $D = 93$ est la dimension du vecteur

**Initialisation :** $w_i = 1 \quad \forall i \in \{1, \ldots, D\}$

Lorsque tous les poids sont égaux à 1, cette formule se réduit à la distance Euclidienne standard normalisée.

---

## 8. Relevance Feedback — Re-weighting Type-1

Référence : Renuka Devi SM, *"Reweighing Strategies for Relevance Feedback in CBIR"*, IJARCCE, Vol. 5, Issue 11, November 2016, DOI: 10.17148/IJARCCE.2016.511118

### 8.1 Principe

Le Relevance Feedback permet à l'utilisateur d'améliorer itérativement les résultats de recherche en indiquant quelles images sont **pertinentes** et lesquelles ne le sont pas. Le système ajuste alors les poids des composantes du vecteur de caractéristiques pour affiner la recherche.

### 8.2 Mise à jour des poids — Équation (5)

$$w_i^{(k+1)} = \frac{\varepsilon + \sigma_{N_r, i}^{(k)}}{\varepsilon + \sigma_{\text{rel}, i}^{(k)}}$$

où :
- $w_i^{(k+1)}$ = nouveau poids de la composante $i$ à l'itération $k+1$
- $\varepsilon = 0.0001$ = constante de lissage pour éviter la division par zéro
- $\sigma_{N_r, i}^{(k)}$ = écart-type de la composante $i$ calculé sur **tous les $N_r$ résultats** retournés à l'itération $k$
- $\sigma_{\text{rel}, i}^{(k)}$ = écart-type de la composante $i$ calculé sur les **images marquées pertinentes** uniquement

### 8.3 Interprétation

| Situation | Effet sur $w_i$ |
|-----------|-----------------|
| $\sigma_{N_r, i}$ grand et $\sigma_{\text{rel}, i}$ petit | $w_i$ augmente → la composante $i$ est discriminante (forte variance globale, faible variance parmi les pertinentes) |
| $\sigma_{N_r, i}$ petit et $\sigma_{\text{rel}, i}$ grand | $w_i$ diminue → la composante $i$ n'est pas discriminante |
| Les deux petits | $w_i \approx 1$ → peu d'effet |

### 8.4 Mise à jour de la requête — Table 1

$$Q_{\text{new}} = \frac{1}{|R|} \sum_{j \in R} \mathbf{f}_j$$

Le nouveau vecteur requête est la **moyenne des vecteurs de caractéristiques** des images marquées pertinentes ($R$).

### 8.5 Algorithme complet d'une itération de feedback

```
Entrée: résultats courants, images pertinentes R, images non-pertinentes NR

1. Récupérer les vecteurs de caractéristiques de tous les résultats (Nr images)
2. Récupérer les vecteurs de caractéristiques des images pertinentes (|R| images)
3. Si |R| = 0 : retourner une erreur (feedback impossible)
4. Calculer σ_Nr,i pour chaque composante i sur les Nr résultats
5. Calculer σ_rel,i pour chaque composante i sur les |R| images pertinentes
   - Si |R| < 2 : σ_rel,i = 0 → w_i = (ε + σ_Nr,i) / ε (poids potentiellement élevés)
6. Calculer les nouveaux poids : w_i^(k+1) = (ε + σ_Nr,i) / (ε + σ_rel,i)
7. Rejeter les vecteurs ou poids non finis. Employer l’écart-type de population (ddof=0).
8. Calculer le nouveau vecteur requête : Q_new = mean(vecteurs pertinents)
9. Rechercher avec la nouvelle requête et les nouveaux poids (Équation 3)
10. Retourner les nouveaux résultats triés par distance croissante
```

### 8.6 Détails importants

> **⚠️ Point critique :** $\sigma_{N_r, i}$ est calculé sur **tous** les $N_r$ résultats retournés, **pas uniquement** sur les non-pertinents. C'est une distinction essentielle par rapport à d'autres méthodes.

> **ε = 0.0001** sert à éviter les divisions par zéro quand l'écart-type est nul (par exemple, quand toutes les images pertinentes ont la même valeur pour une composante).

---

## 9. Métriques d'évaluation

### 9.1 Precision@K

$$\text{Precision@K} = \frac{|\{I_r \in \text{Top-K} : \text{cat}(I_r) = \text{cat}(Q)\}|}{K}$$

La proportion d'images parmi les $K$ premiers résultats qui appartiennent à la même catégorie que l'image requête.

### 9.2 Recall@K

$$\text{Recall@K} = \frac{|\{I_r \in \text{Top-K} : \text{cat}(I_r) = \text{cat}(Q)\}|}{|\{I \in \text{DB} : \text{cat}(I) = \text{cat}(Q)\}|}$$

La proportion d'images de la catégorie de l'image requête qui sont retrouvées dans les $K$ premiers résultats.

**Ground truth :** Les catégories du dataset GHIM-10K (20 catégories × 500 images) servent de vérité terrain.

---

*Document rédigé dans le cadre du Mini-projet 1 — Multimedia Mining — Groupe G11 — AISD Master S3*
