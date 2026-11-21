#!/usr/bin/env python3
"""Reproducible GHIM-10K evaluation using the production ranker and feedback."""

import argparse
import csv
import json
import os
import platform
import random
import sys
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path
from statistics import mean, median
from time import perf_counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.cbir.feature_extractor import FEATURE_GROUPS
from app.cbir.reweighting_type1 import apply_feedback
from app.cbir.search_engine import _get_index
from app.models.image import Image
from app.services.dataset_service import dataset_files

K_VALUES = (5, 10, 20, 25, 50)
ITERATIONS = 5


def evaluate(index, labels, filenames, queries):
    counts = Counter(labels.values())
    for query_id in queries:
        label = labels[query_id]
        eligible = counts[label] - 1
        query = index.get_features(query_id)
        for k in K_VALUES:
            seen_positives = set()
            previous = []
            weights = [1.0] * len(query)
            for iteration in range(ITERATIONS + 1):
                started = perf_counter()
                positives = [i for i, _ in previous if labels[i] == label]
                applied = iteration > 0 and bool(positives)
                if iteration == 0:
                    ranked = index.search(query, k=k, exclude_ids={query_id})
                elif applied:
                    negative = [i for i, _ in previous if labels[i] != label]
                    state = {'retrieved_ids': [i for i, _ in previous],
                             'query_image_id': query_id, 'iteration': iteration - 1}
                    feedback = apply_feedback(index, state, positives, negative, k)
                    ranked, weights = feedback['results'], feedback['weights'].tolist()
                else:
                    ranked = previous
                elapsed = (perf_counter() - started) * 1000 if iteration == 0 or applied else None
                seen_positives.update(positives)
                hits = 0
                average_precision = 0.0
                new_hits = 0
                for rank, (image_id, _) in enumerate(ranked, 1):
                    if labels[image_id] == label:
                        hits += 1
                        average_precision += hits / rank
                        new_hits += image_id not in seen_positives
                metrics = {
                    'query_id': query_id, 'filename': filenames[query_id], 'category': label,
                    'k': k, 'iteration': iteration, 'precision': hits / len(ranked) if ranked else 0,
                    'recall': hits / eligible if eligible else 0,
                    'ap_at_k': average_precision / min(eligible, k) if eligible else 0,
                    'eligible_relevant': eligible, 'relevant': hits, 'new_relevant': new_hits,
                    'previously_labelled_relevant': hits - new_hits,
                    'feedback_applied': applied, 'no_positive': iteration > 0 and not positives,
                    'ranking_unchanged': iteration > 0 and [i for i, _ in previous] == [i for i, _ in ranked],
                    'latency_ms': elapsed,
                }
                yield metrics, {'query_id': query_id, 'k': k, 'iteration': iteration,
                                'ranking': ranked, 'weights': weights, 'positives': positives}
                previous = ranked


