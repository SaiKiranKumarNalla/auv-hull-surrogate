"""Benchmark harness: one data loader, one validation split, one set of metrics for every model.

Rules (see notebooks/02_model_benchmark.ipynb):
- train on Vardhan et al.'s 2,400 training hulls, of which 10 % are held out for validation (model choices);
- the 621 test hulls are used once, for the final score only;
- every model is scored with the same metrics, overall and per fineness group.
"""
import csv
import os
import time

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), '..')
DATA = os.path.join(ROOT, 'reference', 'UUV-design-optimization')
RESULTS = os.path.join(ROOT, 'results', 'benchmark.csv')

GROUPS = [(0, 7, 'fat'), (7, 10, 'typical'), (10, 15, 'slender'), (15, 1e9, 'very_slender')]


def load_data():
    """Return (X_train, y_train, X_test, y_test). X columns: a, b, c, d (mm), n, theta (deg); y: drag (N)."""
    train = np.loadtxt(os.path.join(DATA, 'cad_cfd_pipeline_surrogate_data_generation', 'surrogate_data', 'train_2400.txt'))
    test = np.loadtxt(os.path.join(DATA, 'uuv_optim', 'data', 'surrogate', 'test_data.txt'))
    return train[:, :6], train[:, 6], test[:, :6], test[:, 6]


def fineness(X):
    """Length / diameter of each hull."""
    return X[:, :3].sum(axis=1) / X[:, 3]


def train_val_split(n, seed, val_fraction=0.1):
    """Random indices for training and validation; the test set is never touched here."""
    idx = np.random.default_rng(seed).permutation(n)
    n_val = int(round(val_fraction * n))
    return idx[n_val:], idx[:n_val]


def metrics(pred, y, X):
    """Mean absolute percentage error overall and per fineness group, plus the worst single error."""
    err = np.abs(pred - y) / y * 100
    ld = fineness(X)
    out = {'mape': err.mean(), 'max_err': err.max()}
    for lo, hi, name in GROUPS:
        m = (ld >= lo) & (ld < hi)
        out[f'mape_{name}'] = err[m].mean()
    return out


def run(name, fit_predict, seeds=(0, 1, 2, 3, 4), save=True):
    """Train and score one model for each seed.

    fit_predict(X_tr, y_tr, X_val, y_val, X_test, seed) -> predictions on X_test.
    Returns a list of result dicts (one per seed) and appends them to results/benchmark.csv.
    """
    X_train, y_train, X_test, y_test = load_data()
    rows = []
    for seed in seeds:
        tr, va = train_val_split(len(X_train), seed)
        t0 = time.time()
        pred = fit_predict(X_train[tr], y_train[tr], X_train[va], y_train[va], X_test, seed)
        row = {'model': name, 'seed': seed, 'train_seconds': time.time() - t0, **metrics(pred, y_test, X_test)}
        rows.append(row)
        print(f"{name:28s} seed {seed}: {row['mape']:5.2f} %   fat hulls {row['mape_fat']:5.1f} %   ({row['train_seconds']:.1f} s)")
    if save:
        _append(rows)
    return rows


def _append(rows):
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    keep = []
    if os.path.exists(RESULTS):                      # replace earlier rows of the same model
        with open(RESULTS) as f:
            keep = [r for r in csv.DictReader(f) if r['model'] not in {x['model'] for x in rows}]
    fields = list(rows[0].keys())
    with open(RESULTS, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(keep + [{k: (f'{v:.4f}' if isinstance(v, float) else v) for k, v in r.items()} for r in rows])


def summary():
    """Mean ± standard deviation per model from results/benchmark.csv."""
    with open(RESULTS) as f:
        data = list(csv.DictReader(f))
    models = list(dict.fromkeys(r['model'] for r in data))
    cols = ['mape', 'mape_fat', 'mape_typical', 'mape_slender', 'mape_very_slender', 'max_err', 'train_seconds']
    table = {}
    for m in models:
        rs = [r for r in data if r['model'] == m]
        table[m] = {c: (np.mean([float(r[c]) for r in rs]), np.std([float(r[c]) for r in rs])) for c in cols}
    return table
