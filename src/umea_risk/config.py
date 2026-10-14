"""Load and validate the study configuration."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
STRATEGIES = ["ISK_HOLD", "AD_HOLD", "AD_HARVEST"]
IDS = ["baseline_sweden_lag6", "sweden_lag0", "symmetric_lag6", "symmetric_lag0",
       "grid_m03_sigma15", "grid_m03_sigma25", "grid_m03_sigma35",
       "grid_m06_sigma15", "grid_m06_sigma35", "grid_m09_sigma15",
       "grid_m09_sigma25", "grid_m09_sigma35", "cost_zero", "cost_25bp",
       "threshold_zero", "threshold_10pct", "initial_100k", "no_credit_capacity", "sweden_lag12"]
BASELINE = dict(initial_wealth_sek=500000., initial_price=100., horizon_months=24,
    annual_expected_simple_price_return=.06, annual_diffusion_volatility=.25,
    cost_per_leg=.001, harvest_month=12, harvest_loss_threshold=.05,
    tax_mode="sweden2026", settlement_lag_months=6, credit_capacity_sek=None,
    allow_20pct_proceeds_deduction=True, isk_tax_rate=.01065, isk_allowance_sek=300000.,
    dividend_yield=0., cash_interest_rate=0., settlement_discount_rate=0.)
SCENARIO_OVERRIDES = [{},{'settlement_lag_months':0},{'tax_mode':'symmetric30'},
    {'tax_mode':'symmetric30','settlement_lag_months':0},
    *[{'annual_expected_simple_price_return':m,'annual_diffusion_volatility':sigma}
      for m,sigma in ((.03,.15),(.03,.25),(.03,.35),(.06,.15),(.06,.35),(.09,.15),(.09,.25),(.09,.35))],
    {'cost_per_leg':0.},{'cost_per_leg':.0025},{'harvest_loss_threshold':0.},
    {'harvest_loss_threshold':.10},{'initial_wealth_sek':100000.},
    {'credit_capacity_sek':0.},{'settlement_lag_months':12}]

def _pairs(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"Duplicate JSON key: {k}")
        d[k] = v
    return d

def read_json(path):
    def bad(x):
        raise ValueError(f"Nonfinite JSON constant: {x}")
    data = json.loads(Path(path).read_text(), parse_constant=bad, object_pairs_hook=_pairs)
    def finite(x):
        if isinstance(x, dict):
            for v in x.values(): finite(v)
        elif isinstance(x, list):
            for v in x: finite(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            if not math.isfinite(x): raise ValueError("Nonfinite numeric JSON value")
    finite(data)
    return data

def validate_parameters(p, validation=False):
    if set(p) != set(BASELINE): raise ValueError("Unsupported/missing parameter key")
    for k, v in p.items():
        if k in ("tax_mode", "allow_20pct_proceeds_deduction"): continue
        if k == "credit_capacity_sek" and v is None: continue
        if isinstance(v, bool) or not isinstance(v, (int,float)) or not math.isfinite(v):
            raise ValueError(f"Invalid finite number: {k}")
    if not p['annual_expected_simple_price_return'] > -1: raise ValueError("m must exceed -1")
    if p['annual_diffusion_volatility'] < 0: raise ValueError("Negative volatility")
    for k in ('initial_wealth_sek','initial_price'):
        if p[k] <= 0: raise ValueError(f"Nonpositive {k}")
    for k in ('cost_per_leg','harvest_loss_threshold'):
        if not 0 <= p[k] < 1: raise ValueError(f"Invalid {k}")
    H = p['credit_capacity_sek']
    if H is not None and H < 0: raise ValueError("Negative capacity")
    # Primary configurations use the two reported tax schedules. Engine-level runs also accept
    # the validation-only no-tax mode and the supplementary no-threshold counterfactual.
    modes = ('sweden2026','symmetric30','none','sweden2026_no_deficit_threshold') if validation else ('sweden2026','symmetric30')
    if p['tax_mode'] not in modes: raise ValueError("Unsupported tax mode")
    if p['tax_mode'] == 'symmetric30' and H is not None: raise ValueError("Symmetric capacity must be null")
    if type(p['allow_20pct_proceeds_deduction']) is not bool: raise ValueError("Deduction flag must be boolean")
    for k in ('horizon_months','harvest_month','isk_tax_rate','isk_allowance_sek',
              'dividend_yield','cash_interest_rate','settlement_discount_rate'):
        if p[k] != BASELINE[k]: raise ValueError(f"Fixed rate/clock violated: {k}")
    if type(p['horizon_months']) is not int or type(p['harvest_month']) is not int:
        raise ValueError("Clocks must be integers")
    if type(p['settlement_lag_months']) is not int or p['settlement_lag_months'] not in (0,6,12):
        raise ValueError("Unsupported settlement clock")
    return p

def load_config(path=CONFIG_DIR/'experiment_config.json'):
    c = read_json(path)
    if c['baseline'] != BASELINE: raise ValueError("Fixed baseline changed")
    if c['strategies'] != STRATEGIES or [s['id'] for s in c['scenarios']] != IDS:
        raise ValueError("Fixed strategy/scenario IDs or order changed")
    sim = c['simulation']; boot = c['monte_carlo_intervals']; val=c['validation']
    for actual, expected in [(sim['paths'],20000),(sim['seed'],20261012),
        (sim['rng'],'numpy.PCG64'),(sim['normal_array_shape'],[20000,24]),(sim['dtype'],'float64'),
        (sim['common_random_numbers'],True),(boot['resamples'],2000),(boot['seed'],20261013),
        (boot['rng'],'numpy.PCG64'),(boot['index_shape'],[2000,20000]),
        (boot['reuse_indices_across_scenarios'],True),(boot['confidence'],.95),
        (boot['percentile_method'],'linear'),(c['metrics']['es_alpha'],.95),
        (val['repeat_seed'],20261015),(val['ledger_selection_seed'],20261014),
        (val['scalar_vector_first_n_paths'],32),(val['repeat_paths'],20000),
        (c['scenario_count'],19),(c['arm_scenario_count'],57)]:
        if actual != expected: raise ValueError(f"Fixed setting: {actual!r} != {expected!r}")
    constants = dict(capital_gains_rate=.3,residual_loss_deductible_fraction=.7,
        capital_deficit_threshold_sek=100000.,deficit_reduction_first_rate=.3,
        deficit_reduction_excess_rate=.21,alternative_sale_deduction_fraction=.2,
        symmetric_rate=.3,income_year_rules=2026,rules_fixed_in_both_model_years=True,
        capacity_resets_each_tax_year=True)
    if c['tax_constants'] != constants: raise ValueError("Fixed tax constants changed")
    expected_calendar=dict(opening_snapshot_months=[1,4,7,10,13,16,19,22],empty_initial_snapshot=True,
        assessment_months=[12,24],terminal_liquidation_month=24,reinvest_credit_only_if_month_less_than=24,
        allowed_settlement_lags_months=[0,6,12])
    if c['calendar'] != expected_calendar: raise ValueError("Fixed calendar changed")
    expected_validation=dict(repeat_seed=20261015,repeat_baseline_only=True,repeat_paths=20000,
        repeat_bootstrap_required=False,moment_check_max_standard_errors=6.,ledger_selection_seed=20261014,
        ledger_sample_size=6,scalar_vector_first_n_paths=32,unit_money_atol_sek=1e-8,path_money_atol_sek=1e-6,
        relative_tolerance=1e-10,dimensionless_atol=1e-12,integer_tail_mass_snap_atol=1e-10,outside_reported_configurations=True)
    if val != expected_validation: raise ValueError("Fixed validation settings changed")
    if boot['method']!='paired_iid_path_bootstrap': raise ValueError("Unsupported bootstrap")
    expected_metrics=dict(es_alpha=.95,loss_definition='1 - net_investment_outcome / initial_wealth',
        crra_enabled=False,cara_enabled=False,annualization_enabled=False,negative_outcomes_retained=True)
    if c['metrics'] != expected_metrics: raise ValueError("Fixed estimands changed")
    expected_contrasts=[dict(id='harvest_minus_hold',a='AD_HARVEST',b='AD_HOLD',role='primary'),
        dict(id='harvest_minus_isk',a='AD_HARVEST',b='ISK_HOLD',role='account_context'),
        dict(id='hold_minus_isk',a='AD_HOLD',b='ISK_HOLD',role='account_context')]
    if c['contrasts']!=expected_contrasts:raise ValueError("Fixed contrasts changed")
    resolved = []
    for s,expected_override in zip(c['scenarios'],SCENARIO_OVERRIDES):
        if set(s['overrides']) - set(BASELINE): raise ValueError("Unsupported override")
        if s['overrides']!=expected_override:raise ValueError(f"Fixed override changed: {s['id']}")
        if s['parameters'] != dict(BASELINE,**s['overrides']): raise ValueError(f"Resolution mismatch: {s['id']}")
        validate_parameters(s['parameters'])
        resolved.append(json.dumps(s['parameters'],sort_keys=True))
    if len(set(resolved)) != 19: raise ValueError("Duplicate resolved configuration")
    validate_supplementary(c)
    return c

SUPPLEMENTARY_WEALTH_SEK = [100000., 200000., 300000., 400000., 500000., 750000., 1000000., 2000000.]

def supplementary_experiments(c):
    """Resolve the supplementary experiments, which are separate from the 19 configurations."""
    out = []
    for e in c['supplementary_experiments']['experiments']:
        p = dict(c['baseline'], **e['overrides'])
        validate_parameters(p, validation=True)
        out.append(dict(id=e['id'], role=e['role'], label=e['label'], parameters=p))
    return out

def validate_supplementary(c):
    s = c.get('supplementary_experiments')
    if s is None: raise ValueError("Missing supplementary experiments")
    expected = [dict(id=f'wealth_{int(w/1000)}k', role='starting_wealth', label=f'Swedish rules, W0 = {int(w):,} SEK',
                     overrides={'initial_wealth_sek': w}) for w in SUPPLEMENTARY_WEALTH_SEK]
    expected.append(dict(id='no_deficit_threshold_500k', role='counterfactual_tax_schedule',
        label='Counterfactual: constant 21% relief on residual losses (no 100,000 SEK deficit threshold), W0 = 500,000 SEK',
        overrides={'tax_mode': 'sweden2026_no_deficit_threshold'}))
    if s['experiments'] != expected: raise ValueError("Supplementary experiments changed")
    if s['uses_primary_innovations'] is not True or s['uses_primary_bootstrap_indices'] is not True:
        raise ValueError("Supplementary experiments must reuse the primary random numbers")
    supplementary_experiments(c)

def load_fixtures():
    return read_json(CONFIG_DIR/'benchmark_fixtures.json')
