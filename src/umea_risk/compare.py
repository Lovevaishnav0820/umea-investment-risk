"""Compare a reproduction with the reference results in outputs/.

Rows are matched by identifiers. Identifiers, labels and counts must agree exactly. Floating-point
values agree when |a - b| <= atol + rtol * max(|a|, |b|):

* rtol = 1e-9 for every floating-point column.
* atol = 1e-12 for returns, losses, probabilities and ratios (decimal fractions);
  atol = 1e-6 for columns in SEK.

Justification: the same code run on two platforms differs only through floating-point rounding
(for example in exp/log and in summation order). Between the earlier macOS arm64 run and a Linux
x86-64 run of this study, the largest relative difference in any table cell was below 1e-13.
The tolerances sit several orders of magnitude above that rounding level and far below the
precision at which results are reported (three decimals of a percentage, i.e. 1e-5 as a fraction),
so any change that could alter a reported digit is flagged.

Validation results are compared by status and by counts (exactly). Measured residuals are
platform-dependent, so they are checked against their acceptance bounds rather than against the
reference values; statistical diagnostics are compared with rtol = 1e-6.

File hashes (artifact_manifest.json) verify that the reference files themselves are intact.
Raw floating-point array hashes are not expected to agree across platforms.
"""
import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

RTOL = 1e-9
ATOL_FRACTION = 1e-12
ATOL_SEK = 1e-6
DIAGNOSTIC_RTOL = 1e-6
DIAGNOSTIC_ATOL = 1e-9

TABLES = {
    'tables/scenario_metrics.csv': ('scenario_id', 'strategy'),
    'tables/contrasts.csv': ('scenario_id', 'contrast'),
    'supplementary/supplementary_metrics.csv': ('experiment_id', 'strategy'),
    'supplementary/supplementary_contrasts.csv': ('experiment_id', 'contrast'),
}
TEXT_COLUMNS = {'scenario_id', 'experiment_id', 'strategy', 'contrast', 'arm_a', 'arm_b', 'role', 'experiment_role', 'tax_mode',
                'mean_direction', 'es_direction'}
INTEGER_COLUMNS = {'n_paths', 'count_loss', 'count_nonpositive_W', 'count_funding', 'harvest_count', 'triggered_count',
                   'paths_with_annual_deficit_over_100k'}

# Measured residuals and errors: the candidate must satisfy the acceptance bound.
ACCEPTANCE_BOUNDS = {
    'max_normalized_identity_error': 1., 'max_normalized_error': 1., 'maximum_absolute_residual_sek': 1e-6,
    'max_pairwise_abs_W_difference_sek': 1e-6, 'max_absolute_es_difference': 1e-12,
    'max_absolute_standardized_discrepancy': 6., 'max_mean_difference_in_combined_standard_errors': 6.,
}
TOLERANCE_COMPARED = {'max_absolute_standardized_discrepancy', 'max_mean_difference_in_combined_standard_errors'}

REFERENCE_FILES = [
    'note/research_note.pdf', 'note/research_appendix.pdf', 'note/research_note.md',
    *[f'figures/{stem}.{ext}' for stem in ('figure1_tax_and_lag', 'figure2_paired_difference',
                                           'figure3_wealth_threshold', 'figure4_return_models') for ext in ('png', 'pdf')],
    'tables/scenario_metrics.csv', 'tables/contrasts.csv', 'tables/table1_baseline.md', 'tables/table2_sensitivity.md',
    'supplementary/supplementary_metrics.csv', 'supplementary/supplementary_contrasts.csv',
    'supplementary/table_s1_wealth_threshold.md',
    'validation/validation_results.json', 'validation/artifact_validation.json', 'validation/test_results.json',
    'metadata/run_metadata.json',
]

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while block := f.read(1 << 20): h.update(block)
    return h.hexdigest()

def write_manifest(directory):
    directory = Path(directory)
    files = sorted(p for p in directory.rglob('*') if p.is_file() and p.name != 'artifact_manifest.json'
                   and not any(x in p.parts for x in ('logs', 'cache')))
    manifest = dict(description='SHA-256 hashes of the files in this directory; they verify file integrity only.',
                    files=[dict(path=p.relative_to(directory).as_posix(), bytes=p.stat().st_size, sha256=sha256(p)) for p in files])
    (directory/'metadata').mkdir(parents=True, exist_ok=True)
    (directory/'metadata/artifact_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest

def verify_manifest(directory):
    """Return a list of problems; an empty list means every listed file is present and unchanged."""
    directory = Path(directory); path = directory/'metadata/artifact_manifest.json'
    if not path.exists(): return [f'missing {path}']
    problems = []
    for item in json.loads(path.read_text())['files']:
        p = directory/item['path']
        if not p.exists(): problems.append(f"missing {item['path']}")
        elif sha256(p) != item['sha256']: problems.append(f"changed {item['path']}")
    return problems

def publish_reference(source, destination):
    """Copy the reference subset of a complete run into destination and write its manifest."""
    source, destination = Path(source), Path(destination)
    for rel in REFERENCE_FILES:
        target = destination/rel; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source/rel, target)
    return write_manifest(destination)

