#!/usr/bin/env python3
"""Reproduce the study without modifying the reference results in outputs/.

Steps: verify the reference files against their manifest, run the tests, run the complete study
(19 configurations and the supplementary analysis) into a separate directory, validate the
generated files, compare them with the reference results, and confirm that outputs/ is unchanged.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT/'outputs'
sys.path.insert(0, str(ROOT/'src'))
from umea_risk.compare import verify_manifest  # noqa: E402

def save_test_summary(out):
    suites = ET.parse(out/'validation/tests.xml').getroot().findall('testsuite')
    counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
    report = dict(status='passed' if counts['failures'] == counts['errors'] == 0 else 'failed', **counts)
    (out/'validation/test_results.json').write_text(json.dumps(report, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', type=Path, default=ROOT/'reproduction', help='directory for generated results (default: reproduction/)')
    out = parser.parse_args().output.resolve()
    if out == REFERENCE.resolve(): parser.error('outputs/ holds the reference results; choose another directory')
    problems = verify_manifest(REFERENCE)
    if problems: raise SystemExit(f'Reference results in outputs/ do not match their manifest: {problems[:5]}')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT/'src'), MPLCONFIGDIR=str(out/'cache/matplotlib'), TZ='UTC')
    for sub in ('validation', 'logs'): (out/sub).mkdir(parents=True, exist_ok=True)
    tests = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--junitxml=' + str(out/'validation/tests.xml')],
                           cwd=ROOT, env=env, text=True, capture_output=True)
    (out/'logs/pytest.log').write_text(tests.stdout + tests.stderr); print(tests.stdout, flush=True)
    save_test_summary(out)
    if tests.returncode: raise SystemExit(f'Tests failed; see {out}/logs/pytest.log')
    run = subprocess.Popen([sys.executable, '-m', 'umea_risk.study', '--output', str(out)], cwd=ROOT, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    with (out/'logs/study.log').open('w') as stream:
        for line in run.stdout: print(line, end='', flush=True); stream.write(line); stream.flush()
    if run.wait(): raise SystemExit(f'Study failed; see {out}/logs/study.log and {out}/validation/failure.json')
    subprocess.run([sys.executable, '-m', 'umea_risk.artifacts', str(out)], cwd=ROOT, env=env, check=True)
    comparison = subprocess.run([sys.executable, '-m', 'umea_risk.compare', '--reference', str(REFERENCE), '--candidate', str(out)],
                                cwd=ROOT, env=env)
    problems = verify_manifest(REFERENCE)
    if problems: raise SystemExit(f'Reference results in outputs/ changed during reproduction: {problems[:5]}')
    print('Reference results in outputs/ are unchanged (all manifest hashes verified).')
    if comparison.returncode: raise SystemExit('The reproduction differs from the reference results; see the comparison report.')

if __name__ == '__main__':
    main()
