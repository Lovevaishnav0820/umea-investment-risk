"""Compare engine results with the hand-worked reference values and with each other."""
from dataclasses import asdict
import numpy as np
from umea_risk.tax import annual_ad_tax, isk_assessment, isk_snapshot
from umea_risk.trades import buy, sell, harvest_trigger, fund_positive_bill
from umea_risk.metrics import (empirical_es,variational_es,paired_resamples,interval,
                              break_even_ratio,cash_refund_benchmark)
from umea_risk.scenarios import price_moments

def unit_actual(f):
    i=f['inputs']; kind=f['kind']
    if kind=='annual_ad_tax':
        return {'signed_tax_sek':annual_ad_tax(sum(i['gains_sek']),i['credit_capacity_sek'],i['tax_mode'])}
    if kind=='two_annual_assessments':
        return {'signed_taxes_sek':[annual_ad_tax(g,i['credit_capacity_sek'],i['tax_mode']) for g in i['annual_net_gains_sek']]}
    if kind=='trade_sequence':
        if 'initial_buys' in i:
            n=B=0.
            for b in i['initial_buys']:
                A=b['shares']*b['price']*(1+b['cost_per_leg'])
                t=buy(n,B,A,A,b['price'],b['cost_per_leg']);n,B=t.shares,t.actual_basis
        elif 'initial_shares' in i: n,B=i['initial_shares'],i['initial_actual_basis']
        else:
            b=buy(0.,0.,i['initial_cash_sek'],i['buy_budget_sek'],i['buy_price'],i['cost_per_leg'])
            s=sell(b.shares,b.actual_basis,b.cash,b.shares,i['sale_price'],i['cost_per_leg'])
            return {'after_buy':dict(shares=b.shares,actual_basis=b.actual_basis,cash=b.cash,fee=b.fee),
                    'after_sale':dict(shares=s.shares,actual_basis=s.actual_basis,cash=s.cash,gain=s.gain,fee=s.fee),
                    'fees_total':b.fee+s.fee}
        sale=i['sale'];t=sell(n,B,0.,sale['shares'],sale['price'],sale['cost_per_leg'],alternative=i['allow_20pct_proceeds_deduction'])
        return {'expected_before_sale':dict(shares=n,actual_basis=B),
                'expected_after_sale':dict(net_sale_proceeds=t.net_sale_proceeds,actual_basis_removed=t.actual_basis_removed,
                    deduction_selected=t.deduction_selected,taxable_gain=t.gain,remaining_shares=t.shares,remaining_actual_basis=t.actual_basis)}
    if kind=='sale':
        t=sell(i['shares'],i['actual_basis'],i['cash'],i['sell_quantity'],i['price'],i['cost_per_leg'])
        return dict(shares=t.shares,actual_basis=t.actual_basis,cash=t.cash,gain=t.gain,fee=t.fee)
    if kind=='sell_rebuy':
        s=sell(i['shares'],i['actual_basis'],i['cash'],i['shares'],i['price'],i['cost_per_leg'])
        b=buy(s.shares,s.actual_basis,s.cash,s.cash,i['price'],i['cost_per_leg'])
        return dict(shares=b.shares,actual_basis=b.actual_basis,cash=b.cash,realized_gain=s.gain,fees_total=s.fee+b.fee)
    if kind=='isk_assessment':
        base,tax=isk_assessment(i['quarter_values_sek'],i['deposits_sek'],i['rate'],i['allowance_sek'])
        return dict(base_sek=base,signed_tax_sek=tax)
    if kind=='isk_snapshot': return {'snapshot_value_sek':isk_snapshot(i['shares'],i['price'],i['cash_sek'])}
    if kind=='empirical_es': return {'es':empirical_es(i['losses'],i['alpha'])}
    if kind=='es_contrast':
        a=np.array(i['loss_a']); b=np.array(i['loss_b']);alpha=i['alpha']
        ea,eb=empirical_es(a,alpha),empirical_es(b,alpha)
        return dict(es_a=ea,es_b=eb,difference_of_es=ea-eb,es_of_paired_loss_difference=empirical_es(a-b,alpha))
    if kind=='paired_resamples':
        mean,es=paired_resamples(i['return_a'],i['return_b'],np.array(i['row_draws']),i['alpha'])
        return dict(mean_difference_draws=mean,es_difference_draws=es,mean_difference_percentile_interval=interval(mean))
    if kind=='break_even': return {'terminal_to_refund_price_ratio':break_even_ratio(i['tau'],i['lambda'])}
    if kind=='analytical_cash_refund': return cash_refund_benchmark(i['b'],i['p'],i['z'],i['lambda'],i['tau'])
    if kind=='harvest_trigger':
        return dict(trigger=harvest_trigger(i['shares'],i['basis'],i['price'],i['cost_per_leg'],i['threshold']),
                    net_sale_proceeds=i['shares']*i['price']*(1-i['cost_per_leg']))
    if kind=='positive_bill': return asdict(fund_positive_bill(**i))
    if kind=='price_moments': return price_moments(i['initial_price'],i['annual_expected_simple_price_return'],i['annual_diffusion_volatility'],i['months'])
    raise AssertionError(f"Unimplemented unit: {kind}")

