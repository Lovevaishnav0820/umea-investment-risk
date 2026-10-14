"""Check the files written by a complete run: arrays, tables, ledgers, figures and documents."""
import csv
import sys
from pathlib import Path
import time
import numpy as np
from PIL import Image
from pypdf import PdfReader
from . import __version__
from .config import ROOT,load_config,read_json,STRATEGIES,supplementary_experiments
from .note_content import AUTHOR,REVISION_DATE,FIGURES,NOTE_PAGES,APPENDIX_PAGES
from .metrics import empirical_es,interval
from .scenarios import raw_hash
from .io import write_json,file_hash
from .compare import write_manifest

REQUIRED_PATH_FIELDS=('scenario_id strategy path_id W0 W net_return loss F funding_failure funding_failure_month '
    'closure_month harvested fees_total trade_count buy_count sell_count price_pnl tax_y1 tax_y2 isk_base_y1 '
    'isk_base_y2 final_bank pending_tax_after_runoff accounting_residual').split()
REQUIRED_ARM_FIELDS=('n_paths mean_net_return mean_ci_low mean_ci_high mean_mc_se es95_loss es_ci_low es_ci_high '
    'count_loss probability_loss count_nonpositive_W probability_nonpositive_W count_funding probability_funding '
    'zero_event_upper95_if_applicable mean_F_over_W0 max_F_over_W0 mean_fees_sek mean_fees_over_W0 '
    'harvest_count harvest_frequency mean_W_sek').split()
REQUIRED_DELTA_FIELDS=('arm_a arm_b role delta_mean delta_mean_ci_low delta_mean_ci_high delta_mean_mc_se '
    'delta_es95 delta_es_ci_low delta_es_ci_high paired_median paired_q05 paired_q95 paired_probability_positive '
    'triggered_count triggered_paired_mean').split()
REQUIRED_LEDGER_FIELDS=('scenario_or_fixture strategy path_id month phase sequence event price n_before n_after '
    'B_before B_after C_before C_after bank_before bank_after F_before F_after trade_quantity gross_value '
    'net_proceeds_or_budget actual_basis_removed deduction_selected deduction_method realized_gain fee '
    'cumulative_price_pnl model_tax_year assessed_tax due_month settled_month snapshot_value').split()

