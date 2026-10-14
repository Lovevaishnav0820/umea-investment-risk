"""Vectorized engine: all paths at once, with the same monthly calendar as the scalar engine.

The state transitions are implemented separately from engine.py; the tax functions, the
harvest rule and parameter validation are shared. Optional traces of selected paths record
every event so that the two engines can be compared step by step.
"""
import numpy as np
from .config import validate_parameters, STRATEGIES
from .scenarios import validate_prices
from .tax import annual_ad_tax, isk_assessment
from .trades import harvest_trigger
from .engine import PHASES

class VectorEngine:
    def __init__(self,prices,p,strategy,trace_indices=()):
        validate_parameters(p,validation=True)
        self.prices=validate_prices(prices,p['initial_price'])
        if self.prices.ndim!=2 or strategy not in STRATEGIES:raise ValueError("Vector input/strategy")
        self.p=p;self.strategy=strategy;self.ad=strategy!='ISK_HOLD';self.N=len(prices)
        self.s={k:np.zeros(self.N) for k in ('n','B','C','bank','F','g','fees_total','price_pnl')}
        for k in ('buy_count','sell_count'):self.s[k]=np.zeros(self.N,dtype=np.int64)
        for k in ('harvested','funding_failure'):self.s[k]=np.zeros(self.N,dtype=bool)
        for k in ('account_open','trading_enabled'):self.s[k]=np.ones(self.N,dtype=bool)
        for k in ('funding_failure_month','closure_month'):self.s[k]=np.full(self.N,-1,dtype=np.int64)
        self.quarters=np.zeros((self.N,2,4));self.deposits=np.array([p['initial_wealth_sek'],0.])
        self.bases=np.zeros((self.N,2));self.taxes=np.zeros((self.N,2));self.annual_g=np.zeros((self.N,2))
        self.assessed_months=np.array([12,24]);self.due_months=self.assessed_months+p['settlement_lag_months']
        self.settled_months=np.full((self.N,2),-1,dtype=np.int64)
        self.assessed=np.zeros(2,dtype=bool)
        self.buy_by_month=np.zeros((self.N,25),dtype=np.int64);self.sell_by_month=self.buy_by_month.copy()
        self.trace_indices=np.array(trace_indices,dtype=int);self.history={};self.events=[]
        self.month=0;self.phase='initial';self.price=self.prices[:,0];self.sequence=0
        self.invariants=dict(nonfinite_values=0,negative_asset_state_violations=0,unsettled_records=0,
            post_terminal_trades=0,out_of_order_events=0,unexpected_positive_ad_year1_taxes=0)
        self.state_observations=0;self.min_state={k:0. for k in ('n','B','C','bank','F')}
        self._last_event=(-1,-1,-1)

    def check_state(self):
        self.state_observations+=self.N
        for k,v in self.s.items():
            bad=int(np.count_nonzero(~np.isfinite(v)));self.invariants['nonfinite_values']+=bad
            if bad:raise AssertionError(f"Nonfinite {k} at month {self.month}")
            if k in self.min_state:
                self.min_state[k]=min(self.min_state[k],float(np.min(v)))
                negative=int(np.count_nonzero(v<0));self.invariants['negative_asset_state_violations']+=negative
                if negative:raise AssertionError(f"Negative {k} at month {self.month}")
        if not self.ad and np.any(self.s['B']):raise AssertionError("ISK actual basis")
        closed=~self.s['account_open']
        if np.any(self.s['n'][closed]) or np.any(self.s['C'][closed]):raise AssertionError("Assets in closed account")

    def emit(self,event,before,mask=None,**data):
        if mask is None:mask=np.ones(self.N,dtype=bool)
        order=(self.month,PHASES[self.phase],self.sequence)
        if order<=self._last_event:self.invariants['out_of_order_events']+=self.N;raise AssertionError("Event order")
        self._last_event=order;self.sequence+=1
        if len(self.trace_indices):
            ix=self.trace_indices
            row=dict(month=self.month,phase=self.phase,event=event,mask=mask[ix].copy(),price=self.price[ix].copy())
            for k in ('n','B','C','bank','F'):
                row[k+'_before']=before[k][ix].copy();row[k+'_after']=self.s[k][ix].copy()
            row['cumulative_price_pnl']=self.s['price_pnl'][ix].copy()
            for k,v in data.items():
                a=np.asarray(v)
                row[k]=a[ix].copy() if a.ndim else v
            self.events.append(row)
        self.check_state()

    def before(self):
        # Capture only ledger columns; without a trace these copies are unnecessary.
        return {k:v.copy() for k,v in self.s.items() if k in ('n','B','C','bank','F')} if len(self.trace_indices) else {}

    def purchase(self,budget,event,mask=None):
        s=self.s;A=np.asarray(budget).copy()
        mask=(A>0) if mask is None else mask & (A>0)
        if not np.any(mask):return
        if self.month>=24 or np.any(~s['trading_enabled'][mask]):raise AssertionError("Forbidden purchase")
        if np.any(A[mask]>s['C'][mask]):raise AssertionError("Cash budget")
        before=self.before();A=np.where(mask,A,0.);q=A/((1+self.p['cost_per_leg'])*self.price)
        fee=q*self.price*self.p['cost_per_leg']
        s['n']+=q
        if self.ad:s['B']+=A
        s['C']-=A;s['fees_total']+=fee;s['buy_count']+=mask;self.buy_by_month[:,self.month]+=mask
        self.emit(event,before,mask,trade_quantity=q,gross_value=q*self.price,net_proceeds_or_budget=A,fee=fee)

    def sale(self,quantity,event):
        s=self.s;q=np.asarray(quantity).copy();mask=q>0
        if not np.any(mask):return
        if self.month>24:self.invariants['post_terminal_trades']+=int(mask.sum());raise AssertionError("Runoff trade")
        if np.any(q>s['n']) or np.any(q<0):raise AssertionError("Sale quantity")
        before=self.before();full=mask & (q==s['n']);net=q*self.price*(1-self.p['cost_per_leg'])
        removed=np.zeros(self.N)
        if self.ad:np.divide(s['B']*q,s['n'],out=removed,where=mask)
        alt=.20*net if self.ad and self.p['allow_20pct_proceeds_deduction'] else np.zeros(self.N)
        deduction=np.maximum(removed,alt) if self.ad else np.zeros(self.N)
        method=np.where(alt>removed,'20pct_proceeds','average_cost') if self.ad else np.full(self.N,'not_applicable')
        gain=net-deduction if self.ad else np.zeros(self.N);fee=q*self.price*self.p['cost_per_leg']
        s['n']-=q;s['B']-=removed;s['n'][full]=0.;s['B'][full]=0.
        s['C']+=net;s['g']+=gain;s['fees_total']+=fee;s['sell_count']+=mask;self.sell_by_month[:,self.month]+=mask
        self.emit(event,before,mask,trade_quantity=q,gross_value=q*self.price,net_proceeds_or_budget=net,
            actual_basis_removed=removed,deduction_selected=deduction,deduction_method=method,realized_gain=gain,fee=fee)

    def close(self,mask):
        s=self.s
        first=mask & (s['closure_month']==-1);s['closure_month'][first]=self.month
        s['account_open'][mask]=False;s['trading_enabled'][mask]=False

    def settle(self,y):
        assert self.assessed[y] and self.due_months[y]==self.month and np.all(self.settled_months[:,y]==-1)
        s=self.s;amount=self.taxes[:,y];credit=amount<0;bill=amount>0;zero=amount==0
        if np.any(credit):
            before=self.before();invest=credit & s['account_open'] & s['trading_enabled'] & (self.month<24)
            s['C'][invest]-=amount[invest];s['bank'][credit & ~invest]-=amount[credit & ~invest]
            self.emit('credit_receipt',before,credit,assessed_tax=amount,due_month=int(self.due_months[y]),settled_month=self.month,model_tax_year=y+1)
            self.purchase(s['C'],'credit_reinvestment',invest)
        if np.any(bill):
            before=self.before();remaining=np.where(bill,amount,0.)
            opened=bill & s['account_open'];closed=bill & ~s['account_open']
            paid=np.where(opened,np.minimum(s['C'],remaining),0.);s['C']-=paid;remaining-=paid
            short=opened & (remaining>0)
            if self.ad and np.any(short):raise AssertionError("Unexpected interim positive AD bill")
            resources=s['n']*self.price*(1-self.p['cost_per_leg'])
            partial=short & (remaining<resources)
            q=np.where(short & (remaining>=resources),s['n'],np.where(short,remaining/(self.price*(1-self.p['cost_per_leg'])),0.))
            self.sale(q,'tax_funding_sale')
            before=self.before()
            paid=np.where(opened,np.minimum(s['C'],remaining),0.);s['C']-=paid;remaining-=paid
            residual=s['C'][partial]-remaining[partial]
            if np.any(np.abs(residual)>1e-8+1e-10*np.maximum(np.abs(amount[partial]),1.)):
                raise ArithmeticError("Funding sale residual")
            s['C'][partial]=0.;remaining[partial]=0.
            paid=np.where(closed,np.minimum(s['bank'],remaining),0.);s['bank']-=paid;remaining-=paid
            failure=bill & (remaining>0);s['F']+=remaining;s['funding_failure']|=failure
            first=failure & (s['funding_failure_month']==-1);s['funding_failure_month'][first]=self.month
            self.close(failure | (opened & (s['n']==0) & (s['C']==0)))
            self.emit('bill_payment',before,bill,assessed_tax=amount,due_month=int(self.due_months[y]),settled_month=self.month,model_tax_year=y+1,household_payment=remaining)
        if np.any(zero):self.emit('zero_settlement',self.before(),zero,assessed_tax=amount,due_month=int(self.due_months[y]),settled_month=self.month,model_tax_year=y+1)
        self.settled_months[:,y]=self.month

    def assess(self,y):
        s=self.s;self.annual_g[:,y]=s['g']
        if self.ad:
            self.taxes[:,y]=annual_ad_tax(s['g'],self.p['credit_capacity_sek'],self.p['tax_mode'])
            if y==0:
                count=int(np.count_nonzero(self.taxes[:,y]>0));self.invariants['unexpected_positive_ad_year1_taxes']+=count
                if count:raise AssertionError("Positive AD Y1 assessment")
        else:
            rate=0. if self.p['tax_mode']=='none' else self.p['isk_tax_rate']
            self.bases[:,y],self.taxes[:,y]=isk_assessment(self.quarters[:,y,:],self.deposits[y],rate,self.p['isk_allowance_sek'])
        self.assessed[y]=True
        self.emit('annual_assessment',self.before(),assessed_tax=self.taxes[:,y],due_month=int(self.due_months[y]),model_tax_year=y+1,annual_net_gain=s['g'])
        s['g'][:]=0.
        if self.due_months[y]==self.month:self.phase='zero_lag_settlement';self.settle(y)

    def checkpoint(self):
        if len(self.trace_indices):self.history[self.month]={k:v[self.trace_indices].copy() for k,v in self.s.items()}

    def run(self):
        s=self.s;W0=self.p['initial_wealth_sek'];all_rows=np.ones(self.N,dtype=bool)
        if not self.ad:self.emit('opening_snapshot',self.before(),snapshot_value=np.zeros(self.N))
        before=self.before();s['C'][:]=W0;self.emit('initial_deposit',before,deposit=W0)
        self.purchase(s['C'],'initial_purchase');self.checkpoint()
        for j in range(1,25):
            self.month=j
            if not self.ad and j in (4,7,10,13,16,19,22):
                self.phase='snapshot';value=np.where(s['account_open'],s['n']*self.prices[:,j-1]+s['C'],0.)
                year=(j-1)//12;quarter=((j-1)%12)//3;self.quarters[:,year,quarter]=value
                self.emit('opening_snapshot',self.before(),snapshot_value=value)
            self.phase='return';before=self.before();s['price_pnl']+=s['n']*(self.prices[:,j]-self.prices[:,j-1]);self.price=self.prices[:,j]
            self.emit('price_return',before)
            self.phase='old_settlement'
            for y in range(2):
                if self.assessed[y] and self.due_months[y]==j and np.any(self.settled_months[:,y]==-1):self.settle(y)
            if j==12 and self.strategy=='AD_HARVEST':
                self.phase='harvest';mask=harvest_trigger(s['n'],s['B'],self.price,self.p['cost_per_leg'],self.p['harvest_loss_threshold'])
                self.sale(np.where(mask,s['n'],0.),'harvest_sale');self.purchase(s['C'],'harvest_repurchase',mask);s['harvested']|=mask
            if j==24:
                self.phase='liquidation';self.pre_liquidation_n=s['n'].copy();self.sale(s['n'],'terminal_sale')
                before=self.before();s['bank']+=s['C'];s['C'][:]=0.;self.close(all_rows);self.emit('account_close',before)
            if j in (12,24):self.phase='assessment';self.assess(j//12-1)
            self.checkpoint()
        pending=np.where(self.settled_months<0,self.taxes,0.).sum(axis=1)
        self.pre_runoff_value=s['bank']-s['F']-pending
        for j in range(25,25+self.p['settlement_lag_months']):
            self.month=j;self.phase='runoff'
            for y in range(2):
                if self.assessed[y] and self.due_months[y]==j and np.any(self.settled_months[:,y]==-1):self.settle(y)
            self.checkpoint()
        self.invariants['unsettled_records']=int(np.count_nonzero(self.settled_months<0))
        if self.invariants['unsettled_records']:raise AssertionError("Unsettled tax after runoff")
        self.check_state();self.W=s['bank']-s['F'];self.net_return=self.W/W0-1.;self.loss=-self.net_return
        self.accounting_residual=self.W-(W0+s['price_pnl']-s['fees_total']-self.taxes.sum(axis=1))
        self.runoff_residual=self.W-self.pre_runoff_value
        scale=np.maximum.reduce([np.abs(self.W),np.full(self.N,W0),np.abs(s['price_pnl']),s['fees_total'],np.abs(self.taxes.sum(axis=1))])
        self.normalized_identity=np.abs(self.accounting_residual)/(1e-6+1e-10*scale)
        self.normalized_runoff=np.abs(self.runoff_residual)/(1e-6+1e-10*np.maximum(np.abs(self.W),np.abs(self.pre_runoff_value)))
        if np.any(self.normalized_identity>1) or np.any(self.normalized_runoff>1):raise AssertionError("Accounting identity/runoff failure")
        return self

    def outcome_arrays(self,scenario_id):
        s=self.s
        return dict(scenario_id=np.array(scenario_id),strategy=np.array(self.strategy),path_id=np.arange(self.N),
            W0=np.full(self.N,self.p['initial_wealth_sek']),W=self.W,net_return=self.net_return,loss=self.loss,F=s['F'],
            funding_failure=s['funding_failure'],funding_failure_month=s['funding_failure_month'],closure_month=s['closure_month'],
            harvested=s['harvested'],fees_total=s['fees_total'],trade_count=s['buy_count']+s['sell_count'],buy_count=s['buy_count'],
            sell_count=s['sell_count'],price_pnl=s['price_pnl'],tax_y1=self.taxes[:,0],tax_y2=self.taxes[:,1],
            isk_base_y1=self.bases[:,0],isk_base_y2=self.bases[:,1],isk_base_applicable=np.full(self.N,not self.ad),
            final_bank=s['bank'],pending_tax_after_runoff=np.zeros(self.N),accounting_residual=self.accounting_residual,
            runoff_residual=self.runoff_residual,tax_assessed_months=self.assessed_months,tax_due_months=self.due_months,
            tax_settled_months=self.settled_months,annual_net_gains=self.annual_g,quarter_values=self.quarters,
            final_shares=s['n'],final_actual_basis=s['B'],final_account_cash=s['C'],
            buy_count_by_month=self.buy_by_month,sell_count_by_month=self.sell_by_month)

def run_vector(prices,p,strategy,trace_indices=()):
    return VectorEngine(prices,p,strategy,trace_indices).run()
