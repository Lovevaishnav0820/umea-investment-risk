"""Empirical expected shortfall with exact tail mass, and the paired bootstrap."""
from types import SimpleNamespace
import numpy as np

def compact(engine,W0):
    """Keep only the per-path results needed for metrics and intervals."""
    return SimpleNamespace(net_return=engine.net_return,loss=engine.loss,W=engine.W,W0=W0,
        s={k:engine.s[k] for k in ('F','fees_total','harvested')})

def empirical_es(losses,alpha=.95,axis=-1):
    x=np.asarray(losses,dtype=np.float64)
    if x.size==0 or not np.isfinite(x).all() or not 0<=alpha<1: raise ValueError("Invalid ES input")
    x=np.sort(x,axis=axis)
    x=np.flip(x,axis=axis)
    n=x.shape[axis]; u=(1-alpha)*n
    if abs(u-round(u))<=1e-10: u=float(round(u))
    k=int(np.floor(u)); f=u-k
    total=np.take(x,np.arange(k),axis=axis).sum(axis=axis)
    if f: total=total+f*np.take(x,k,axis=axis)
    return total/u

def variational_es(losses,alpha):
    x=np.asarray(losses,dtype=float)
    return min(eta+np.maximum(x-eta,0.).mean()/(1-alpha) for eta in np.unique(x))

def paired_resamples(return_a,return_b,indices,alpha=.95):
    a=np.asarray(return_a)[indices]; b=np.asarray(return_b)[indices]
    return (a-b).mean(axis=1), empirical_es(-a,alpha,axis=1)-empirical_es(-b,alpha,axis=1)

def interval(statistics):
    return np.quantile(statistics,[.025,.975],method='linear')

def mean_se(x):
    return np.std(x,ddof=1)/np.sqrt(len(x))

def break_even_ratio(tau,relief):
    if not np.isfinite(tau) or not np.isfinite(relief) or not 0 <= tau < 1 or not 0 <= relief <= 1:
        raise ValueError("Require 0 <= tau < 1 and 0 <= relief <= 1")
    if relief == 0:
        if tau == 0:
            raise ValueError("No unique break-even: all admissible ratios give equal wealth")
        raise ValueError("No finite break-even at zero relief with positive gains tax")
    return tau*(1-relief)/(relief*(1-tau))

def cash_refund_benchmark(b,p,z,relief,tau):
    credit=relief*(b-p); tax=tau*(z-p)
    return dict(credit=credit,terminal_gains_tax=tax,terminal_net_outcome=z-tax+credit,
                hold_net_outcome=z-tau*(z-b))

def scenario_statistics(scenario_id,engines,indices,contrasts):
    """Strategy metrics and paired contrasts, with intervals from one shared bootstrap index matrix."""
    from .config import STRATEGIES
    n=len(indices[0]);draws=len(indices)
    arm_mean=np.empty((draws,3));arm_es=arm_mean.copy();arm_rows=[];contrast_rows=[];paired={}
    for j,strategy in enumerate(STRATEGIES):
        e=engines[strategy];r=e.net_return;loss=e.loss;s=e.s;W0=e.W0
        for start in range(0,draws,100):
            stop=min(start+100,draws)
            samples=r[indices[start:stop]]
            arm_mean[start:stop,j]=samples.mean(axis=1)
            arm_es[start:stop,j]=empirical_es(-samples,axis=1)
        low,high=interval(arm_mean[:,j]);elow,ehigh=interval(arm_es[:,j]);count=int(np.count_nonzero(s['F']>0))
        row=dict(scenario_id=scenario_id,strategy=strategy,n_paths=n,mean_net_return=float(r.mean()),
            mean_ci_low=float(low),mean_ci_high=float(high),mean_mc_se=float(mean_se(r)),
            es95_loss=float(empirical_es(loss)),es_ci_low=float(elow),es_ci_high=float(ehigh),
            count_loss=int(np.count_nonzero(e.W<W0)),probability_loss=float(np.mean(e.W<W0)),
            count_nonpositive_W=int(np.count_nonzero(e.W<=0)),probability_nonpositive_W=float(np.mean(e.W<=0)),
            count_funding=count,probability_funding=count/n,zero_event_upper95_if_applicable=3/n if count==0 else None,
            mean_F_over_W0=float(s['F'].mean()/W0),max_F_over_W0=float(s['F'].max()/W0),
            mean_fees_sek=float(s['fees_total'].mean()),mean_fees_over_W0=float(s['fees_total'].mean()/W0),
            harvest_count=int(s['harvested'].sum()),harvest_frequency=float(s['harvested'].mean()),mean_W_sek=float(e.W.mean()),
            mean_bootstrap_sd=float(arm_mean[:,j].std(ddof=1)),es_bootstrap_sd=float(arm_es[:,j].std(ddof=1)))
        row['bootstrap_to_analytic_mean_se_ratio']=row['mean_bootstrap_sd']/row['mean_mc_se'] if row['mean_mc_se'] else None
        arm_rows.append(row)
    delta_mean=np.empty((draws,3));delta_es=delta_mean.copy()
    trigger=engines['AD_HARVEST'].s['harvested'];triggered=int(trigger.sum())
    for j,c in enumerate(contrasts):
        a,b=STRATEGIES.index(c['a']),STRATEGIES.index(c['b'])
        difference=engines[c['a']].net_return-engines[c['b']].net_return
        paired[c['id']]=difference
        # The paired mean is recomputed in every draw; the ES contrast is the difference of the two ES values.
        for start in range(0,draws,100):
            stop=min(start+100,draws)
            delta_mean[start:stop,j]=difference[indices[start:stop]].mean(axis=1)
        delta_es[:,j]=arm_es[:,a]-arm_es[:,b]
        low,high=interval(delta_mean[:,j]);elow,ehigh=interval(delta_es[:,j])
        row=dict(scenario_id=scenario_id,contrast=c['id'],arm_a=c['a'],arm_b=c['b'],role=c['role'],
            delta_mean=float(difference.mean()),delta_mean_ci_low=float(low),delta_mean_ci_high=float(high),
            delta_mean_mc_se=float(mean_se(difference)),delta_es95=arm_rows[a]['es95_loss']-arm_rows[b]['es95_loss'],
            delta_es_ci_low=float(elow),delta_es_ci_high=float(ehigh),paired_median=float(np.median(difference)),
            paired_q05=float(np.quantile(difference,.05,method='linear')),paired_q95=float(np.quantile(difference,.95,method='linear')),
            paired_probability_positive=float(np.mean(difference>0)),triggered_count=triggered,
            triggered_paired_mean=float(difference[trigger].mean()) if triggered else None,
            delta_mean_bootstrap_sd=float(delta_mean[:,j].std(ddof=1)),delta_es_bootstrap_sd=float(delta_es[:,j].std(ddof=1)))
        row['bootstrap_to_analytic_mean_se_ratio']=row['delta_mean_bootstrap_sd']/row['delta_mean_mc_se'] if row['delta_mean_mc_se'] else None
        row['mean_direction']='numerically_unresolved' if low<=0<=high else 'positive' if low>0 else 'negative'
        row['es_direction']='numerically_unresolved' if elow<=0<=ehigh else 'positive' if elow>0 else 'negative'
        contrast_rows.append(row)
    return arm_rows,contrast_rows,dict(arm_mean=arm_mean,arm_es=arm_es,delta_mean=delta_mean,delta_es=delta_es),paired