def compare_expected(actual,expected,path='',residuals=None):
    """Compare every expected field; a missing field is an error rather than a silent skip."""
    if residuals is None: residuals=[]
    if isinstance(expected,dict):
        for key,v in expected.items():
            assert key in actual,f'Missing expected field: {path}.{key}'
            compare_expected(actual[key],v,path+'.'+key,residuals)
    elif isinstance(expected,bool): assert bool(actual)==expected,path
    elif isinstance(expected,str) or expected is None: assert actual==expected,path
    elif isinstance(expected,list):
        assert len(actual)==len(expected),path
        for k,v in enumerate(expected): compare_expected(actual[k],v,f'{path}[{k}]',residuals)
    else:
        discrete=any(s in path for s in ('count','month','records','trades_at','year3_isk_tax')) and not any(s in path for s in ('monthly_log','shares_','basis_'))
        if discrete: assert actual==expected,f'{path}: expected {expected!r}, observed {actual!r}'
        else:
            leaf=path.rsplit('.',1)[-1].split('[',1)[0]
            dimensionless=('shares' in leaf or leaf in ('es','es_a','es_b','difference_of_es',
                'es_of_paired_loss_difference','mean_difference_draws','es_difference_draws',
                'mean_difference_percentile_interval','terminal_to_refund_price_ratio',
                'annual_log_drift','monthly_log_mean','monthly_log_variance'))
            atol=1e-12 if dimensionless else 1e-8
            error=abs(float(actual)-expected);bound=atol+1e-10*max(abs(float(actual)),abs(expected))
            residuals.append(dict(field=path,expected=expected,observed=float(actual),absolute_residual=error,normalized_residual=error/bound,atol=atol,rtol=1e-10))
            assert error<=bound,f'{path}: expected {expected!r}, observed {actual!r}, residual {error:g}'
    return residuals

def compare_engines(scalar,vector,row=0,atol=1e-8):
    """Compare the scalar and vector engines on one path.

    The engines implement the monthly state transitions separately but share the tax
    functions, the harvest rule and parameter validation, so agreement checks the two
    state-transition implementations rather than the tax rules themselves.
    Discrete fields must agree exactly; numerical fields use atol + 1e-10 * scale.
    """
    residuals=[];checked=0;discrete_checked=0;mismatches=[]
    def check(a,b,key):
        nonlocal checked,discrete_checked
        checked+=1
        if a is None:a=-1
        if key in ('settled_months','due_months'):
            discrete_checked+=1
            if not np.array_equal(a,b):mismatches.append(f'{key}: {a!r} != {b!r}')
        elif isinstance(a,(bool,int,str)):
            discrete_checked+=1
            if not a==b:mismatches.append(f'{key}: {a!r} != {b!r}')
        else:
            a,b=np.asarray(a),np.asarray(b)
            small=key in ('n','n_before','n_after','n_before_liquidation','trade_quantity','net_return')
            bound=(1e-12 if small else atol)+1e-10*np.maximum(np.abs(a),np.abs(b))
            err=np.abs(a-b);norm=err/bound
            residuals.append((float(np.max(err)),float(np.max(norm))))
            assert np.all(norm<=1),f'{key}: {a!r} != {b!r}, normalized {norm}'
    for month,state in scalar.checkpoints.items():
        for k,a in state.items():check(a,vector.history[month][k][row],k)
    for k,a,b in [('tax', [r['assessed_amount'] for r in scalar.records],vector.taxes[row]),
                  ('quarter_values',scalar.quarters,vector.quarters[row]),('annual_g',scalar.annual_g,vector.annual_g[row]),
                  ('settled_months',[r['settled_month'] for r in scalar.records],vector.settled_months[row]),
                  ('due_months',[r['due_month'] for r in scalar.records],vector.due_months),
                  ('W',scalar.state.bank-scalar.state.F,vector.W[row]),
                  ('pre_runoff_value',scalar.pre_runoff_value,vector.pre_runoff_value[row]),
                  ('n_before_liquidation',scalar.pre_liquidation_n,vector.pre_liquidation_n[row])]:check(a,b,k)
    vevents=[e for e in vector.events if e['mask'][row]]
    assert len(vevents)==len(scalar.ledger),f'Event count: {len(vevents)} != {len(scalar.ledger)}'
    for se,ve in zip(scalar.ledger,vevents):
        for k in ('month','phase','event'):check(se[k],ve[k],k)
        for k in ('price','n_before','n_after','B_before','B_after','C_before','C_after','bank_before','bank_after',
                  'F_before','F_after','cumulative_price_pnl','trade_quantity','gross_value','net_proceeds_or_budget',
                  'actual_basis_removed','deduction_selected','deduction_method','realized_gain','fee','assessed_tax',
                  'due_month','settled_month','snapshot_value'):
            if se.get(k) is None:assert k not in ve or ve[k] is None,k
            else:
                v=ve[k];b=v[row] if isinstance(v,np.ndarray) else v
                check(se[k],b,k)
    assert not mismatches,f'Discrete scalar/vector mismatches: {mismatches[:5]}'
    return dict(checked_fields=checked,discrete_fields_checked=discrete_checked,discrete_mismatches=len(mismatches),
                max_absolute_residual=max((a for a,b in residuals),default=0.),
                max_normalized_error=max((b for a,b in residuals),default=0.))
