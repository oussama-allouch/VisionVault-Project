#!/usr/bin/env python3
"""CLI script to build the CBIR feature index for all images.

Usage:
    cd backend
    python scripts/build_index.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

app = create_app()

with app.app_context():
    from app.models.image import Image
    from app.cbir.indexer import FeatureIndex
    from app.extensions import db

    index_folder = app.config['INDEX_FOLDER']
    print(f"[VisionVault] Construction de l'index CBIR")
    print(f"  Dossier index : {index_folder}")
    print()

    images = Image.query.all()
    image_paths_and_ids = [
        (img.stored_path, img.id)
        for img in images
        if os.path.exists(img.stored_path)
    ]

    total = len(image_paths_and_ids)
    print(f"  Images à indexer : {total}")
    if total == 0:
        print("  ERREUR : Aucune image trouvée. Importez d'abord le dataset.")
        print("    python scripts/import_dataset.py")
        sys.exit(1)

    print(f"  Extraction des descripteurs (93 dimensions)...")
    print(f"  Cela peut prendre plusieurs minutes pour {total} images...\n")

    start = time.time()
    index = FeatureIndex(index_folder)
    index.build(image_paths_and_ids)
    duration = time.time() - start

    # Mark all as indexed
    Image.query.update({'is_indexed': True})
    db.session.commit()

    print(f"\n  ✓ Index construit en {duration:.1f} secondes")
    print(f"  Images indexées : {len(index.image_ids)}")
    print(f"  Taille matrice  : {index.normalized_matrix.shape}")
    print(f"  Fichiers sauvegardés dans {index_folder}/")
    print("  ✓ Prêt pour la recherche CBIR.")
