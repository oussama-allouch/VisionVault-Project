# Référence de l’API VisionVault

Préfixe `/api/v1`. Les réponses sont JSON sauf les fichiers. Les routes protégées demandent `Authorization: Bearer <access_token>`. La galerie est partagée entre comptes autorisés. Les recherches, le feedback et les informations d’activité sont rattachés au compte. Les opérations de corpus et de reconstruction exigent un administrateur.

| Méthode et route | Données ou comportement |
|---|---|
| POST `/auth/login` | `email`, `password`. Retourne le compte et les JWT d’accès et de rafraîchissement. |
| POST `/auth/refresh` | Utilise le JWT de rafraîchissement dans l’en-tête. |
| POST `/auth/register` | `email`, `password`. Désactivé par défaut. |
| GET `/auth/me`, POST `/auth/logout` | Compte actif et révocation de la famille JWT dans SQLite. |
| GET `/images` | Pagination `page`, `per_page` 1–100, `category_id`, `search`, `sort_by`, `sort_order`. |
| POST `/images`, `/images/bulk-upload` | Multipart `file` ou `files` répété, `category_id` facultatif. Le lot retourne un statut par fichier. |
| GET/DELETE `/images/{id}` | Détails ou suppression de l’entrée. L’original d’un corpus importé est conservé sur disque. |
| GET `/images/{id}/media/original` et `/media/thumbnail` | Fichier autorisé à l’intérieur du dossier géré. |
| GET `/images/{id}/download` | Original en pièce jointe. |
| POST `/images/bulk-download`, `/images/bulk-delete` | `ids` uniques (1–100). Téléchargement ZIP ou nombre de suppressions. |
| POST `/images/{id}/move` | `category_id` valide ou `null`. |
| GET/POST `/categories` | Arborescence ou création avec `name` et `parent_id` facultatif. |
| GET/PATCH/DELETE `/categories/{id}` | Détail, modification de nom ou de parent, suppression avec promotion des enfants. |
| POST `/images/{id}/crop` | `x`, `y`, `width`, `height` entiers, dans l’image orientée. |
| POST `/images/{id}/resize` | `width` et/ou `height`, `maintain_aspect` booléen. |
| POST `/images/{id}/transform` | Liste `operations`, p. ex. `[{"type":"rotate","angle":90}]`. |
| GET `/images/{id}/features` | Les cinq familles, avec vecteur brut de 93 composantes. |
| POST `/images/features/batch` | `ids` uniques (1–32), résultat par image. |
| GET `/images/{id}/{descriptor}` | `color-histogram`, `color-moments`, `dominant-colors`, `glcm`, `lbp`. |
| POST `/cbir/search` | `query_image_id`, `num_results` 1–100. Réponse avec session, rangs, distances et métriques si catégorie disponible. |
| POST `/cbir/search/upload` | Multipart `file` et `num_results`. Recherche externe, sans métriques de catégorie. |
| POST `/cbir/feedback` | `session_id`, `iteration`, `num_results`, `relevant_ids`, `non_relevant_ids`. IDs du dernier classement, distincts et sans conflit. |
| GET/DELETE `/cbir/sessions/{id}`, GET `/cbir/sessions/{id}/history` | Historique de la session du compte actif. |
| POST `/index/import`, `/index/rebuild`, GET `/index/status` | Import, reconstruction et état de l’index. |
| GET `/index/health` | Contrôle de disponibilité public local. |
| GET `/analytics/overview`, `/analytics/evaluation` | Résumé de la galerie et activité du compte. |

Une itération obsolète ou un résultat supprimé depuis le classement entraîne une réponse 409. Un label invalide ou un retour sans positif entraîne une réponse 400. Une session appartenant à un autre utilisateur renvoie 404.