def validate_artifacts(out=ROOT/'reproduction'):
    out=Path(out);start=time.perf_counter();c=load_config()
    registry=read_json(out/'arrays/registry.json');checked=0
    for item in registry['artifacts']:
        p=out/item['file'];assert file_hash(p)==item['file_sha256'],f'Serialized file hash: {p}'
        with np.load(p,allow_pickle=False) as arrays:
            assert set(arrays.files)==set(item['arrays']),f'Array registry: {p}'
            for k,info in item['arrays'].items():
                a=arrays[k];checked+=1
                assert list(a.shape)==info['shape'] and str(a.dtype)==info['dtype'],f'Shape/dtype: {p}/{k}'
                assert raw_hash(a)==info['raw_sha256'],f'Raw-byte hash: {p}/{k}'
    n_paths=c['simulation']['paths'];draws=c['monte_carlo_intervals']['resamples']
    arms=list(csv.DictReader((out/'tables/scenario_metrics.csv').open()))
    deltas=list(csv.DictReader((out/'tables/contrasts.csv').open()))
    assert [(r['scenario_id'],r['strategy']) for r in arms]==[(s['id'],a) for s in c['scenarios'] for a in STRATEGIES]
    assert [(r['scenario_id'],r['contrast']) for r in deltas]==[(s['id'],d['id']) for s in c['scenarios'] for d in c['contrasts']]
    assert all(set(REQUIRED_ARM_FIELDS)<=r.keys() for r in arms)
    assert all(set(REQUIRED_DELTA_FIELDS)<=r.keys() for r in deltas)
    residuals=[];path_records=0
    def near(a,b):
        error=abs(float(a)-float(b));residuals.append(error)
        assert error<=1e-12+1e-10*max(abs(float(a)),abs(float(b)))
    def check_intervals(boot,stat,j,row,low,high):
        bounds=interval(boot[stat][:,j]);near(row[low],bounds[0]);near(row[high],bounds[1])
    for scenario in c['scenarios']:
        sid=scenario['id'];W0=scenario['parameters']['initial_wealth_sek'];returns={};losses={}
        with np.load(out/f'arrays/bootstrap/{sid}.npz',allow_pickle=False) as boot:
            for field in ('arm_mean','arm_es','delta_mean','delta_es'):assert boot[field].shape==(draws,3)
            for j,strategy in enumerate(STRATEGIES):
                r=next(x for x in arms if x['scenario_id']==sid and x['strategy']==strategy)
                with np.load(out/f'arrays/outcomes/{sid}__{strategy}.npz',allow_pickle=False) as a:
                    assert set(REQUIRED_PATH_FIELDS)<=set(a.files)
                    assert str(a['scenario_id'])==sid and str(a['strategy'])==strategy
                    assert np.array_equal(a['path_id'],np.arange(n_paths));assert np.all(a['W0']==W0)
                    assert np.array_equal(a['W'],a['final_bank']-a['F']);assert np.all(a['pending_tax_after_runoff']==0)
                    assert np.array_equal(a['net_return'],a['W']/W0-1.) and np.array_equal(a['loss'],-a['net_return'])
                    returns[strategy]=a['net_return'];losses[strategy]=a['loss'];path_records+=len(a['W'])
                    near(r['mean_net_return'],a['net_return'].mean());near(r['es95_loss'],empirical_es(a['loss']))
                    check_intervals(boot,'arm_mean',j,r,'mean_ci_low','mean_ci_high');check_intervals(boot,'arm_es',j,r,'es_ci_low','es_ci_high')
                    assert int(r['n_paths'])==len(a['W'])
                    for field,observed in [('count_loss',np.count_nonzero(a['W']<W0)),('count_nonpositive_W',np.count_nonzero(a['W']<=0)),
                        ('count_funding',np.count_nonzero(a['F']>0)),('harvest_count',a['harvested'].sum())]:assert int(r[field])==observed
                    assert np.array_equal(a['funding_failure'],a['F']>0)
            with np.load(out/f'arrays/paired/{sid}.npz',allow_pickle=False) as paired:
                for j,d in enumerate(c['contrasts']):
                    r=next(x for x in deltas if x['scenario_id']==sid and x['contrast']==d['id'])
                    diff=returns[d['a']]-returns[d['b']]
                    assert np.array_equal(paired[d['id']],diff)
                    near(r['delta_mean'],diff.mean());near(r['delta_es95'],empirical_es(losses[d['a']])-empirical_es(losses[d['b']]))
                    check_intervals(boot,'delta_mean',j,r,'delta_mean_ci_low','delta_mean_ci_high')
                    check_intervals(boot,'delta_es',j,r,'delta_es_ci_low','delta_es_ci_high')
    supp_arms=list(csv.DictReader((out/'supplementary/supplementary_metrics.csv').open()))
    supp_deltas=list(csv.DictReader((out/'supplementary/supplementary_contrasts.csv').open()))
    experiments=supplementary_experiments(c)
    assert [(r['experiment_id'],r['strategy']) for r in supp_arms]==[(e['id'],a) for e in experiments for a in STRATEGIES]
    assert [(r['experiment_id'],r['contrast']) for r in supp_deltas]==[(e['id'],d['id']) for e in experiments for d in c['contrasts']]
    for e in experiments:
        W0=e['parameters']['initial_wealth_sek'];returns={}
        with np.load(out/f"arrays/supplementary/{e['id']}__bootstrap.npz",allow_pickle=False) as boot:
            for j,strategy in enumerate(STRATEGIES):
                r=next(x for x in supp_arms if x['experiment_id']==e['id'] and x['strategy']==strategy)
                with np.load(out/f"arrays/supplementary/{e['id']}__{strategy}.npz",allow_pickle=False) as a:
                    returns[strategy]=a['net_return'];assert len(a['W'])==n_paths
                    over=int(np.count_nonzero((-0.7*a['annual_net_gains']>100000.).any(axis=1)))
                    assert r['paths_with_annual_deficit_over_100k']==('' if strategy=='ISK_HOLD' else str(over))
                    assert np.array_equal(a['net_return'],a['W']/W0-1.)
                near(r['mean_net_return'],returns[strategy].mean());near(r['es95_loss'],empirical_es(-returns[strategy]))
                check_intervals(boot,'arm_es',j,r,'es_ci_low','es_ci_high')
            for j,d in enumerate(c['contrasts']):
                r=next(x for x in supp_deltas if x['experiment_id']==e['id'] and x['contrast']==d['id'])
                diff=returns[d['a']]-returns[d['b']];near(r['delta_mean'],diff.mean())
                near(r['delta_es95'],empirical_es(-returns[d['a']])-empirical_es(-returns[d['b']]))
                check_intervals(boot,'delta_mean',j,r,'delta_mean_ci_low','delta_mean_ci_high')
                check_intervals(boot,'delta_es',j,r,'delta_es_ci_low','delta_es_ci_high')
                near(float(r['delta_mean_sek']),float(r['delta_mean'])*W0);near(float(r['delta_es95_sek']),float(r['delta_es95'])*W0)
    fixture_ledgers=sorted((out/'ledgers/fixtures').glob('*.csv'));diagnostic_ledgers=sorted((out/'ledgers/diagnostics').glob('*.csv'))
    expected_fixture_ledgers=len(read_json(ROOT/'config/benchmark_fixtures.json')['full_path_fixtures'])
    expected_diagnostic=len(c['scenarios'])*len(STRATEGIES)*c['validation']['ledger_sample_size']
    assert len(fixture_ledgers)==expected_fixture_ledgers and len(diagnostic_ledgers)==expected_diagnostic
    ledger_rows=0
    for p in fixture_ledgers+diagnostic_ledgers:
        rows=list(csv.DictReader(p.open()));ledger_rows+=len(rows);assert rows and set(REQUIRED_LEDGER_FIELDS)<=rows[0].keys()
        for a,b in zip(rows,rows[1:]):
            assert (int(a['month']),int(a['phase_order']),int(a['sequence']))<(int(b['month']),int(b['phase_order']),int(b['sequence']))
            for k in ('n','B','C','bank','F'):assert float(a[k+'_after'])==float(b[k+'_before']),f'Ledger continuity: {p}/{k}'
        records=read_json(p.with_name(p.stem+'_tax_records.json'))
        assert len(records)==2 and all(r['settled'] and r['assessed_month']<=r['settled_month']==r['due_month'] for r in records)
    for stem in FIGURES:
        with Image.open(out/f'figures/{stem}.png') as image:assert image.width>=1000 and image.height>=500;image.verify()
        assert len(PdfReader(out/f'figures/{stem}.pdf').pages)==1
    assert sorted(p.stem for p in (out/'figures').glob('*.png'))==sorted(FIGURES)
    note=PdfReader(out/'note/research_note.pdf');appendix=PdfReader(out/'note/research_appendix.pdf')
    assert len(note.pages)==NOTE_PAGES and len(appendix.pages)==APPENDIX_PAGES
    text='\n'.join(p.extract_text() for p in note.pages)
    for term in ('[MC interval]',f'{draws:,} paired bootstrap draws','configurations with Swedish tax rules','Negative ES95 differences','per individual taxpayer',REVISION_DATE):
        assert term in text,f'Missing from research note: {term}'
    for doc in (note,appendix):
        assert doc.metadata.author==AUTHOR and doc.metadata.title and __version__ in (doc.metadata.creator or '')
    md=(out/'note/research_note.md').read_text()
    assert 'P&amp;L' not in md and all(f'../figures/{stem}.png' in md for stem in FIGURES)
    report=dict(status='passed',array_files_checked=len(registry['artifacts']),arrays_rehashed=checked,
        primary_path_records=path_records,arm_rows=len(arms),contrast_rows=len(deltas),
        supplementary_arm_rows=len(supp_arms),supplementary_contrast_rows=len(supp_deltas),
        fixture_ledgers=len(fixture_ledgers),diagnostic_ledgers=len(diagnostic_ledgers),chronological_ledger_rows=ledger_rows,
        note_pages=len(note.pages),appendix_pages=len(appendix.pages),figures=len(FIGURES),
        max_table_serialization_residual=max(residuals),seconds=time.perf_counter()-start)
    write_json(out/'validation/artifact_validation.json',report)
    write_manifest(out)
    return report

if __name__=='__main__':print(validate_artifacts(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'reproduction'))
