"""Annual signed tax assessments. No per-trade refunds and no netting across tax years.

Signed tax is positive for an amount owed and negative for a credit. The capital-deficit
threshold and the usable reduction capacity apply to one individual taxpayer per tax year.
"""
import numpy as np

DEFICIT_THRESHOLD_SEK = 100000.
TAX_MODES = ('sweden2026', 'symmetric30', 'none', 'sweden2026_no_deficit_threshold')

def annual_ad_tax(g, capacity=None, mode='sweden2026'):
    """Tax on one year's net realized depå gain g.

    'sweden2026': 30% on positive net gains; 70% of a net loss forms the capital deficit,
    reduced at 30% up to 100,000 SEK of deficit and 21% above it, capped by capacity.
    'sweden2026_no_deficit_threshold': counterfactual used only in the supplementary
    analysis; the deficit is reduced at 30% without the 100,000 SEK threshold, i.e. a
    constant 21% relief on residual raw losses.
    'symmetric30': counterfactual 30% tax or credit. 'none': validation only.
    """
    g = np.asarray(g,dtype=np.float64)
    if not np.isfinite(g).all(): raise ValueError("Nonfinite gain")
    if capacity is not None and (not np.isfinite(capacity) or capacity < 0): raise ValueError("Invalid capacity")
    if mode == 'none': return np.zeros_like(g)
    if mode == 'symmetric30': return .30*g
    if mode not in ('sweden2026', 'sweden2026_no_deficit_threshold'): raise ValueError(f"Unsupported tax mode: {mode}")
    x = np.where(g>=0,g,.7*g)
    deficit = np.maximum(-x,0.)
    if mode == 'sweden2026':
        credit = .30*np.minimum(deficit,DEFICIT_THRESHOLD_SEK)+.21*np.maximum(deficit-DEFICIT_THRESHOLD_SEK,0.)
    else:
        credit = .30*deficit
    if capacity is not None: credit = np.minimum(credit,capacity)
    return .30*np.maximum(x,0.)-credit

def isk_assessment(quarter_values, deposits, rate=.01065, allowance=300000.):
    base = (np.sum(quarter_values,axis=-1)+deposits)/4
    return base, rate*np.maximum(base-allowance,0.)

def isk_snapshot(shares, price, cash):
    return shares*price+cash
