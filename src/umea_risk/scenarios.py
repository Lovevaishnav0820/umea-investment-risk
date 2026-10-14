"""Random numbers and the transformation of standard-normal innovations into price paths."""
import hashlib
import numpy as np

def raw_hash(a):
    a=np.asarray(a)
    a=np.ascontiguousarray(a.astype(a.dtype.newbyteorder('<'),copy=False))
    return hashlib.sha256(a.tobytes(order='C')).hexdigest()

def generate_innovations(seed=20261012,n=20000):
    return np.random.Generator(np.random.PCG64(seed)).standard_normal((n,24))

def generate_bootstrap_indices(n=20000, resamples=2000, seed=20261013):
    return np.random.Generator(np.random.PCG64(seed)).integers(0,n,size=(resamples,n),dtype=np.int64)

def ledger_indices():
    return np.sort(np.random.Generator(np.random.PCG64(20261014)).choice(20000,6,replace=False))

def prices_from_innovations(z,p):
    m=p['annual_expected_simple_price_return']; sigma=p['annual_diffusion_volatility']; S0=p['initial_price']
    x=(np.log1p(m)-.5*sigma**2)/12+sigma/np.sqrt(12)*z
    with np.errstate(over='raise',under='raise',invalid='raise'):
        prices=np.column_stack((np.full(len(z),S0),S0*np.exp(np.cumsum(x,axis=1))))
    validate_prices(prices,S0)
    return prices

def validate_prices(prices,S0):
    a=np.asarray(prices,dtype=np.float64)
    if a.shape[-1]!=25 or not np.isfinite(a).all() or not (a>0).all() or not (a[...,0]==S0).all():
        raise ValueError("Expected 25 strictly positive finite prices starting at S0")
    return a

def price_moments(S0,m,sigma,months=24):
    return dict(expected_price_12=S0*(1+m),expected_price_24=S0*(1+m)**(months/12),
        annual_log_drift=np.log1p(m),monthly_log_mean=(np.log1p(m)-sigma*sigma/2)/12,
        monthly_log_variance=sigma*sigma/12)
