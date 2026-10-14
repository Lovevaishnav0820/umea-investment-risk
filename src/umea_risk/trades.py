"""Purchases and sales with fees, average acquisition cost, the harvest rule and payment of tax bills."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Trade:
    shares: float
    actual_basis: float
    cash: float
    quantity: float=0.
    fee: float=0.
    net_sale_proceeds: float=0.
    actual_basis_removed: float=0.
    deduction_selected: float=0.
    deduction_method: str='average_cost'
    gain: float=0.

def _valid(n,B,C,S,c):
    if not all(math.isfinite(x) for x in (n,B,C,S,c)) or min(n,B,C)<0 or S<=0 or not 0<=c<1:
        raise ValueError("Invalid trade state")

def buy(n,B,C,A,S,c,ad=True):
    _valid(n,B,C,S,c)
    if not math.isfinite(A) or not 0<=A<=C: raise ValueError("Budget exceeds cash")
    q=A/((1+c)*S)
    return Trade(n+q,B+A if ad else 0.,C-A,q,q*S*c)

def sell(n,B,C,q,S,c,ad=True,alternative=True):
    _valid(n,B,C,S,c)
    if not math.isfinite(q) or not 0<=q<=n: raise ValueError("Sale exceeds shares")
    if q==0: return Trade(n,B,C)
    net=q*S*(1-c); removed=B*q/n if ad else 0.
    alt=.20*net if alternative and ad else 0.
    deduction=max(removed,alt) if ad else 0.
    method='20pct_proceeds' if ad and alt>removed else 'average_cost' if ad else 'not_applicable'
    remaining_n,remaining_B=(0.,0.) if q==n else (n-q,B-removed if ad else 0.)
    return Trade(remaining_n,remaining_B,C+net,q,q*S*c,net,removed,deduction,method,net-deduction if ad else 0.)

def harvest_trigger(shares,basis,price,cost_per_leg,threshold):
    return (shares>0) & (shares*price*(1-cost_per_leg)<(1-threshold)*basis)

@dataclass(frozen=True)
class Funding:
    shares: float
    actual_basis: float
    cash: float
    bank: float
    external_funding: float
    funding_failure: bool
    account_open: bool
    signed_bill_settled: float
    shares_sold: float=0.
    fee: float=0.

def fund_positive_bill(bill,cash,shares,basis,price,cost_per_leg,bank,
                       external_funding,strategy,account_open):
    if bill<0 or not math.isfinite(bill): raise ValueError("Expected positive bill")
    B=0. if basis is None else basis
    q=fee=0.
    if account_open:
        if strategy!='ISK_HOLD' and bill>cash: raise AssertionError("Unsupported interim positive AD bill")
        paid=min(cash,bill); cash-=paid; remaining=bill-paid
        if remaining>0 and shares>0:
            resources=shares*price*(1-cost_per_leg)
            # Resource comparison is exact; tolerance never discards a real funding gap.
            q=shares if remaining>=resources else remaining/(price*(1-cost_per_leg))
            partial=remaining<resources
            t=sell(shares,B,cash,q,price,cost_per_leg,ad=False)
            shares,B,cash,fee=t.shares,t.actual_basis,t.cash,t.fee
            if partial:
                # This sale was defined to fund exactly this bill. Clear only
                # its arithmetic residual, never a genuine exhausted-account gap.
                residual=cash-remaining
                if abs(residual)>1e-8+1e-10*max(cash,remaining):raise ArithmeticError("Funding sale residual")
                cash=0.;remaining=0.
            else:
                paid=min(cash,remaining); cash-=paid; remaining-=paid
        if shares==0 and cash==0: account_open=False
    else:
        paid=min(bank,bill); bank-=paid; remaining=bill-paid
    external_funding+=remaining
    return Funding(shares,B,cash,bank,external_funding,remaining>0,account_open,bill,q,fee)
