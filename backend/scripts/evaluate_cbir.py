#!/usr/bin/env python3
"""CLI script to evaluate CBIR search quality.

Runs queries for a sample of images and measures precision@K / recall@K
using same-category membership as ground truth.

Usage:
    cd backend
    python scripts/evaluate_cbir.py
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

app = create_app()

with app.app_context():
    from app.models.image import Image
    from app.cbir.indexer import FeatureIndex
    from app.cbir.evaluation import precision_at_k, recall_at_k
    import numpy as np

    index_folder = app.config['INDEX_FOLDER']
    index = FeatureIndex(index_folder)

    try:
        index.load()
    except FileNotFoundError:
        print("ERREUR : Index CBIR non construit. Lancez d'abord :")
        print("  python scripts/build_index.py")
        sys.exit(1)

    print(f"[VisionVault] Évaluation CBIR")
    print(f"  Images dans l'index : {len(index.image_ids)}")

    # Build category mapping
    all_images = Image.query.all()
    id_to_cat = {img.id: img.category_id for img in all_images}
    cat_counts = {}
    for img in all_images:
        if img.category_id:
            cat_counts[img.category_id] = cat_counts.get(img.category_id, 0) + 1

    # Sample queries: pick N random images (at most 5 per category)
    num_queries = min(100, len(index.image_ids))
    query_ids = random.sample(index.image_ids, num_queries)

    K_values = [5, 10, 20, 25, 50]

    print(f"  Nombre de requêtes : {num_queries}")
    print(f"  K values : {K_values}")
    print()

    results = {k: {'precision': [], 'recall': []} for k in K_values}

    start = time.time()
    for i, qid in enumerate(query_ids):
        try:
            query_vec = index.get_features(qid)
            query_cat = id_to_cat.get(qid)
            if not query_cat:
                continue

            total_in_cat = cat_counts.get(query_cat, 0)

            for k in K_values:
                search_results = index.search(query_vec, weights=None, k=k,
                                              exclude_ids={qid})
                result_ids = [r[0] for r in search_results]

                p = precision_at_k(result_ids, query_cat, id_to_cat, k=k)
                r = recall_at_k(result_ids, query_cat, id_to_cat, total_in_cat, k=k)
                results[k]['precision'].append(p)
                results[k]['recall'].append(r)

        except Exception as e:
            print(f"  Warning: query {qid} failed: {e}")

        if (i + 1) % 25 == 0:
            print(f"  Évalué {i + 1} / {num_queries} requêtes...")

    duration = time.time() - start

    print(f"\n=== Résultats (sans Re-weighting, recherche initiale) ===\n")
    print(f"{'K':>5} | {'Précision@K':>12} | {'Rappel@K':>10}")
    print("-" * 35)
    for k in K_values:
        precs = results[k]['precision']
        recs = results[k]['recall']
        if precs:
            avg_p = sum(precs) / len(precs)
            avg_r = sum(recs) / len(recs)
            print(f"{k:>5} | {avg_p:>11.4f} | {avg_r:>9.4f}")
        else:
            print(f"{k:>5} | {'N/A':>11} | {'N/A':>9}")

    print(f"\nTemps total : {duration:.1f} secondes")
    print("Note : Ces métriques sont la baseline sans relevance feedback.")
    print("       Après Re-weighting Type-1, la précision devrait augmenter.")
