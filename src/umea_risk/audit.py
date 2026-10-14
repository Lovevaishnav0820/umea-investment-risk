"""Checks against hand-worked reference values, scalar/vector comparisons and statistical diagnostics.

Every check raises on failure, so a recorded status of 'passed' means all of its assertions held.
Counts are taken from the cases that were actually executed.
"""
import time
import numpy as np
from .config import load_fixtures,STRATEGIES
from .verification import unit_actual,compare_expected,compare_engines
from .engine import run_scalar
from .vector import run_vector
from .metrics import empirical_es,variational_es,mean_se
from .scenarios import prices_from_innovations,generate_innovations

def deterministic_audit(config,z):
    t0=time.perf_counter();f=load_fixtures();report=[];ledgers=[]
    for fixture in f['unit_fixtures']:
        t=time.perf_counter();res=compare_expected(unit_actual(fixture),fixture['expected'],fixture['id'])
        report.append(dict(id=fixture['id'],kind='unit',status='passed',checked_fields=len(res),
            maximum_absolute_residual=max((r['absolute_residual'] for r in res),default=0.),
            maximum_normalized_residual=max((r['normalized_residual'] for r in res),default=0.),
            fields=res,seconds=time.perf_counter()-t,exception=None))
    identity=[];runoff=[];vector_checks=[];invariants=[]
    for fixture in f['full_path_fixtures']:
        t=time.perf_counter();p=fixture['parameters'];strategy=fixture['strategy']
        s=run_scalar(fixture['prices'],p,strategy,fixture['id'])
        residuals=compare_expected(s.fixture_actual(),fixture['expected'],fixture['id'])
        v=run_vector(np.array(fixture['prices'])[None,:],p,strategy,[0]);agreement=compare_engines(s,v)
        # Deterministic property tolerances are stricter than random-path tolerances.
        W=s.state.bank-s.state.F;tax=sum(r['assessed_amount'] for r in s.records)
        scale=max(abs(W),p['initial_wealth_sek'],abs(s.state.price_pnl),s.state.fees_total,abs(tax))
        ir=abs(W-(p['initial_wealth_sek']+s.state.price_pnl-s.state.fees_total-tax))
        rr=abs(W-s.pre_runoff_value)
        identity.append(dict(id=fixture['id'],absolute_residual_sek=ir,normalized_error=ir/(1e-8+1e-10*scale)))
        runoff.append(dict(id=fixture['id'],absolute_residual_sek=rr,normalized_error=rr/(1e-8+1e-10*max(abs(W),abs(s.pre_runoff_value)))))
        vector_checks.append(dict(id=fixture['id'],paths=1,**agreement));invariants.append(v.invariants)
        for a,b in zip(s.ledger,s.ledger[1:]):
            assert (a['month'],a['phase_order'],a['sequence'])<(b['month'],b['phase_order'],b['sequence'])
            for key in ('n','B','C','bank','F'):
                assert a[key+'_after']==b[key+'_before'],f'Ledger continuity {fixture["id"]}: {key}'
        ledgers.append(s)
        report.append(dict(id=fixture['id'],kind='full_path',status='passed',checked_fields=len(residuals),
            maximum_absolute_residual=max((r['absolute_residual'] for r in residuals),default=0.),
            maximum_normalized_residual=max((r['normalized_residual'] for r in residuals),default=0.),
            fields=residuals,scalar_vector=agreement,accounting=identity[-1],runoff=runoff[-1],
            seconds=time.perf_counter()-t,exception=None))
    for scenario in config['scenarios']:
        n_check=config['validation']['scalar_vector_first_n_paths']
        p=scenario['parameters'];prices=prices_from_innovations(z[:n_check],p)
        for strategy in STRATEGIES:
            t=time.perf_counter();v=run_vector(prices,p,strategy,np.arange(n_check))
            checks=[compare_engines(run_scalar(prices[row],p,strategy),v,row,atol=1e-6) for row in range(n_check)]
            vector_checks.append(dict(id=scenario['id']+'/'+strategy,paths=len(checks),
                checked_fields=sum(c['checked_fields'] for c in checks),
                discrete_fields_checked=sum(c['discrete_fields_checked'] for c in checks),
                max_absolute_residual=max(c['max_absolute_residual'] for c in checks),
                max_normalized_error=max(c['max_normalized_error'] for c in checks),
                discrete_mismatches=sum(c['discrete_mismatches'] for c in checks),
                seconds=time.perf_counter()-t))
    n_check=config['validation']['scalar_vector_first_n_paths']
    p=dict(config['baseline'],tax_mode='none',cost_per_leg=0.)
    prices=prices_from_innovations(z[:n_check],p);out=[run_vector(prices,p,s).W for s in STRATEGIES]
    no_tax_error=max(float(np.max(np.abs(a-b))) for a in out for b in out)
    es_errors=[]
    for fixture in f['unit_fixtures']:
        if fixture['kind']=='empirical_es':
            i=fixture['inputs'];es_errors.append(float(abs(empirical_es(i['losses'],i['alpha'])-variational_es(i['losses'],i['alpha']))))
    assert no_tax_error<=1e-6 and max(es_errors)<=1e-12
    counts=dict(unit_examples=sum(r['kind']=='unit' for r in report),full_path_examples=sum(r['kind']=='full_path' for r in report),
        scalar_vector_cases=sum(c['paths'] for c in vector_checks),
        scalar_vector_random_paths=sum(c['paths'] for c in vector_checks if '/' in c['id']),
        no_tax_paths=int(len(out[0])),variational_es_examples=len(es_errors))
    return dict(status='passed',counts=counts,fixture_tests=report,scalar_vector_checks=vector_checks,
        fixture_identity=identity,fixture_runoff=runoff,no_tax_max_abs_W_difference_sek=no_tax_error,
        variational_es_max_absolute_difference=max(es_errors),seconds=time.perf_counter()-t0),ledgers

