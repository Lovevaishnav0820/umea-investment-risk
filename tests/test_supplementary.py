"""Properties of the supplementary starting-wealth and no-threshold experiments."""
import numpy as np
from umea_risk.config import BASELINE, load_config, supplementary_experiments
from umea_risk.scenarios import generate_innovations, prices_from_innovations
from umea_risk.tax import annual_ad_tax
from umea_risk.vector import run_vector

Z = generate_innovations()[:200]

def returns(**overrides):
    p = dict(BASELINE, **overrides)
    prices = prices_from_innovations(Z, p)
    return {s: run_vector(prices, p, s).net_return for s in ('AD_HOLD', 'AD_HARVEST')}

def test_experiment_list():
    e = supplementary_experiments(load_config())
    assert [x['parameters']['initial_wealth_sek'] for x in e if x['role'] == 'starting_wealth'] == \
        [100000., 200000., 300000., 400000., 500000., 750000., 1000000., 2000000.]
    cf = [x for x in e if x['role'] == 'counterfactual_tax_schedule']
    assert len(cf) == 1 and cf[0]['parameters'] == dict(BASELINE, tax_mode='sweden2026_no_deficit_threshold')

def test_no_threshold_schedule_is_proportional():
    g = np.array([-1e3, -2e5, -1e6, 5e4])
    assert np.allclose(annual_ad_tax(10 * g, mode='sweden2026_no_deficit_threshold'),
                       10 * annual_ad_tax(g, mode='sweden2026_no_deficit_threshold'), rtol=1e-15, atol=0)
    assert annual_ad_tax(-1e6, mode='sweden2026_no_deficit_threshold') == -210000.

def test_depå_returns_do_not_depend_on_wealth_without_threshold():
    a = returns(initial_wealth_sek=100000., tax_mode='sweden2026_no_deficit_threshold')
    b = returns(initial_wealth_sek=2000000., tax_mode='sweden2026_no_deficit_threshold')
    for s in a: np.testing.assert_allclose(a[s], b[s], rtol=0, atol=1e-12)

def test_threshold_cannot_bind_at_100k():
    # A raw loss of at most 100,000 SEK gives a deficit of at most 70,000 SEK, below the threshold.
    a = returns(initial_wealth_sek=100000.)
    b = returns(initial_wealth_sek=100000., tax_mode='sweden2026_no_deficit_threshold')
    for s in a: np.testing.assert_array_equal(a[s], b[s])

def test_threshold_changes_results_at_baseline_wealth():
    a = returns(); b = returns(tax_mode='sweden2026_no_deficit_threshold')
    assert not np.array_equal(a['AD_HOLD'], b['AD_HOLD'])
