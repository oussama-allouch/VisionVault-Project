#!/usr/bin/env python3
"""CLI script to import the GHIM-10K dataset into VisionVault.

Usage:
    cd backend
    python scripts/import_dataset.py
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

app = create_app()

with app.app_context():
    from app.services.dataset_service import DatasetService
    dataset_path = app.config['DATASET_PATH']

    print(f"[VisionVault] Import du dataset GHIM-10K")
    print(f"  Chemin : {dataset_path}")
    print()

    if not os.path.isdir(dataset_path):
        print(f"ERREUR : Le dossier dataset n'existe pas : {dataset_path}")
        print("Veuillez télécharger GHIM-10K depuis Kaggle et le placer dans data/GHIM-10K/")
        sys.exit(1)

    start = time.time()
    stats = DatasetService.import_dataset(dataset_path)
    duration = time.time() - start

    print(f"  ✓ Import terminé en {duration:.1f} secondes")
    print(f"  Catégories traitées : {stats['categories_created']}")
    print(f"  Images importées    : {stats['images_imported']}")
    print(f"  Images ignorées     : {stats['images_skipped']}")
    print(f"  Erreurs             : {stats['errors']}")
    print()

    # Print summary
    from app.models.image import Image
    from app.models.category import Category
    total = Image.query.count()
    cats = Category.query.count()
    print(f"  Base de données : {total} images, {cats} catégories")
    print("  ✓ Prêt pour la construction de l'index CBIR.")