def aggregate(rows, fields):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[f] for f in fields)].append(row)
    result = []
    for key, values in sorted(grouped.items()):
        times = [v['latency_ms'] for v in values if v['latency_ms'] is not None]
        result.append({**dict(zip(fields, key)), 'queries': len(values),
                       **{f'mean_{f}': mean(v[f] for v in values) for f in
                          ('precision', 'recall', 'ap_at_k', 'new_relevant',
                           'previously_labelled_relevant')},
                       'mean_latency_ms': mean(times) if times else None,
                       'median_latency_ms': median(times) if times else None,
                       'no_positive': sum(v['no_positive'] for v in values),
                       'ranking_unchanged': sum(v['ranking_unchanged'] for v in values)})
    return result


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def plot_results(folder, summary, categories, example):
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.grid': True, 'grid.alpha': .24})
    main = [r for r in summary if r['k'] == 25]
    stages = range(ITERATIONS + 1)
    before = [r for r in summary if r['iteration'] == 0]
    after = [r for r in summary if r['iteration'] == ITERATIONS]

    def save(filename, title, xlabel, ylabel):
        plt.title(title, loc='left', pad=14)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.tight_layout()
        plt.savefig(folder / filename, dpi=185)
        plt.close()

    for metric, label in [('precision', 'Précision'), ('recall', 'Rappel')]:
        plt.figure(figsize=(7.2, 3.8))
        for k in K_VALUES:
            rows = [r for r in summary if r['k'] == k]
            plt.plot(stages, [100 * r[f'mean_{metric}'] for r in rows], 'o-', label=f'K = {k}')
        plt.ylim(0, 100 if metric == 'precision' else max(
            1, 100 * max(r['mean_recall'] for r in summary) * 1.15))
        plt.legend(ncol=3)
        save(f'{metric}_iterations.png', f'{label} par itération', 'Itération', f'{label} (%)')
    plt.figure(figsize=(7.2, 3.8))
    for rows, label in [(before, 'Itération 0'), (after, 'Itération 5')]:
        plt.plot(K_VALUES, [100 * r['mean_precision'] for r in rows], 'o-', label=label)
    plt.ylim(0, 100)
    plt.legend()
    save('precision_k.png', 'Précision avant et après retour', 'K', 'Précision (%)')

    plt.figure(figsize=(7.2, 3.8))
    for rows, label in [(before, 'Itération 0'), (after, 'Itération 5')]:
        plt.plot([100 * r['mean_recall'] for r in rows], [100 * r['mean_precision'] for r in rows], 'o-', label=label)
        for r in rows:
            plt.annotate(str(r['k']), (100*r['mean_recall'], 100*r['mean_precision']), xytext=(4, 4), textcoords='offset points')
    plt.xlim(left=0)
    plt.ylim(0, 100)
    plt.legend()
    save('precision_rappel.png', 'Relation précision–rappel pour cinq valeurs de K', 'Rappel (%)', 'Précision (%)')

    plt.figure(figsize=(8.4, 4))
    cat_before = [r for r in categories if r['k'] == 25 and r['iteration'] == 0]
    cat_after = [r for r in categories if r['k'] == 25 and r['iteration'] == ITERATIONS]
    x = list(range(len(cat_before)))
    for offset, rows, label in [(-.2, cat_before, 'Itération 0'), (.2, cat_after, 'Itération 5')]:
        plt.bar([v+offset for v in x], [100*r['mean_precision'] for r in rows], width=.4, label=label)
    plt.xticks(x, [r['category'].removeprefix('Classe ') for r in cat_before], rotation=45)
    plt.ylim(0, 100)
    plt.legend()
    save('categories.png', 'Précision par classe à K = 25', 'Classe GHIM-10K', 'Précision (%)')

    plt.figure(figsize=(7.2, 3.8))
    for label, key in [('Moyenne', 'mean_latency_ms'), ('Médiane', 'median_latency_ms')]:
        plt.plot(stages, [r[key] for r in main], 'o-', label=label)
    plt.ylim(bottom=0)
    plt.legend()
    save('latence.png', 'Latence de calcul à K = 25', 'Itération', 'Millisecondes')

    plt.figure(figsize=(7.2, 3.8))
    for name, (start, end) in FEATURE_GROUPS.items():
        plt.plot(stages, [mean(r['weights'][start:end]) for r in example], 'o-', label=name.replace('_',' '))
    plt.yscale('log')
    plt.legend(ncol=2, fontsize=8)
    save('poids.png', 'Poids par famille pour une requête', 'Itération', 'Poids moyen (échelle logarithmique)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261121)
    parser.add_argument('--per-category', type=int, default=5)
    parser.add_argument('--dataset-revision', default=None)
    args = parser.parse_args()
    if args.per_category < 5:
        parser.error('Au moins cinq requêtes par catégorie sont requises.')
    output = args.output
    for name in ('csv', 'json', 'figures'):
        (output / name).mkdir(parents=True, exist_ok=True)
    started = perf_counter()
    app = create_app()
    with app.app_context():
        image_paths = {str(path): label for label, path in dataset_files(Path(app.config['DATASET_PATH']))}
        images = Image.query.filter_by(source_type='dataset').order_by(Image.id).all()
        index = _get_index()
        labels = {image.id: image_paths[image.stored_path] for image in images
                  if image.id in index.rows and image.stored_path in image_paths}
        filenames = {image.id: image.filename for image in images}
        if (set(labels) != set(index.image_ids) or len(set(labels.values())) != 20
                or len(labels) < 9500):
            parser.error('Utilisez une base GHIM-10K complète et dédiée à l’expérience.')
    grouped = defaultdict(list)
    for image_id, label in labels.items():
        grouped[label].append(image_id)
    rng = random.Random(args.seed)
    queries = [i for _, members in sorted(grouped.items()) for i in rng.sample(members, args.per_category)]
    print(f'{len(labels)} images, {len(grouped)} classes, {len(queries)} requêtes', flush=True)
    rows, raw = [], []
    for row, detail in evaluate(index, labels, filenames, queries):
        rows.append(row)
        raw.append(detail)
        if len(rows) % (25 * len(K_VALUES) * (ITERATIONS + 1)) == 0:
            print(f'{len(rows) // (len(K_VALUES) * (ITERATIONS+1))} requêtes terminées', flush=True)
    summary = aggregate(rows, ('k', 'iteration'))
    categories = aggregate(rows, ('category', 'k', 'iteration'))
    first = queries[0]
    example = [detail for detail in raw if detail['query_id'] == first and detail['k'] == 25]
    plot_results(output / 'figures', summary, categories, example)

    def write_json(filename, content):
        (output / 'json' / filename).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')

    for name, records in [('par_requete', rows), ('synthese', summary), ('par_categorie', categories)]:
        write_csv(output / 'csv' / f'{name}.csv', records)
        write_json(f'{name}.json', records)
    with (output / 'json' / 'classements_et_poids.jsonl').open('w', encoding='utf-8') as stream:
        for detail in raw:
            stream.write(json.dumps(detail) + '\n')
    write_json('config.json', {'seed': args.seed, 'per_category': args.per_category, 'k': K_VALUES,
                               'iterations': ITERATIONS, 'dataset_revision': args.dataset_revision,
                               'dataset_images_indexed': len(labels), 'category_counts': dict(Counter(labels.values())),
                               'query_ids': queries, 'weight_example_id': first,
                               'environment': {'python': platform.python_version(), 'system': platform.platform(),
                                               'processor': platform.processor(), 'logical_cores': os.cpu_count(),
                                               'packages': {p: version(p) for p in ('numpy','scikit-learn','scikit-image','Pillow','opencv-python-headless')}},
                               'duration_seconds': perf_counter() - started})
    print('Évaluation terminée.', flush=True)


if __name__ == '__main__':
    main()
