"""Full-path worked examples run through the scalar engine, with accounting and calendar checks."""
import pytest
from umea_risk.config import load_fixtures
from umea_risk.engine import run_scalar
from umea_risk.verification import compare_expected

@pytest.mark.parametrize('fixture',load_fixtures()['full_path_fixtures'],ids=lambda f:f['id'])
def test_full_scalar_fixture(fixture):
    e=run_scalar(fixture['prices'],fixture['parameters'],fixture['strategy'],fixture['id'])
    compare_expected(e.fixture_actual(),fixture['expected'],fixture['id'])
    s=e.state;W=s.bank-s.F;W0=fixture['parameters']['initial_wealth_sek'];tax=sum(r['assessed_amount'] for r in e.records)
    residual=abs(W-(W0+s.price_pnl-s.fees_total-tax))
    assert residual<=1e-8+1e-10*max(abs(W),W0,abs(s.price_pnl),s.fees_total,abs(tax))
    assert abs(W-e.pre_runoff_value)<=1e-8+1e-10*max(abs(W),abs(e.pre_runoff_value))
    assert all((a['month'],a['phase_order'],a['sequence'])<(b['month'],b['phase_order'],b['sequence']) for a,b in zip(e.ledger,e.ledger[1:]))
    assert all(r['assessed_month']<=r['settled_month']==r['due_month'] for r in e.records)
