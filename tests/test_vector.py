"""The vectorized engine against the scalar engine, and the no-tax equality of all strategies."""
import numpy as np
import pytest
from umea_risk.config import load_config,load_fixtures
from umea_risk.engine import run_scalar
from umea_risk.vector import run_vector
from umea_risk.scenarios import generate_innovations,prices_from_innovations
from umea_risk.verification import compare_engines

@pytest.mark.parametrize('f',load_fixtures()['full_path_fixtures'],ids=lambda f:f['id'])
def test_vector_full_fixture(f):
    e=run_scalar(f['prices'],f['parameters'],f['strategy'])
    v=run_vector(np.array(f['prices'])[None,:],f['parameters'],f['strategy'],[0])
    compare_engines(e,v)

def test_no_tax_general_equality():
    c=load_config();p=dict(c['baseline'],tax_mode='none',cost_per_leg=0.)
    prices=prices_from_innovations(generate_innovations()[:32],p)
    results=[run_vector(prices,p,s).W for s in c['strategies']]
    assert max(np.max(np.abs(a-b)) for a in results for b in results)<=1e-6

@pytest.mark.parametrize('scenario',load_config()['scenarios'],ids=lambda s:s['id'])
def test_first32_scalar_vector(scenario):
    p=scenario['parameters'];prices=prices_from_innovations(generate_innovations()[:32],p)
    for strategy in load_config()['strategies']:
        v=run_vector(prices,p,strategy,np.arange(32))
        for row in range(32):compare_engines(run_scalar(prices[row],p,strategy),v,row,atol=1e-6)
