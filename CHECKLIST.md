# CHECKLIST DE CONFORMITÉ — PROJET VISIONVAULT (GROUPE G11)

Ce document valide le respect rigoureux de chaque exigence du Master Prompt et des spécifications académiques.

---

## 1. Informations Générales & Méthodologie

- [x] **Nom du projet :** VisionVault — Intelligent Image Gallery & CBIR
- [x] **Groupe :** G11 — AISD Master S3 — Multimedia Mining
- [x] **Méthode attribuée :** Re-weighting Type-1 (Équation 5 de Renuka Devi SM, 2016)
- [x] **Dataset :** GHIM-10K (10 000 images, 20 catégories × 500 images)
- [x] **Langue de l'interface :** Français intégral
- [x] **Langue des commentaires techniques :** Français / Anglais cohérent
- [x] **Prêt pour soutenance :** Oui, scénario de démonstration à 17 étapes documenté

---

## 2. Pile Technologique

### Backend
- [x] Python 3.11+
- [x] Flask & Flask-RESTful (classes Resource modulaires)
- [x] Flask-SQLAlchemy & SQLite pour métadonnées, utilisateurs et historique
- [x] Flask-JWT-Extended avec gestion du rafraîchissement et blocage de déconnexion
- [x] Flask-CORS pour communication avec React
- [x] Pillow pour manipulations d'images et miniatures
- [x] OpenCV, scikit-image, scikit-learn, SciPy, NumPy pour la vision par ordinateur
- [x] Aucun GPU ni modèle deep learning requis (méthodes classiques pures)

### Frontend
- [x] React 19 avec TypeScript
- [x] Vite 8 avec compilation ultra-rapide
- [x] Tailwind CSS 4 avec palette indigo/violet et mode sombre
- [x] Lucide React pour les icônes
- [x] Recharts pour les visualisations interactives (histogrammes, barres, camemberts, courbes)
- [x] React Router 7 avec routes protégées et gestion 404
- [x] Axios avec intercepteur JWT
- [x] TanStack React Query & React Hot Toast pour notifications

---

## 3. Descripteurs Visuels (93 dimensions)

- [x] **Histogramme de couleur HSV :** 48 dimensions ($16 \times 3$), normalisé L1
- [x] **Moments de couleur :** 9 dimensions (moyenne, écart-type, skewness sur H, S, V)
- [x] **Couleurs dominantes :** 20 dimensions (5 clusters K-Means en RGB avec pourcentages)
- [x] **Matrice GLCM :** 6 dimensions (contraste, corrélation, énergie, homogénéité, dissimilarité, ASM moyennés sur 4 angles)
- [x] **Descripteur LBP :** 10 dimensions (LBP uniforme $P=8, R=1$, normalisé L1)
- [x] **Normalisation globale :** Min-Max Scaler ajusté et sauvegardé sur disque (`joblib`)

---

## 4. Algorithme Re-weighting Type-1 (Équation 5)

- [x] **Formule rigoureusement implémentée :**
  $$w_i^{(k+1)} = \frac{\varepsilon + \sigma_{Nr, i}^k}{\varepsilon + \sigma_{rel, i}^k}$$
- [x] **Constante de lissage :** $\varepsilon = 0.0001$ exactement
- [x] **$\sigma_{Nr}$ :** calculé sur l'ensemble des $N_r$ images retournées
- [x] **$\sigma_{rel}$ :** calculé uniquement sur les images marquées comme pertinentes
- [x] **Distance :** distance euclidienne pondérée normalisée (Équation 3)
- [x] **Mise à jour de la requête :** $Q_{new} = \text{mean}(X_{rel})$ (centroïde des pertinents)
- [x] **Protection :** remplacement des poids non-finis ou nuls par des valeurs positives sûres

---

## 5. Fonctionnalités et Pages de l'Interface

- [x] **Page 1 — Connexion :** Formulaire moderne, tokens JWT, gestion d'erreurs, compte démo
- [x] **Page 2 — Dashboard :** 4 cartes de statistiques réelles, état de l'index, graphique de distribution par catégorie Recharts, liens rapides
- [x] **Page 3 — Galerie d'images :** Grille responsive, pagination, recherche textuelle, filtre par catégorie, tri, sélection multiple, suppression sécurisée, téléchargement ZIP, modale de détails
- [x] **Page 4 — Gestion des catégories :** Arbre hiérarchique, ajout de catégories/sous-catégories, renommage, suppression avec dissociation des images, comptage d'images
- [x] **Page 5 — Upload d'images :** Drag & drop interactif, téléversement par lot, sélection de catégorie, génération automatique de miniature, indexation
- [x] **Page 6 — Éditeur d'images :** Recadrage avec coordonnées, redimensionnement avec conservation des proportions, rotation 90°, miroirs horizontal et vertical, aperçu avant/après, sauvegarde comme nouvelle image non destructive
- [x] **Page 7 — Descripteurs visuels :** Vue détaillée `/features/:id` avec visualisations graphiques de l'histogramme HSV, tableau des moments, pastilles des couleurs dominantes, tableau GLCM et barre LBP
- [x] **Page 8 — Recherche CBIR & Relevance Feedback :** Choix d'image requête via sélecteur dans la galerie, choix de $K$, affichage des résultats avec badges de rang et distances, boutons trois états (Pertinent / Non pertinent / Neutre), application de Re-weighting Type-1 avec itérations successives, graphique des poids par groupe et courbe Précision/Rappel
- [x] **Page 9 — Analytiques :** Métriques d'évaluation, distribution des images, historique réel des sessions de recherche
- [x] **Page 404 — Not Found :** Page personnalisée aux couleurs de VisionVault

---

## 6. Scripts CLI et Automatisation

- [x] `backend/scripts/import_dataset.py` : Import automatisé des dossiers du dataset GHIM-10K
- [x] `backend/scripts/build_index.py` : Construction de l'index des 93 descripteurs
- [x] `backend/scripts/evaluate_cbir.py` : Script d'évaluation automatique de précision/rappel
- [x] `backend/tests/test_features.py` : Tests unitaires pytest pour tous les descripteurs
- [x] `backend/tests/test_reweighting.py` : Tests unitaires pytest pour l'Équation 5 et les distances

---

## 7. Documentation et Livrables

- [x] `README.md` : Guide d'installation et de démarrage pas à pas sous Windows
- [x] `report/rapport_g11.md` : Rapport académique complet en français
- [x] `docs/architecture.md` : Description de l'architecture logicielle
- [x] `docs/algorithms.md` : Documentation mathématique des algorithmes
- [x] `docs/api.md` : Documentation détaillée des endpoints REST
- [x] `docs/dataset-guide.md` : Guide de structuration du dataset GHIM-10K
- [x] `docs/user-guide.md` : Manuel utilisateur pour la démonstration
- [x] `.gitignore` : Exclusion propre des données lourdes, caches, bases et modules
