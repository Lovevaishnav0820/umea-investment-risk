"""Run the study: reference checks, the 19 configurations, intervals, supplementary analysis and reports."""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import platform
import sys
import time
from pathlib import Path
import numpy as np
from . import __version__
from .config import ROOT,CONFIG_DIR,load_config,load_fixtures,STRATEGIES
from .scenarios import generate_innovations,generate_bootstrap_indices,ledger_indices,prices_from_innovations,raw_hash
from .vector import run_vector
from .engine import run_scalar
from .audit import deterministic_audit,moment_diagnostics,repeat_baseline
from .metrics import scenario_statistics,compact
from .supplementary import run_supplementary
from .io import write_json,write_csv,save_arrays,file_hash

DEPENDENCIES=('numpy','matplotlib','pytest','reportlab','pypdf','pillow')

def environment():
    return dict(software_version=__version__,python=sys.version,platform=platform.platform(),machine=platform.machine(),
        dependencies={name:importlib.metadata.version(name) for name in DEPENDENCIES})

def run_study(out):
    out=Path(out);start=time.perf_counter();c=load_config();f=load_fixtures()
    for sub in ('metadata','arrays','ledgers/fixtures','ledgers/diagnostics','tables','figures','validation','note','supplementary'):
        (out/sub).mkdir(parents=True,exist_ok=True)
    meta=dict(run_started_utc=datetime.now(timezone.utc).isoformat(),**environment(),
        input_sha256={name:file_hash(CONFIG_DIR/name) for name in ('experiment_config.json','benchmark_fixtures.json')},
        seeds=dict(primary_innovations=c['simulation']['seed'],bootstrap_indices=c['monte_carlo_intervals']['seed'],
                   diagnostic_path_selection=c['validation']['ledger_selection_seed'],independent_baseline_check=c['validation']['repeat_seed']))
    registry=[]
    z=generate_innovations(seed=c['simulation']['seed'],n=c['simulation']['paths'])
    indices=generate_bootstrap_indices(n=c['simulation']['paths'],resamples=c['monte_carlo_intervals']['resamples'],
        seed=c['monte_carlo_intervals']['seed']);selected=ledger_indices()
    meta['diagnostic_path_ids']=selected.tolist()
    for filename,key,a in [('primary_innovations','Z',z),('bootstrap_indices','indices',indices)]:
        record=save_arrays(out/f'arrays/{filename}.npz',**{key:a});record['file']=str(Path(record['file']).relative_to(out));registry.append(record)
    n_check=c['validation']['scalar_vector_first_n_paths']
    print(f"Reference checks: {len(f['unit_fixtures'])} unit examples, {len(f['full_path_fixtures'])} full-path examples, "
          f"scalar/vector comparison on the first {n_check} paths of {len(c['scenarios'])} configurations",flush=True)
    deterministic,fixtures=deterministic_audit(c,z)
    for e in fixtures:
        write_csv(out/f'ledgers/fixtures/{e.scenario}.csv',e.ledger)
        write_json(out/f'ledgers/fixtures/{e.scenario}_tax_records.json',e.records)
    engines={};allpaths=[];price_cache={};moments=[];price_hashes=[]
    for scenario in c['scenarios']:
        sid=scenario['id'];p=scenario['parameters'];key=tuple(p[k] for k in ('annual_expected_simple_price_return','annual_diffusion_volatility','initial_price'))
        if key not in price_cache:
            prices=prices_from_innovations(z,p);price_cache[key]=prices
            price_hashes.append(dict(m=key[0],sigma=key[1],S0=key[2],shape=list(prices.shape),dtype=str(prices.dtype),raw_sha256=raw_hash(prices)))
            moments.append(dict(m=key[0],sigma=key[1],checks=moment_diagnostics(prices,p)))
        prices=price_cache[key];engines[sid]={}
        print(f'Configuration {sid}: {len(STRATEGIES)} strategies x {len(z):,} paths with accounting and state checks',flush=True)
        for strategy in STRATEGIES:
            t=time.perf_counter();v=run_vector(prices,p,strategy)
            allpaths.append(dict(id=sid+'/'+strategy,paths=int(v.N),status='passed',seconds=time.perf_counter()-t,
                accounting_max_absolute_residual_sek=float(np.max(np.abs(v.accounting_residual))),
                max_normalized_identity_error=float(np.max(v.normalized_identity)),
                runoff_max_absolute_residual_sek=float(np.max(np.abs(v.runoff_residual))),
                max_normalized_runoff_error=float(np.max(v.normalized_runoff)),
                invariant_violations=v.invariants,state_observations=v.state_observations,min_asset_states=v.min_state,
                tax_records_checked=int(v.settled_months.size),no_month24_buys=bool(np.all(v.buy_by_month[:,24]==0)),
                terminal_n_B_C_zero=bool(np.all(v.s['n']==0) and np.all(v.s['B']==0) and np.all(v.s['C']==0))))
            record=save_arrays(out/f'arrays/outcomes/{sid}__{strategy}.npz',**v.outcome_arrays(sid))
            record['file']=str(Path(record['file']).relative_to(out));registry.append(record)
            engines[sid][strategy]=compact(v,p['initial_wealth_sek'])
            for path_id in selected:
                e=run_scalar(prices[path_id],p,strategy,sid,int(path_id))
                write_csv(out/f'ledgers/diagnostics/{sid}__{strategy}__path{path_id}.csv',e.ledger)
                write_json(out/f'ledgers/diagnostics/{sid}__{strategy}__path{path_id}_tax_records.json',e.records)
            del v
    if any(check['status']!='passed' for model in moments for check in model['checks']):
        raise AssertionError('Price-moment diagnostic failed; the primary seed is kept and the failure must be investigated')
    meta['price_models']=price_hashes
    metrics=[];contrasts=[];baseline_boot=None;se_diagnostics=[]
    for scenario in c['scenarios']:
        sid=scenario['id'];print(f"Metrics and {len(indices):,} paired bootstrap draws: {sid}",flush=True)
        arm,delta,boot,paired=scenario_statistics(sid,engines[sid],indices,c['contrasts'])
        metrics+=arm;contrasts+=delta
        record=save_arrays(out/f'arrays/bootstrap/{sid}.npz',**boot,arm_order=np.array(STRATEGIES),contrast_order=np.array([d['id'] for d in c['contrasts']]))
        record['file']=str(Path(record['file']).relative_to(out));registry.append(record)
        record=save_arrays(out/f'arrays/paired/{sid}.npz',**paired)
        record['file']=str(Path(record['file']).relative_to(out));registry.append(record)
        if sid==c['scenarios'][0]['id']:baseline_boot=boot
        for row in arm+delta:
            ratio=row['bootstrap_to_analytic_mean_se_ratio']
            se_diagnostics.append(dict(scenario_id=sid,id=row.get('strategy',row.get('contrast')),
                ratio=ratio,outside_0p5_to_1p5=ratio is not None and not .5<=ratio<=1.5))
    write_csv(out/'tables/scenario_metrics.csv',metrics);write_csv(out/'tables/contrasts.csv',contrasts)
    print(f"Independent baseline check with seed {c['validation']['repeat_seed']} (not used in reported results)",flush=True)
    repeat,repeated,z2=repeat_baseline(c,engines[c['scenarios'][0]['id']],baseline_boot)
    repeat['innovation_raw_sha256']=raw_hash(z2)
    for strategy,v in repeated.items():
        record=save_arrays(out/f'arrays/repeat_baseline/{strategy}.npz',**v.outcome_arrays(f"validation_seed{c['validation']['repeat_seed']}"))
        record['file']=str(Path(record['file']).relative_to(out));registry.append(record)
    if any(x['status']!='passed' for x in repeat['mean_checks']+repeat['moment_diagnostics']):
        raise AssertionError('Independent-seed diagnostic failed; seeds are not changed to obtain a pass')
    supp_arms,supp_contrasts,supp_records=run_supplementary(out,c,z,indices,engines[c['scenarios'][0]['id']])
    registry+=supp_records
    write_json(out/'arrays/registry.json',dict(array_hash_format='SHA-256 of C-contiguous little-endian raw array bytes',artifacts=registry))
    counts={k:sum(a['invariant_violations'][k] for a in allpaths) for k in allpaths[0]['invariant_violations']}
    primary_paths=sum(a['paths'] for a in allpaths);n_full=deterministic['counts']['full_path_examples']
    sv=deterministic['scalar_vector_checks']
    properties=[
        dict(id='resource_conservation',status='passed',checked_paths=primary_paths+n_full,
            max_normalized_identity_error=max([a['max_normalized_identity_error'] for a in allpaths]+[a['normalized_error'] for a in deterministic['fixture_identity']]),
            maximum_absolute_residual_sek=max(a['accounting_max_absolute_residual_sek'] for a in allpaths)),
        dict(id='runoff_equivalence',status='passed',checked_paths=primary_paths+n_full,
            max_normalized_error=max([a['max_normalized_runoff_error'] for a in allpaths]+[a['normalized_error'] for a in deterministic['fixture_runoff']])),
        dict(id='scalar_vector_agreement',status='passed',checked_paths=sum(a['paths'] for a in sv),
            checked_fields=sum(a['checked_fields'] for a in sv),discrete_fields_checked=sum(a['discrete_fields_checked'] for a in sv),
            max_normalized_error=max(a['max_normalized_error'] for a in sv),discrete_mismatches=sum(a['discrete_mismatches'] for a in sv)),
        dict(id='no_tax_general_equality',status='passed',checked_paths=deterministic['counts']['no_tax_paths'],
            max_pairwise_abs_W_difference_sek=deterministic['no_tax_max_abs_W_difference_sek']),
        dict(id='state_and_event_invariants',status='passed',checked_paths=primary_paths+n_full,
            **counts,state_observations=sum(a['state_observations'] for a in allpaths)),
        dict(id='variational_es_agreement',status='passed',checked_examples=deterministic['counts']['variational_es_examples'],
            max_absolute_es_difference=deterministic['variational_es_max_absolute_difference']),
        dict(id='return_moment_diagnostics',status='passed',checked_models=len(moments),checked_moments=sum(len(m['checks']) for m in moments),
            max_absolute_standardized_discrepancy=max(x['standardized_discrepancy'] for m in moments for x in m['checks'])),
        dict(id='baseline_repeat_seed',status='passed',seed=repeat['seed'],checked_mean_estimates=len(repeat['mean_checks']),
            max_mean_difference_in_combined_standard_errors=repeat['max_mean_difference_in_combined_standard_errors']),
        dict(id='configuration_integrity',status='passed',unique_configurations=len(c['scenarios']),strategies=len(STRATEGIES),
            arm_configurations=len(metrics),primary_paths=int(len(z)),bootstrap_resamples=int(len(indices)))]
    assert {p['id'] for p in properties}=={p['id'] for p in f['property_tests']}
    validation=dict(status='passed',counts=dict(unit_examples_passed=deterministic['counts']['unit_examples'],
            full_path_examples_passed=n_full,property_requirements_passed=len(properties),
            primary_strategy_path_outcomes=primary_paths,configurations=len(c['scenarios']),
            supplementary_experiments=len({r['experiment_id'] for r in supp_contrasts})),
        reference_checks=deterministic,all_path_checks=allpaths,property_tests=properties,price_moments=moments,
        repeat_baseline=repeat,bootstrap_se_diagnostics=se_diagnostics,
        fixture_tolerances=dict(money_atol_sek=c['validation']['unit_money_atol_sek'],shares_and_dimensionless_atol=c['validation']['dimensionless_atol'],rtol=c['validation']['relative_tolerance']),
        random_path_tolerances=dict(money_atol_sek=c['validation']['path_money_atol_sek'],shares_and_dimensionless_atol=c['validation']['dimensionless_atol'],rtol=c['validation']['relative_tolerance']),
        seconds=time.perf_counter()-start)
    write_json(out/'validation/validation_results.json',validation)
    from .report import generate_outputs
    print('Tables, figures, research note and appendix',flush=True)
    generate_outputs(out,c,metrics,contrasts,engines[c['scenarios'][0]['id']],validation,supp_contrasts,supp_arms)
    meta['measured_accounting_residual']=dict(max_absolute_residual_sek=properties[0]['maximum_absolute_residual_sek'],
        note='Measured in this run and environment; floating-point residuals can differ across platforms.')
    meta['run_finished_utc']=datetime.now(timezone.utc).isoformat();meta['seconds']=time.perf_counter()-start;meta['status']='passed'
    write_json(out/'metadata/run_metadata.json',meta)
    print(f'Completed: {out.resolve()} ({time.perf_counter()-start:.1f} seconds)',flush=True)

def main():
    parser=argparse.ArgumentParser(description='Run the complete study and write all results to OUTPUT.')
    parser.add_argument('--output',type=Path,default=ROOT/'reproduction');args=parser.parse_args()
    if args.output.resolve()==(ROOT/'outputs').resolve():parser.error('outputs/ holds the reference results; choose another directory')
    try:run_study(args.output)
    except Exception as exc:
        write_json(args.output/'validation/failure.json',dict(status='failed',exception=repr(exc),timestamp_utc=datetime.now(timezone.utc).isoformat()))
        raise

if __name__=='__main__':main()
