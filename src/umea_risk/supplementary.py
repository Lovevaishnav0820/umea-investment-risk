"""Supplementary analysis: starting-wealth sweep and a no-threshold counterfactual.

These experiments reuse the primary standard-normal innovations and the primary bootstrap
index matrix. They are reported separately and do not change the 19 primary configurations.
"""
from pathlib import Path
import numpy as np
from .config import STRATEGIES, supplementary_experiments
from .scenarios import prices_from_innovations
from .vector import run_vector
from .metrics import scenario_statistics, compact
from .io import write_csv, save_arrays
from .tax import DEFICIT_THRESHOLD_SEK

def run_supplementary(out, c, z, indices, baseline):
    """Run every supplementary experiment and return (arm rows, contrast rows, array records).

    baseline holds the compact primary baseline results; the 500,000 SEK Swedish-rule
    experiment repeats the baseline configuration and must reproduce it exactly.
    """
    out = Path(out); arms = []; contrasts = []; records = []
    for e in supplementary_experiments(c):
        p = e['parameters']; W0 = p['initial_wealth_sek']
        prices = prices_from_innovations(z, p); engines = {}; over = {}
        print(f"Supplementary {e['id']}: 3 strategies x {len(z):,} paths, {len(indices):,} paired bootstrap draws", flush=True)
        for strategy in STRATEGIES:
            v = run_vector(prices, p, strategy)
            engines[strategy] = compact(v, W0)
            # Paths with a capital deficit (70% of a net loss) above 100,000 SEK in at least one tax year.
            over[strategy] = int(np.count_nonzero((-0.7 * v.annual_g > DEFICIT_THRESHOLD_SEK).any(axis=1))) if v.ad else None
            record = save_arrays(out/f"arrays/supplementary/{e['id']}__{strategy}.npz", W=v.W, net_return=v.net_return,
                                 harvested=v.s['harvested'], F=v.s['F'], fees_total=v.s['fees_total'],
                                 annual_net_gains=v.annual_g)
            record['file'] = str(Path(record['file']).relative_to(out)); records.append(record)
            del v
        if p == c['baseline']:
            for strategy in STRATEGIES:
                if not np.array_equal(engines[strategy].net_return, baseline[strategy].net_return):
                    raise AssertionError(f"Supplementary {e['id']} does not reproduce the primary baseline for {strategy}")
        arm, delta, boot, _ = scenario_statistics(e['id'], engines, indices, c['contrasts'])
        record = save_arrays(out/f"arrays/supplementary/{e['id']}__bootstrap.npz", **boot)
        record['file'] = str(Path(record['file']).relative_to(out)); records.append(record)
        for row in arm:
            row.pop('scenario_id')
            arms.append(dict(experiment_id=e['id'], experiment_role=e['role'], initial_wealth_sek=W0, tax_mode=p['tax_mode'], **row,
                             paths_with_annual_deficit_over_100k=over[row['strategy']]))
        for row in delta:
            row.pop('scenario_id')
            row = dict(experiment_id=e['id'], experiment_role=e['role'], initial_wealth_sek=W0, tax_mode=p['tax_mode'], **row)
            for k in ('delta_mean', 'delta_mean_ci_low', 'delta_mean_ci_high', 'delta_es95', 'delta_es_ci_low', 'delta_es_ci_high'):
                row[k + '_sek'] = row[k] * W0
            contrasts.append(row)
    write_csv(out/'supplementary/supplementary_metrics.csv', arms)
    write_csv(out/'supplementary/supplementary_contrasts.csv', contrasts)
    return arms, contrasts, records
