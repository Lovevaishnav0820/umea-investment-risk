"""Every hand-worked unit example in config/benchmark_fixtures.json, including nested fields."""
import pytest
from umea_risk.config import load_fixtures
from umea_risk.metrics import empirical_es, variational_es
from umea_risk.verification import unit_actual, compare_expected

FIXTURES = load_fixtures()['unit_fixtures']

@pytest.mark.parametrize('fixture', FIXTURES, ids=lambda f: f['id'])
def test_unit_example(fixture):
    compare_expected(unit_actual(fixture), fixture['expected'], fixture['id'])

@pytest.mark.parametrize('fixture', [f for f in FIXTURES if f['kind'] == 'empirical_es'], ids=lambda f: f['id'])
def test_es_matches_variational_definition(fixture):
    i = fixture['inputs']
    assert abs(empirical_es(i['losses'], i['alpha']) - variational_es(i['losses'], i['alpha'])) <= 1e-12
