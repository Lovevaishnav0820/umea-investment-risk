"""The comparison command accepts the reference results and detects altered results."""
import csv
import json
import shutil
from pathlib import Path
import pytest
from umea_risk.compare import compare, verify_manifest, TABLES

REFERENCE = Path(__file__).resolve().parents[1]/'outputs'
FILES = [*TABLES, 'validation/validation_results.json', 'validation/test_results.json']

@pytest.fixture
def candidate(tmp_path):
    for rel in FILES:
        (tmp_path/rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REFERENCE/rel, tmp_path/rel)
    return tmp_path

def edit_csv(path, key, column, change):
    rows = list(csv.DictReader(open(path, newline='')))
    for row in rows:
        if tuple(row[k] for k in key[0]) == key[1]: row[column] = change(row[column])
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def failures(report):
    return [m for f in report['files'].values() for m in f['failures']]

BASE = (('scenario_id', 'contrast'), ('baseline_sweden_lag6', 'harvest_minus_hold'))

def test_reference_manifest_is_intact():
    assert verify_manifest(REFERENCE) == []

def test_identical_results_pass(candidate):
    report = compare(REFERENCE, candidate)
    assert report['status'] == 'passed', failures(report)
    assert report['files']['tables/contrasts.csv']['stats']['rows'] == 57

def test_rounding_level_difference_passes(candidate):
    edit_csv(candidate/'tables/contrasts.csv', BASE, 'delta_mean', lambda v: repr(float(v) * (1 + 1e-13)))
    assert compare(REFERENCE, candidate)['status'] == 'passed'

@pytest.mark.parametrize('column,change', [
    ('delta_mean', lambda v: repr(float(v) * (1 + 1e-6))),          # estimate
    ('delta_es_ci_low', lambda v: repr(float(v) + 1e-7)),           # interval
    ('triggered_count', lambda v: str(int(v) + 1)),                 # count
    ('es_direction', lambda v: 'positive'),                         # classification
    ('delta_es95', lambda v: 'nan'),                                # nonfinite value
])
def test_altered_contrast_is_detected(candidate, column, change):
    edit_csv(candidate/'tables/contrasts.csv', BASE, column, change)
    report = compare(REFERENCE, candidate)
    assert report['status'] == 'failed'
    assert any(column in m for m in failures(report))

def test_missing_row_is_detected(candidate):
    path = candidate/'tables/scenario_metrics.csv'
    rows = list(csv.DictReader(open(path, newline='')))
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows[:-1])
    report = compare(REFERENCE, candidate)
    assert report['status'] == 'failed' and any('missing row' in m for m in failures(report))

def test_altered_supplementary_result_is_detected(candidate):
    key = (('experiment_id', 'contrast'), ('no_deficit_threshold_500k', 'harvest_minus_hold'))
    edit_csv(candidate/'supplementary/supplementary_contrasts.csv', key, 'delta_es95', lambda v: repr(float(v) - 1e-5))
    assert compare(REFERENCE, candidate)['status'] == 'failed'

def test_altered_validation_count_is_detected(candidate):
    path = candidate/'validation/validation_results.json'
    v = json.loads(path.read_text()); v['counts']['primary_strategy_path_outcomes'] -= 1
    path.write_text(json.dumps(v))
    report = compare(REFERENCE, candidate)
    assert report['status'] == 'failed' and any('primary_strategy_path_outcomes' in m for m in failures(report))

def test_missing_file_is_detected(candidate):
    (candidate/'validation/test_results.json').unlink()
    assert compare(REFERENCE, candidate)['status'] == 'failed'
