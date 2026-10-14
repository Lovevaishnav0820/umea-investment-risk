"""Scalar engine: one price path at a time, with a complete event ledger.

Within each month the order is: quarter-opening value (ISK), price return, settlement of
taxes that fall due, the month-12 harvest, the month-24 sale, the annual assessment and,
with a zero lag, its settlement. An assessed tax is not cash until it is settled.
After month 24 only tax settlements occur.
"""
from dataclasses import dataclass, asdict
import math
from .config import validate_parameters, STRATEGIES
from .scenarios import validate_prices
from .tax import annual_ad_tax, isk_assessment
from .trades import buy, sell, harvest_trigger

PHASES = {'initial':0,'snapshot':1,'return':2,'old_settlement':3,
          'harvest':4,'liquidation':5,'assessment':6,'zero_lag_settlement':7,'runoff':8}

@dataclass
class State:
    n: float=0.
    B: float=0.
    C: float=0.
    bank: float=0.
    F: float=0.
    g: float=0.
    fees_total: float=0.
    price_pnl: float=0.
    buy_count: int=0
    sell_count: int=0
    harvested: bool=False
    funding_failure: bool=False
    funding_failure_month: int|None=None
    closure_month: int|None=None
    account_open: bool=True
    trading_enabled: bool=True

class ScalarEngine:
    def __init__(self,prices,p,strategy,scenario='validation',path_id=0):
        validate_parameters(p,validation=True)
        self.prices=validate_prices(prices,p['initial_price'])
        if self.prices.ndim!=1 or strategy not in STRATEGIES: raise ValueError("Scalar input/strategy")
        self.p=p; self.strategy=strategy; self.ad=strategy!='ISK_HOLD'
        self.state=State(); self.records=[]; self.ledger=[]; self.checkpoints={}
        self.quarters=[[0.]*4 for _ in range(2)]; self.deposits=[p['initial_wealth_sek'],0.]
        self.bases=[None,None]; self.annual_g=[0.,0.]; self.credit_states=[]
        self.scenario=scenario; self.path_id=path_id; self.month=0; self.price=float(prices[0]); self.phase='initial'
        self.min_state={k:0. for k in ('n','B','C','bank','F')}
        self.pre_liquidation_n=None; self.pre_runoff_value=None

    def emit(self,event,before,**data):
        s=self.state
        row=dict(scenario_or_fixture=self.scenario,strategy=self.strategy,path_id=self.path_id,
            month=self.month,phase=self.phase,phase_order=PHASES[self.phase],sequence=len(self.ledger),
            event=event,price=self.price,cumulative_price_pnl=s.price_pnl,
            model_tax_year=1 if self.month<=12 else 2)
        for k in ('n','B','C','bank','F'):
            row[k+'_before']=before[k]; row[k+'_after']=getattr(s,k)
        for k in ('trade_quantity','gross_value','net_proceeds_or_budget','actual_basis_removed',
                  'deduction_selected','deduction_method','realized_gain','fee','assessed_tax',
                  'due_month','settled_month','snapshot_value'):
            row[k]=data.get(k)
        row.update(data); self.ledger.append(row)
        self.check_state()

    def check_state(self):
        for k in ('n','B','C','bank','F'):
            x=getattr(self.state,k)
            if not math.isfinite(x) or x<0: raise AssertionError(f"{k} invalid at month {self.month}: {x}")
            self.min_state[k]=min(self.min_state[k],x)
        for k in ('g','fees_total','price_pnl'):
            if not math.isfinite(getattr(self.state,k)): raise AssertionError(f"Nonfinite {k}")
        if self.state.B and not self.ad: raise AssertionError("ISK basis must be zero")

    def purchase(self,A,event):
        if A==0: return
        if not self.state.trading_enabled or self.month>=24: raise AssertionError("Forbidden purchase")
        before=asdict(self.state);s=self.state
        t=buy(s.n,s.B,s.C,A,self.price,self.p['cost_per_leg'],self.ad)
        s.n,s.B,s.C=t.shares,t.actual_basis,t.cash;s.fees_total+=t.fee;s.buy_count+=1
        self.emit(event,before,trade_quantity=t.quantity,gross_value=t.quantity*self.price,
                  net_proceeds_or_budget=A,fee=t.fee)

    def sale(self,q,event):
        if q==0:return
        if self.month>24:raise AssertionError("Runoff trade")
        before=asdict(self.state);s=self.state
        t=sell(s.n,s.B,s.C,q,self.price,self.p['cost_per_leg'],self.ad,self.p['allow_20pct_proceeds_deduction'])
        s.n,s.B,s.C=t.shares,t.actual_basis,t.cash;s.g+=t.gain;s.fees_total+=t.fee;s.sell_count+=1
        self.emit(event,before,trade_quantity=q,gross_value=q*self.price,net_proceeds_or_budget=t.net_sale_proceeds,
            actual_basis_removed=t.actual_basis_removed,deduction_selected=t.deduction_selected,
            deduction_method=t.deduction_method,realized_gain=t.gain,fee=t.fee)

    def close(self):
        s=self.state;s.account_open=False;s.trading_enabled=False
        if s.closure_month is None:s.closure_month=self.month

    def settle(self,record):
        assert not record['settled'] and record['due_month']==self.month
        s=self.state;amount=record['assessed_amount']
        if amount<0:
            before=asdict(s)
            invest=self.month<24 and s.trading_enabled and s.account_open
            if invest:s.C-=amount
            else:s.bank-=amount
            self.emit('credit_receipt',before,assessed_tax=amount,due_month=record['due_month'],
                      settled_month=self.month,model_tax_year=record['year'])
            if invest:self.purchase(s.C,'credit_reinvestment')
            self.credit_states.append(dict(month=self.month,n=s.n,B=s.B))
        elif amount>0:
            before=asdict(s);remaining=amount
            if s.account_open:
                paid=min(s.C,remaining);s.C-=paid;remaining-=paid
                if remaining>0:
                    if self.ad:raise AssertionError("Unexpected interim positive AD bill")
                    resources=s.n*self.price*(1-self.p['cost_per_leg'])
                    partial=remaining<resources
                    q=s.n if remaining>=resources else remaining/(self.price*(1-self.p['cost_per_leg']))
                    self.sale(q,'tax_funding_sale')
                    before=asdict(s)
                    if partial:
                        residual=s.C-remaining
                        if abs(residual)>1e-8+1e-10*max(s.C,remaining):raise ArithmeticError("Funding sale residual")
                        s.C=0.;remaining=0.
                    else:
                        paid=min(s.C,remaining);s.C-=paid;remaining-=paid
                if s.n==0 and s.C==0:self.close()
            else:
                paid=min(s.bank,remaining);s.bank-=paid;remaining-=paid
            if remaining>0:
                s.F+=remaining;s.funding_failure=True
                if s.funding_failure_month is None:s.funding_failure_month=self.month
                self.close()
            self.emit('bill_payment',before,assessed_tax=amount,due_month=record['due_month'],
                      settled_month=self.month,model_tax_year=record['year'],household_payment=remaining)
        else:
            self.emit('zero_settlement',asdict(s),assessed_tax=0.,due_month=record['due_month'],
                      settled_month=self.month,model_tax_year=record['year'])
        record['settled']=True;record['settled_month']=self.month

    def assess(self,year):
        s=self.state
        self.annual_g[year-1]=s.g
        if self.ad:
            amount=float(annual_ad_tax(s.g,self.p['credit_capacity_sek'],self.p['tax_mode']))
            if year==1 and amount>0:raise AssertionError("Unexpected positive AD Y1 tax")
        else:
            rate=0. if self.p['tax_mode']=='none' else self.p['isk_tax_rate']
            base,amount=isk_assessment(self.quarters[year-1],self.deposits[year-1],rate,self.p['isk_allowance_sek'])
            self.bases[year-1]=float(base);amount=float(amount)
        record=dict(year=year,assessed_month=self.month,assessed_amount=amount,
            due_month=self.month+self.p['settlement_lag_months'],settled=False,settled_month=None,annual_net_gain=s.g)
        self.records.append(record)
        self.emit('annual_assessment',asdict(s),assessed_tax=amount,due_month=record['due_month'],model_tax_year=year,
                  annual_net_gain=s.g)
        s.g=0.
        if record['due_month']==self.month:
            self.phase='zero_lag_settlement';self.settle(record)

    def run(self):
        s=self.state;W0=self.p['initial_wealth_sek']
        if not self.ad:self.emit('opening_snapshot',asdict(s),snapshot_value=0.)
        before=asdict(s);s.C=W0;self.emit('initial_deposit',before,deposit=W0)
        self.purchase(W0,'initial_purchase');self.checkpoints[0]=asdict(s)
        for j in range(1,25):
            self.month=j
            if not self.ad and j in (4,7,10,13,16,19,22):
                self.phase='snapshot';value=s.n*self.prices[j-1]+s.C if s.account_open else 0.
                year=(j-1)//12;quarter=((j-1)%12)//3;self.quarters[year][quarter]=float(value)
                self.emit('opening_snapshot',asdict(s),snapshot_value=float(value))
            self.phase='return';before=asdict(s);s.price_pnl+=s.n*(self.prices[j]-self.prices[j-1]);self.price=float(self.prices[j])
            self.emit('price_return',before)
            self.phase='old_settlement'
            for record in self.records:
                if not record['settled'] and record['due_month']==j:self.settle(record)
            if j==12 and self.strategy=='AD_HARVEST':
                self.phase='harvest'
                if harvest_trigger(s.n,s.B,self.price,self.p['cost_per_leg'],self.p['harvest_loss_threshold']):
                    self.sale(s.n,'harvest_sale');self.purchase(s.C,'harvest_repurchase');s.harvested=True
            if j==24:
                self.phase='liquidation';self.pre_liquidation_n=s.n
                self.sale(s.n,'terminal_sale')
                before=asdict(s);s.bank+=s.C;s.C=0.;self.close();self.emit('account_close',before)
            if j in (12,24):
                self.phase='assessment';self.assess(j//12)
            self.checkpoints[j]=asdict(s)
        self.pre_runoff_value=s.bank-s.F-sum(r['assessed_amount'] for r in self.records if not r['settled'])
        for j in range(25,25+self.p['settlement_lag_months']):
            self.month=j;self.phase='runoff'
            for record in self.records:
                if not record['settled'] and record['due_month']==j:self.settle(record)
            self.checkpoints[j]=asdict(s)
        assert all(r['settled'] for r in self.records)
        return self

    def fixture_actual(self):
        s=self.state;records=self.records
        out=dict(year1_tax=records[0]['assessed_amount'],year2_tax=records[1]['assessed_amount'],
            year1_base=self.bases[0],year2_base=self.bases[1],terminal_net_outcome=s.bank-s.F,
            external_funding=s.F,fees_total=s.fees_total,price_pnl=s.price_pnl,harvested=s.harvested,
            funding_failure=s.funding_failure,funding_failure_month=s.funding_failure_month,
            closure_month=s.closure_month,terminal_bank=s.bank,
            tax_due_months=[r['due_month'] for r in records],assessed_months=[r['assessed_month'] for r in records],
            settled_records_after_runoff=sum(r['settled'] for r in records),
            unsettled_records_after_runoff=sum(not r['settled'] for r in records),terminal_shares=s.n,
            terminal_actual_basis=s.B,terminal_account_cash=s.C,
            trades_at_or_after_month25=sum(row['trade_quantity'] is not None and row['month']>=25 for row in self.ledger),
            year3_isk_tax=sum(r['assessed_amount'] for r in records if r['year']>=3 and not self.ad),
            year1_snapshots=self.quarters[0],year2_snapshots=self.quarters[1],year1_deposits=self.deposits[0],year2_deposits=self.deposits[1],
            shares_end_month12=self.checkpoints[12]['n'],basis_end_month12=self.checkpoints[12]['B'],
            shares_end_month17=self.checkpoints[17]['n'],shares_before_liquidation_month24=self.pre_liquidation_n,
            buy_count_month24=sum(row['event'] in ('initial_purchase','harvest_repurchase','credit_reinvestment') and row['month']==24 for row in self.ledger),
            credit_receipts_months=[a['month'] for a in self.credit_states])
        if self.credit_states:
            out['shares_after_credit']=self.credit_states[0]['n'];out['basis_after_credit']=self.credit_states[0]['B']
        return out

def run_scalar(prices,p,strategy,scenario='validation',path_id=0):
    return ScalarEngine(prices,p,strategy,scenario,path_id).run()
