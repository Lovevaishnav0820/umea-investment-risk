"""Check bootstrap pairing and analytical boundary cases independently."""
from types import SimpleNamespace

import numpy as np
import pytest

from umea_risk.config import STRATEGIES, load_config
from umea_risk.metrics import break_even_ratio, empirical_es, scenario_statistics
from umea_risk.scenarios import generate_bootstrap_indices


def test_bootstrap_sample_count_and_seed():
    c = load_config()
    actual = generate_bootstrap_indices(n=17, resamples=c['monte_carlo_intervals']['resamples'])
    expected = np.random.Generator(np.random.PCG64(20261013)).integers(
        0, 17, size=(2000, 17), dtype=np.int64)
    assert np.array_equal(actual, expected)


def test_batched_statistics_preserve_pairing_and_tail_values():
    # Cross two batch boundaries, include ties, and use non-integer tail mass.
    returns = np.array([[-.5, -.1, 0., 0., .1, .4, .6],
                        [-.4, -.2, 0., 0., .2, .3, .5],
                        [-.3, -.2, 0., 0., .1, .2, .4]])
    indices = generate_bootstrap_indices(n=7, resamples=203, seed=4)
    engines = {}
    for strategy, r in zip(STRATEGIES, returns):
        engines[strategy] = SimpleNamespace(
            net_return=r, loss=-r, W=100*(1+r), W0=100,
            s={'F': np.zeros(7), 'fees_total': np.zeros(7),
               'harvested': np.array([True, True, False, False, False, False, False])})
    contrasts = load_config()['contrasts']
    _, rows, boot, _ = scenario_statistics('test', engines, indices, contrasts)
    for j, r in enumerate(returns):
        expected_mean = np.array([r[idx].mean() for idx in indices])
        expected_es = np.array([empirical_es(-r[idx]) for idx in indices])
        np.testing.assert_array_equal(boot['arm_mean'][:, j], expected_mean)
        np.testing.assert_array_equal(boot['arm_es'][:, j], expected_es)
    for j, contrast in enumerate(contrasts):
        a, b = STRATEGIES.index(contrast['a']), STRATEGIES.index(contrast['b'])
        expected = np.array([(returns[a, idx]-returns[b, idx]).mean() for idx in indices])
        np.testing.assert_array_equal(boot['delta_mean'][:, j], expected)
        np.testing.assert_array_equal(boot['delta_es'][:, j], boot['arm_es'][:, a]-boot['arm_es'][:, b])
        assert rows[j]['delta_es95'] == empirical_es(-returns[a])-empirical_es(-returns[b])
    assert rows[0]['delta_es95'] < 0  # Harvesting has lower tail loss in this example.


@pytest.mark.parametrize('tau,relief,message', [
    (0., 0., 'No unique break-even'),
    (.3, 0., 'No finite break-even'),
    (1., .21, 'Require'),
    (.3, -.1, 'Require'),
    (.3, 1.1, 'Require'),
    (float('nan'), .21, 'Require'),
])
def test_break_even_domain(tau, relief, message):
    with pytest.raises(ValueError, match=message):
        break_even_ratio(tau, relief)