def moment_diagnostics(prices,p):
    N=len(prices);J=N*24;S0=p['initial_price'];m=p['annual_expected_simple_price_return'];sigma=p['annual_diffusion_volatility']
    x=np.log(prices[:,1:]/prices[:,:-1]).ravel()
    target=S0*(1+m)**2;se=target*np.sqrt(np.expm1(2*sigma*sigma)/N)
    mu=(np.log1p(m)-sigma*sigma/2)/12;var=sigma*sigma/12
    mse=np.sqrt(var/J);vse=var*np.sqrt(2/(J-1))
    out=[]
    for label,actual,expected,standard_error in [('terminal_price_mean',float(prices[:,-1].mean()),target,se),
        ('log_increment_mean',float(x.mean()),mu,mse),('log_increment_variance',float(x.var(ddof=1)),var,vse)]:
        standardized=abs(actual-expected)/standard_error if standard_error else (0. if abs(actual-expected)<1e-12 else float('inf'))
        out.append(dict(id=label,observed=actual,expected=expected,theoretical_standard_error=standard_error,
                        standardized_discrepancy=standardized,acceptance_bound_standard_errors=6.,status='passed' if standardized<=6 else 'failed'))
    return out

def repeat_baseline(config,primary,bootstrap):
    z=generate_innovations(20261015);p=config['baseline'];prices=prices_from_innovations(z,p)
    repeat={s:run_vector(prices,p,s) for s in STRATEGIES}
    checks=[];es=[]
    for j,s in enumerate(STRATEGIES):
        a=primary[s].net_return;b=repeat[s].net_return
        combined=np.sqrt(mean_se(a)**2+mean_se(b)**2)
        discrepancy=abs(a.mean()-b.mean())/combined if combined else float(abs(a.mean()-b.mean())>1e-12)*7.
        checks.append(dict(id=s,primary_mean=float(a.mean()),repeat_mean=float(b.mean()),primary_se=float(mean_se(a)),
            repeat_se=float(mean_se(b)),combined_se=float(combined),standardized_difference=float(discrepancy),status='passed' if discrepancy<=6 else 'failed'))
        e1=empirical_es(-a);e2=empirical_es(-b);sd=bootstrap['arm_es'][:,j].std(ddof=1)
        es.append(dict(id=s,primary_es95=float(e1),repeat_es95=float(e2),repeat_minus_primary=float(e2-e1),
            primary_bootstrap_sd=float(sd),rough_comparison_scale=float(np.sqrt(2)*sd),interpretation='descriptive stability diagnostic'))
    for j,c in enumerate(config['contrasts']):
        a=primary[c['a']].net_return-primary[c['b']].net_return
        b=repeat[c['a']].net_return-repeat[c['b']].net_return
        combined=np.sqrt(mean_se(a)**2+mean_se(b)**2)
        discrepancy=abs(a.mean()-b.mean())/combined if combined else float(abs(a.mean()-b.mean())>1e-12)*7.
        checks.append(dict(id=c['id'],primary_mean=float(a.mean()),repeat_mean=float(b.mean()),primary_se=float(mean_se(a)),
            repeat_se=float(mean_se(b)),combined_se=float(combined),standardized_difference=float(discrepancy),status='passed' if discrepancy<=6 else 'failed'))
        e1=empirical_es(primary[c['a']].loss)-empirical_es(primary[c['b']].loss)
        e2=empirical_es(repeat[c['a']].loss)-empirical_es(repeat[c['b']].loss)
        sd=bootstrap['delta_es'][:,j].std(ddof=1)
        es.append(dict(id=c['id'],primary_es95=float(e1),repeat_es95=float(e2),repeat_minus_primary=float(e2-e1),
            primary_bootstrap_sd=float(sd),rough_comparison_scale=float(np.sqrt(2)*sd),interpretation='descriptive stability diagnostic'))
    return dict(seed=20261015,paths=20000,mean_checks=checks,es_diagnostics=es,
        moment_diagnostics=moment_diagnostics(prices,p),included_in_primary_tables=False,
        max_mean_difference_in_combined_standard_errors=max(c['standardized_difference'] for c in checks)),repeat,z