def _number(text, where, failures):
    try: x = float(text)
    except ValueError:
        failures.append(f'{where}: not a number: {text!r}'); return None
    if not math.isfinite(x):
        failures.append(f'{where}: nonfinite value {text!r}'); return None
    return x

def compare_table(reference_path, candidate_path, keys):
    failures = []; stats = dict(rows=0, cells=0, max_abs_diff=0., max_rel_diff=0., worst=None)
    ref = list(csv.DictReader(open(reference_path, newline='')))
    cand = list(csv.DictReader(open(candidate_path, newline='')))
    if not ref: failures.append('reference table is empty')
    if ref and cand and list(ref[0].keys()) != list(cand[0].keys()):
        failures.append(f'columns differ: missing {sorted(set(ref[0]) - set(cand[0]))}, extra {sorted(set(cand[0]) - set(ref[0]))}')
        return failures, stats
    def index(rows, label):
        out = {}
        for r in rows:
            k = tuple(r[c] for c in keys)
            if k in out: failures.append(f'{label}: duplicate row {k}')
            out[k] = r
        return out
    R, C = index(ref, 'reference'), index(cand, 'candidate')
    for k in R.keys() - C.keys(): failures.append(f'missing row {k}')
    for k in C.keys() - R.keys(): failures.append(f'unexpected row {k}')
    if [tuple(r[c] for c in keys) for r in ref] != [tuple(r[c] for c in keys) for r in cand] and not (R.keys() ^ C.keys()):
        failures.append('row order differs')
    for k in sorted(R.keys() & C.keys()):
        stats['rows'] += 1
        for col, a in R[k].items():
            b = C[k][col]; where = f'{k}/{col}'; stats['cells'] += 1
            if col in TEXT_COLUMNS:
                if a != b: failures.append(f'{where}: {a!r} != {b!r}')
                continue
            if a == '' or b == '':
                if a != b: failures.append(f'{where}: empty/non-empty mismatch {a!r} vs {b!r}')
                continue
            x, y = _number(a, where + ' (reference)', failures), _number(b, where + ' (candidate)', failures)
            if x is None or y is None: continue
            if col in INTEGER_COLUMNS:
                if x != y: failures.append(f'{where}: count {a} != {b}')
                continue
            atol = ATOL_SEK if col.endswith('_sek') else ATOL_FRACTION
            d = abs(x - y); rel = d / max(abs(x), abs(y)) if d else 0.
            if d > stats['max_abs_diff']: stats['max_abs_diff'] = d; stats['worst'] = dict(row=list(k), column=col, reference=a, candidate=b)
            stats['max_rel_diff'] = max(stats['max_rel_diff'], rel)
            if d > atol + RTOL * max(abs(x), abs(y)): failures.append(f'{where}: {a} vs {b} (difference {d:.3g})')
    return failures, stats

def _compare_values(ref, cand, where, failures, stats):
    if isinstance(ref, bool) or isinstance(ref, str) or ref is None:
        if ref != cand: failures.append(f'{where}: {ref!r} != {cand!r}')
    elif isinstance(ref, int):
        if ref != cand: failures.append(f'{where}: count {ref} != {cand}')
    elif isinstance(ref, float):
        if not isinstance(cand, (int, float)) or not math.isfinite(cand):
            failures.append(f'{where}: invalid candidate value {cand!r}'); return
        key = where.rsplit('.', 1)[-1]
        if key in ACCEPTANCE_BOUNDS:
            if cand > ACCEPTANCE_BOUNDS[key]: failures.append(f'{where}: {cand} exceeds acceptance bound {ACCEPTANCE_BOUNDS[key]}')
            stats['acceptance_checked'] += 1
            if key not in TOLERANCE_COMPARED: return
        d = abs(ref - cand); stats['max_diagnostic_abs_diff'] = max(stats['max_diagnostic_abs_diff'], d)
        if d > DIAGNOSTIC_ATOL + DIAGNOSTIC_RTOL * max(abs(ref), abs(cand)): failures.append(f'{where}: {ref} vs {cand}')
    elif isinstance(ref, dict):
        for k, v in ref.items():
            if k not in cand: failures.append(f'{where}.{k}: missing'); continue
            _compare_values(v, cand[k], f'{where}.{k}', failures, stats)
    elif isinstance(ref, list):
        if not isinstance(cand, list) or len(ref) != len(cand): failures.append(f'{where}: list length differs'); return
        for i, (a, b) in enumerate(zip(ref, cand)): _compare_values(a, b, f'{where}[{i}]', failures, stats)

