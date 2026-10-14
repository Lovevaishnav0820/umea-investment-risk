# Mathematical model and worked examples

The return process and trading policy are modelling choices. Tax constants follow the Skatteverket guidance listed in [SOURCES.md](SOURCES.md). The calculations below are worked out by hand and provide the reference values used by the tests (`config/benchmark_fixtures.json`); they do not use the simulation code. All money is nominal SEK and rates are decimals.

<a id="ref-moments"></a>
## Price process and moments

For independent Z_ij~N(0,1), let Δ=1/12, a=log(1+m), and

$$
X_{ij}=\log(S_{ij}/S_{i,j-1})=(a-\sigma^2/2)\Delta+\sigma\sqrt\Delta Z_{ij},\quad S_{i0}=100.
$$

The normal exponential moment gives E[exp(sum of 12 X)]=exp(a)=1+m. Thus m is the annual expected **simple price return**, while a is the drift of the log price. Using a=m would turn the input 6% into an expected return of exp(0.06)−1. At month j, t=j/12,

$$
E[S_j]=S_0(1+m)^t,\qquad
\operatorname{Var}(S_j)=S_0^2(1+m)^{2t}(e^{\sigma^2t}-1).
$$

At baseline E[S12]=106 and E[S24]=112.36. Monthly log mean is (log1p(0.06)−0.25²/2)/12; variance is 0.25²/12. These are population moments; a sample will differ from them by simulation error. See [METHODOLOGY.md](METHODOLOGY.md#price-moment-checks) for the six-standard-error checks. The unit example `gbm_expected_terminal` contains these values.

<a id="ref-trades"></a>
## Acquisition cost, deduction and trades

Let n be shares and B their total acquisition cost, including purchase fees. A purchase with cash budget A costs qS(1+c)=A, so q=A/[S(1+c)], B increases by A, and cash decreases by A. The market value of the holding rises by qS and the difference qSc is the fee.

A sale of q shares yields N=qS(1−c) and removes B_s=Bq/n_old from the acquisition cost. The taxable deduction is D=max(B_s,0.2N) when the 20% alternative is available, otherwise B_s, and the realized gain is N−D. The remaining acquisition cost is B−B_s, **not B−D**: the alternative deduction does not change the cost of the shares that remain. A full sale leaves B=n=0. Taking the larger of the two deductions corresponds to choosing the more favorable permitted method.

Worked examples:

- Buy 100 shares at 10 with c=.01: cost 1,010. Buy another 100 at 20: cost 2,020. Total n=200, B=3,030. Sell 50 at 30: net proceeds 1,485, acquisition cost removed 757.5; 20% of proceeds is only 297, so gain=727.5 and remaining n=150, B=2,272.5.
- Start n=100, B=1,000. Sell 10 at 100 without cost: N=1,000, acquisition cost removed=100, alternative=200, gain=800; remaining n=90, B=900 (not 800).
- Spend A=101 at S=10, c=.01: q=10, B=101, buy fee=1. Sell all at 10: cash=99, gain=−2, sell fee=1, n=B=0. Total fee=2.
- A zero-quantity sale changes nothing, even when n=0 (no division by zero occurs).
- Without costs, one share with acquisition cost 100 sold and then repurchased at 80 still leaves one share, but the new acquisition cost is 80 and the realized loss is 20.

The corresponding unit examples are `average_basis_after_two_buys_and_partial_sale`, `alternative_deduction_does_not_rewrite_basis`, `budget_buy_and_full_sale`, `zero_quantity_sale` and `zero_cost_reset`.

<a id="ref-tax"></a>
## Annual tax function and kink

Realized gains are aggregated into g_y before tax is applied. Under the Swedish schedule, let x=g if g≥0 and x=.7g otherwise. The usable reduction for a negative x is

$$
R(x;H)=\min\{H,\ .30\min((-x)^+,100000)+.21((-x-100000)^+)\},
\quad T(g;H)=.30x^+-R(x;H).
$$

A null H means no binding cap. H is the capacity of one individual taxpayer in one tax year, after other tax reductions, not a pool shared across the two years. Same-year netting happens before the cap is applied, and nothing is carried forward. The symmetric counterfactual uses T=.30g, and the no-tax mode used in some tests uses T=0. The supplementary no-threshold counterfactual replaces R by .30(−x)⁺, i.e. a constant 21% of a residual raw loss; for a raw loss of 200,000 it gives −42,000 (unit example `tax_no_deficit_threshold`).

For an isolated raw share loss d>0 before the capacity cap:

$$
R(d)=\begin{cases}.21d,&d\le 100000/.7,\\
30000+.147(d-100000/.7),&d>100000/.7.
\end{cases}
$$

The deductible-deficit threshold is 100,000; the raw-loss threshold is 142,857.142857… SEK. Above it the marginal raw-loss relief is .7×.21=.147. Therefore −100,000 has tax −21,000, −200,000 has tax −38,400, and −500,000 has tax −82,500. At the kink the credit is 30,000. A 20,000 capacity truncates the −200,000 example to −20,000; zero capacity truncates it to zero. Two separate years with that cap each permit 20,000, not 20,000 across both. Same-year +20,000 and −20,000 gives zero; +20,000 and −10,000 gives 3,000. Symmetric −200,000 gives −60,000. These values are the unit examples `tax_*` and `capacity_annual_reset`.

<a id="ref-reinvestment"></a>
## Reinvestment benchmark and its domain

Start with one share costing b, sold and repurchased at p<b at the first year-end with zero costs. Let d=b−p and the usable credit R=λd. Before the credit arrives the investor still has one share with acquisition cost p. At refund price s, investing R buys R/s more shares, so n=1+R/s and B=p+R.

For terminal price z, assume 0≤τ<1, 0≤λ≤1, b>p>0, s>0, z≥b, and the acquisition cost is at least the alternative deduction in each final sale: b≥.2z and p+R≥.2z(1+R/s). The study's .21 and .30 relief rates satisfy the bound on λ. Because p+R=p+λ(b−p)≤b and 1+R/s≥1, z≥b then guarantees nonnegative taxable final gains for both strategies. Also assume no discounting, no interim bill or external funding, recognized realizations, and the loss and the final gain in separate tax years. In this region,

$$
W_D=z-\tau(z-b)=(1-\tau)z+\tau b,
$$
$$
W_H=z(1+R/s)-\tau[z(1+R/s)-(p+R)]
=(1-\tau)z(1+R/s)+\tau(p+R).
$$

Subtract W_D, substitute p=b−d and R=λd:

$$
\Delta W=d\{\lambda[(1-\tau)z/s+\tau]-\tau\}.
$$

For λ>0, break-even is z/s=τ(1−λ)/[λ(1−τ)]. At λ=.21 and τ=.30 the ratio is 79/49=1.612244897959…. It is the **price ratio after the refund is received**, not the recovery since the original purchase. If λ=0 and τ>0, no finite ratio gives break-even in this region: lowering the acquisition cost costs τd. If λ=τ=0, every admissible ratio gives equal wealth, so there is no unique break-even ratio. If τ=λ=.30, break-even is z/s=1. Costs, capacity kinks and the alternative deduction can change the calculation. For a single example with nonlinear relief replace λ by R(d)/d; that does not make λ constant across losses.

The bound λ≤1 and both alternative-deduction inequalities are part of the formula's domain. Within that domain, z≥b guarantees nonnegative terminal gains for both strategies.

### Hand-worked outcomes

| Case (b=100, p=80) | Credit | Refund price | Shares / acquisition cost after credit | Final sale / tax | W after all settlements |
|---|---:|---:|---|---|---:|
| Asymmetric reinvestment, z=100 | 4.2 | 80 | 1.0525 / 84.2 | 105.25 / 6.315 | 98.935 |
| Credit retained as cash, z=100 | 4.2 | No purchase | 1 / 80 | 100 / 6 | 100−6+4.2=98.2 |
| Symmetric reinvestment, z=100 | 6 | 80 | 1.075 / 86 | 107.5 / 6.45 | 101.05 |
| Asymmetric credit at lower price, z=100 | 4.2 | 60 | 1.07 / 84.2 | 107 / 6.84 | 100.16 |
| Continuing decline, z=60 | 4.2 | 70 | 1.06 / 84.2 | 63.6 / −4.326 | 67.926 |

The passive recovery benchmark ends at 100. Passive continuing decline gives 60+.21×40=68.4. In the continuing-decline harvest case, the second loss is 84.2−63.6=20.6, giving a credit .21×20.6=4.326; the gain formula above does not apply. The two annual credits are separate and are not netted across years.

With the refund at month 24 (lag 12), it remains cash and the recovery path ends at 98.2, with no extra purchase or sale. Keeping the credit as cash before month 24 would also give 98.2, but it is not one of the reported strategies. With lag zero, the 4.2 credit can be invested immediately at month 12; the same 98.935 follows at p=s=80. On the *same lower-price path*, lag zero produces 98.935 while lag six buys at 60 and produces 100.16. This shows that delay is not harmful on every path; it is not a statement about the average effect.

For the full-path example `asymmetric_refund_reinvested`, n=1 and B=80 at the ends of months 12 and 17. Only month 18 receives the refund and changes n to 1.0525 and B to 84.2. The price rise then generates price_pnl=−20+1.0525×20=1.05; taxes sum to 2.115, giving 100+1.05−2.115=98.935.

<a id="ref-isk"></a>
## ISK calendar

Let Q_yq be the account value (shares plus cash in the account) at the start of each quarter, with K_y=(ΣQ_yq+deposits_y)/4. T_y=.01065 max(K_y−300000,0). The account is empty at the first January observation, then receives W0 once. With no costs and flat prices, Y1 observations [0,500000,500000,500000] plus deposit 500000 give K1=500000 and T1=2130. Counting the initial assets in January as well as the deposit would double-count them.

Lag 6 pays T1 at month 18, after the month's return but before the month-19 opening snapshot. Thus Y2 observations are [500000,500000,497870,497870], K2=498935, T2=2118.65775 and W=500000−2130−2118.65775=495751.34225. Lag zero pays at month 12 before all Y2 observations: K2=497870, T2=2107.3155 and W=495762.6845. The 11.34225 difference comes from the lower tax base in year 2, not from investment growth.

At flat W0=100000, K1=K2=100000 and the tax is zero. Initial investments of 100,000 SEK are not exempt on every path: sufficiently high later values can exceed the allowance. An account with 10 shares priced 100 and cash 250 is valued at 1250. Fees and withdrawals affect future observed values but are not standalone deductions from the base.

<a id="ref-funding"></a>
## External funding and utility functions

In the full-path example `isk_positive_prices_negative_net_outcome`, W0=500000, S0=100, c=0. The price stays at 100 through month 9 and is 0.2 from month 10. The quarter-opening value for month 10 uses the **previous** price, so K1=500000 and T1=2130. The account is then worth only 1000. At month 18 all 5000 shares are sold for 1000 and the investor pays the remaining 1130 from outside the account. Investment stops; F=1130, bank=0. Y2 observations [1000,1000,0,0] give K2=500 and T2=0. Final W=−1130 despite strictly positive prices. Price_pnl=−499000; identity: 500000−499000−2130=−1130. This deterministic path says nothing about probability; under Gaussian increments, open sets of paths with a funding shortfall have positive probability.

Funding unit examples: a bill 100 with C=20 and four shares at 10 uses 20+40 and requires F=40. A closed account with bank=20 and bill 100 requires F=80. A bill 40 with four shares at 10 exactly uses up the account but requires F=0, so the account closes without an external-funding event. A later bill based on earlier account values is still assessed after closure, and no liability is forgiven.

**Constant relative risk aversion (CRRA) requires strictly positive wealth and suitable moments.** U(W)=W^(1−γ)/(1−γ), or log W at γ=1, is not a utility on negative investment outcomes. Even for an integer exponent, evaluating the power at W<0 is not a meaningful extension of CRRA. Positive values in one finite sample do not show that the model's outcomes are always positive, and finite E[W^(1−γ)] or E[|log W|] would also need to be shown.

A tax on realized gains alone does not create this problem: with nonnegative acquisition cost and τ<1, the tax on a position sold now cannot exceed τ times its positive proceeds. In a simple one-period comparison (our own illustration, of the kind of wealth-tax versus gains-tax comparison studied by Farago, Hjalmarsson and Kiss [P1]), terminal wealth under a proportional wealth tax q<1 over T years is (1−q)^T W0 R, and under a gains tax with loss relief λ it is W0[R−τ(R−1)^+ + λ(1−R)^+] ≥ (1−τ)W0R, for a lognormal gross return R. Both are positive and have finite positive and negative moments, so CRRA expected utility is finite. The ISK tax in this study is based on earlier account values and can exceed what remains in the account, so that argument does not carry over.

W is a net investment outcome, not consumption or total wealth. Adding arbitrary outside wealth, truncating W at a small positive value, dropping paths with external funding or stopping at zero would change the experiment, so none of these is done.

Constant absolute risk aversion (CARA), U(W)=−exp(−aW), is defined for all real W, but that alone does not make it usable here: the ISK tax is proportional to an earlier, lognormally distributed account value, and the probability of a large earlier value followed by a severe fall declines only like the exponential of a squared log-price, which need not control the exponential of a price-sized tax bill. E[exp(−aW)] can therefore be infinite. The study does not claim that E[exp(−aW)] is finite and does not estimate a CARA certainty equivalent.

### Why mean and ES are well-defined

In ISK, the number of shares never increases after the initial purchase; tax payments reduce it. Each of the finitely many quarterly account values is bounded by the initial share count times a lognormal price with finite moments (cash in the account is zero between operations). Taxes and external funding are bounded by finite sums of these values and constants.

In depå hold (`AD_HOLD`), the final sale proceeds are proportional to S24. In depå harvest (`AD_HARVEST`), the single sale and repurchase reduce the share count by the trading costs. The year-1 credit is at most .30W0 under every tax schedule used. The value it adds at the end is bounded by a constant times S24/S_receipt, which has finite moments, and the acquisition cost it adds is bounded by the same credit. Final credits and taxes are piecewise-linear functions of these quantities, and no credit is reinvested more than once. Hence E|W|, E|r| and E|L| are finite, so the means and ES at a fixed level exist. This establishes first moments only; it does not justify any utility ranking.

<a id="ref-es"></a>
## Expected shortfall and paired bootstrap

For integrable loss L and α=.95, ES is min over η of η+E[(L−η)^+]/(1−α). For N equally weighted sample losses sorted descending, u=(1−α)N, k=floor(u), f=u−k:

$$
\widehat{ES}_\alpha=\frac{\sum_{i=1}^k L_{[i]}+fL_{[k+1]}}{u}.
$$

A value of u within 1e−10 of an integer is rounded to that integer. The estimator uses exactly the requested probability mass and agrees with the discrete variational definition; ties at the cutoff are split as needed. For N=20000, exactly the worst 1000 observations enter. Gains are negative losses and are kept as negative values.

Unit examples: 96 zeros and four ones at α=.95 include four ones and one zero, so ES=.8. For [0,1,2,3] at α=.625, u=1.5, so ES=(3+.5×2)/1.5=8/3. For [−.4,−.3,−.2,−.1] at α=.5, ES=(−.1−.2)/2=−.15. Evaluating the variational expression at each distinct sample loss gives an independent check of the minimum.

For paired losses A=[0,2], B=[2,0] at α=.5, both ES values are 2, so their difference is 0. But paired difference losses are [−2,2], whose ES is 2. The two quantities answer different questions: the tail of each strategy, and the tail of one strategy's outperformance of the other.

For returns A=[.1,.2], B=[.05,.25], fixed paired bootstrap rows [0,0], [1,1], [0,1] give mean contrasts .05, −.05, 0 and ES95 contrasts −.05, .05, −.05. Linear 2.5/97.5 percentiles of the three mean contrasts are [−.0475,.0475]. This small example checks the pairing and the percentile interpolation; the study uses 2,000 draws of 20,000 paths.

<a id="ref-threshold"></a>
## Strict harvest threshold

Harvest if and only if n>0 and nS(1−c)<(1−h)B. At n=1, B=100, c=0, h=.05, price 95 is equality and does not trigger; price 94.999999 does. At flat price 100 with initial budget 100 and c=.001, n=1/1.001 and sale proceeds=100×.999/1.001=99.8001998002…; h=0 therefore triggers. Costs can create a deductible loss even without a price decrease.

<a id="ref-invariance"></a>
## Zero-tax and rising-price examples

With no taxes and no costs, a full sell/rebuy leaves the same shares and no credit; all three strategies end at W0S24/S0 on every path. The recovery path ends at 100 from budget 100 for every strategy. With positive costs that equality is false: at flat price 100, budget 101 and c=.01, holding buys one share then sells for 99. Harvesting once with h=0 sells for 99, rebuys 99/101 shares and finally sells for 9801/101=97.0396039604…. Fees equal the lost wealth, 400/101=3.9603960396…, whereas holding fees are 2.

On prices S_j=100+j, initial budget 100 and zero costs, there is no first-year loss. AD_HARVEST and AD_HOLD both sell at 124, assess gains tax 7.2 and end at 116.8. These deterministic cases would reveal spurious trades or a missing final tax without reusing the simulation code.

<a id="ref-identity"></a>
## Accounting identity and settlement after month 24

Start with W0 invested and no bank cash. Each price movement changes the market value of the holding by n_before×ΔS. Each trade moves money between shares and cash but destroys exactly its fee. Each paid positive tax removes resources; each credit adds them. External funding F pays an otherwise uncovered bill but never becomes investable cash. Before subtracting the external funding, final bank equals W0+price_pnl−fees_total−ΣT+F. Thus

$$
\boxed{W=\text{bank}-F=W_0+\text{price P\&L}-\text{fees}-\sum_y T_y.}
$$

At month 24 after final assessment and any immediate settlement, let U be the sum of still-pending signed taxes. With no interest after month 24, W=bank24−F24−U. Settling the remaining taxes after month 24 gives the same answer. A negative pending tax is a receivable, so subtracting it adds it, and a bill already paid is not subtracted again. These identities would reveal free funding, omitted fees, missing liabilities or duplicated credits.

<a id="ref-validation"></a>
## Tolerances and numerical checks

The property checks in `config/benchmark_fixtures.json` state acceptance bounds, not realized values. For a monetary equality the normalized error is abs(a−b)/(atol+rtol×scale), with atol=1e−8 SEK for the worked examples or 1e−6 SEK for simulated paths and rtol=1e−10. For the accounting identity the scale is max(abs(W),abs(W0),abs(price_pnl),abs(fees),abs(sum tax)); for a comparison of two numbers it is max(abs(a),abs(b)). A comparison passes when the normalized error is at most 1. Shares and dimensionless comparisons use atol=1e−12. Discrete quantities match exactly.

Scalar/vector agreement covers all full-path examples and the first 32 shared price paths in all 19 configurations, retaining negative W. The state checks find no nonfinite values, no negative asset balances, no missing settlements, no trade after month 24 and no positive depå tax in year 1. The check `no_tax_general_equality` runs the first 32 baseline paths without tax or costs, where all strategies must end equal. The calendar and funding examples are also compared month by month, because the accounting identity alone cannot show that timing is correct.

For the primary and the independent-seed baseline runs, the absolute difference in means is compared with six times the square root of the sum of the two estimated variances of the mean, for each strategy and each of the three paired contrasts; if both standard errors are zero, the means must be equal. Differences in ES between the two runs are reported against the bootstrap standard deviation for information only. Seeds are fixed in advance and are not changed after a failed check.
