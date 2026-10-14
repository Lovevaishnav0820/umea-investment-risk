"""Rejection of invalid parameters, JSON input and changes to the fixed study configuration."""
import copy
import json
import numpy as np
import pytest
from umea_risk.config import BASELINE, load_config, read_json, validate_parameters
from umea_risk.scenarios import validate_prices,prices_from_innovations
from umea_risk.tax import annual_ad_tax

@pytest.mark.parametrize('key,value',[('annual_expected_simple_price_return',-1),('annual_diffusion_volatility',-1),
    ('cost_per_leg',1),('harvest_loss_threshold',-1),('initial_wealth_sek',0),('initial_price',0),
    ('credit_capacity_sek',-1),('horizon_months',25),('settlement_lag_months',3),('tax_mode','other'),
    ('tax_mode','none'),('tax_mode','sweden2026_no_deficit_threshold'),('isk_tax_rate',0.02),('dividend_yield',.01),('cash_interest_rate',.01),
    ('cost_per_leg',float('nan'))])
def test_reject_invalid_parameter(key,value):
    with pytest.raises(ValueError):validate_parameters(dict(BASELINE,**{key:value}))

@pytest.mark.parametrize('text',['{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}','{"a":1e999}'])
def test_reject_invalid_json(tmp_path,text):
    p=tmp_path/'invalid.json';p.write_text(text)
    with pytest.raises(ValueError):read_json(p)

@pytest.mark.parametrize('change',['resolution','unknown_override','duplicate_id','order','seed','tax_rate',
    'override_value','calendar','validation_bound','estimand','supplementary'])
def test_reject_changed_configuration(tmp_path,change):
    c=copy.deepcopy(load_config())
    if change=='resolution':c['scenarios'][1]['parameters']['cost_per_leg']=.002
    if change=='unknown_override':c['scenarios'][1]['overrides']['new_parameter']=1
    if change=='duplicate_id':c['scenarios'][1]['id']=c['scenarios'][0]['id']
    if change=='order':c['scenarios'].reverse()
    if change=='seed':c['simulation']['seed']+=1
    if change=='tax_rate':c['tax_constants']['capital_gains_rate']=.4
    if change=='override_value':
        c['scenarios'][1]['overrides']['cost_per_leg']=.002
        c['scenarios'][1]['parameters']['cost_per_leg']=.002
    if change=='calendar':c['calendar']['opening_snapshot_months'][1]=5
    if change=='validation_bound':c['validation']['relative_tolerance']=.1
    if change=='estimand':c['metrics']['es_alpha']=.9
    if change=='supplementary':c['supplementary_experiments']['experiments'][0]['overrides']['initial_wealth_sek']=150000.
    p=tmp_path/'c.json';p.write_text(json.dumps(c))
    with pytest.raises(ValueError):load_config(p)

def test_reject_invalid_prices_and_overflow():
    for x in (0.,-1.,float('nan'),float('inf')):
        a=np.full(25,100.);a[12]=x
        with pytest.raises(ValueError):validate_prices(a,100.)
    with pytest.raises((FloatingPointError,ValueError)):
        prices_from_innovations(np.full((2,24),1e6),BASELINE)
    with pytest.raises(ValueError):annual_ad_tax(1.,mode='unknown')