def compare_validation(reference_path, candidate_path):
    ref = json.loads(Path(reference_path).read_text()); cand = json.loads(Path(candidate_path).read_text())
    failures = []; stats = dict(acceptance_checked=0, max_diagnostic_abs_diff=0.)
    if cand.get('status') != 'passed': failures.append(f"candidate status {cand.get('status')!r}")
    _compare_values(ref['counts'], cand.get('counts', {}), 'counts', failures, stats)
    rp = {p['id']: p for p in ref['property_tests']}; cp = {p['id']: p for p in cand.get('property_tests', [])}
    for k in rp.keys() ^ cp.keys(): failures.append(f'property test set differs: {k}')
    for k in rp.keys() & cp.keys():
        _compare_values(rp[k], cp[k], f'property_tests.{k}', failures, stats)
    for i, (a, b) in enumerate(zip(ref['price_moments'], cand.get('price_moments', []))):
        for j, (x, y) in enumerate(zip(a['checks'], b['checks'])):
            if y['status'] != 'passed': failures.append(f'price_moments[{i}].{y["id"]}: {y["status"]}')
            _compare_values(x['standardized_discrepancy'], y['standardized_discrepancy'], f'price_moments[{i}][{j}].standardized_discrepancy', failures, stats)
    return failures, stats

def compare_tests(reference_path, candidate_path):
    ref = json.loads(Path(reference_path).read_text()); cand = json.loads(Path(candidate_path).read_text())
    return [f'test_results.{k}: {ref[k]!r} != {cand.get(k)!r}' for k in ref if ref[k] != cand.get(k)], {}

def compare(reference, candidate):
    reference, candidate = Path(reference), Path(candidate)
    report = dict(reference=str(reference), candidate=str(candidate),
                  tolerances=dict(rtol=RTOL, atol_fraction=ATOL_FRACTION, atol_sek=ATOL_SEK,
                                  diagnostic_rtol=DIAGNOSTIC_RTOL, diagnostic_atol=DIAGNOSTIC_ATOL), files={})
    jobs = [(rel, compare_table, keys) for rel, keys in TABLES.items()]
    jobs += [('validation/validation_results.json', compare_validation, None), ('validation/test_results.json', compare_tests, None)]
    for rel, fn, keys in jobs:
        a, b = reference/rel, candidate/rel
        if not a.exists() or not b.exists():
            report['files'][rel] = dict(failures=[f'missing file: {a if not a.exists() else b}'], stats={}); continue
        failures, stats = fn(a, b, keys) if keys else fn(a, b)
        report['files'][rel] = dict(failures=failures, stats=stats)
    report['status'] = 'passed' if not any(f['failures'] for f in report['files'].values()) else 'failed'
    return report

def summary(report):
    lines = [f"Comparison of {report['candidate']} with {report['reference']}: {report['status'].upper()}"]
    for rel, f in report['files'].items():
        s = f['stats']
        if 'cells' in s:
            lines.append(f"  {rel}: {s['rows']} rows, {s['cells']} cells, max |diff| {s['max_abs_diff']:.3g}, max relative diff {s['max_rel_diff']:.3g}")
        elif 'acceptance_checked' in s:
            lines.append(f"  {rel}: counts and statuses compared, {s['acceptance_checked']} acceptance bounds checked, max diagnostic |diff| {s['max_diagnostic_abs_diff']:.3g}")
        else:
            lines.append(f'  {rel}: compared')
        for msg in f['failures'][:10]: lines.append(f'    FAIL {msg}')
        if len(f['failures']) > 10: lines.append(f"    ... {len(f['failures']) - 10} more")
    return '\n'.join(lines)

def main(argv=None):
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description='Compare a reproduction with the reference results.')
    parser.add_argument('--reference', type=Path, default=root/'outputs')
    parser.add_argument('--candidate', type=Path, default=root/'reproduction')
    parser.add_argument('--report', type=Path, help='where to write the JSON report (default: CANDIDATE/validation/comparison_report.json)')
    args = parser.parse_args(argv)
    report = compare(args.reference, args.candidate)
    path = args.report or args.candidate/'validation/comparison_report.json'
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2) + '\n')
    print(summary(report)); print(f'Report: {path}')
    return 0 if report['status'] == 'passed' else 1

if __name__ == '__main__':
    sys.exit(main())
