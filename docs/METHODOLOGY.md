# Methodology

Love Vaishnav · 14 October 2026

The study asks whether one year-end loss realization, with usable tax relief invested when it is received, changes the expected two-year net return or the ES95 loss of an investment in a Swedish depå. ISK holding is included for comparison. The primary contrast is depå harvest minus depå hold (`AD_HARVEST` − `AD_HOLD`); two further contrasts compare each depå strategy with ISK holding (`ISK_HOLD`). The strategies are fixed rules, not optimized trading policies.

## Design and price process

All three strategies start with the same budget. The baseline uses 500,000 SEK, initial price 100 SEK, expected annual simple price return 6%, diffusion volatility 25% and a cost of 0.1% on each purchase or sale. Depå harvest checks once, at month 12, and sells and repurchases the whole position if net sale proceeds are strictly below 95% of its acquisition cost. Depå hold and ISK hold keep their shares except for sales needed to pay tax and the final sale. Credits received before month 24 are invested immediately; later credits remain cash. All positions are sold at month 24 and all outstanding taxes are settled afterward.

For path $i$, month $j$, independent $Z_{ij}\sim N(0,1)$ and $\Delta=1/12$,

$$
\log(S_{ij}/S_{i,j-1})=[\log(1+m)-\sigma^2/2]\Delta+\sigma\sqrt{\Delta}\,Z_{ij}.
$$

Here $m$ is the expected annual simple price return, not the drift of the log price. Thus $E[S_j]=S_0(1+m)^{j/12}$ and

$$
\operatorname{Var}(S_j)=S_0^2(1+m)^{2j/12}\,[\exp(\sigma^2j/12)-1].
$$

The baseline expectations are $E[S_{12}]=106$ and $E[S_{24}]=112.36$. There are 20,000 independent 24-month paths. Strategies share prices within a configuration, and all configurations share the same matrix of standard-normal innovations, transformed with their own parameters (common random numbers). The nine return models combine $m\in\{3\%,6\%,9\%\}$ and $\sigma\in\{15\%,25\%,35\%\}$. Together with the tax-schedule and settlement-lag variants and one-at-a-time changes to costs, harvest threshold, initial investment, tax-reduction capacity and settlement lag, there are 19 distinct configurations. A symmetric 30% tax and credit is included as a counterfactual for comparison.

## Trade, tax and calendar rules

Let $n$ be the number of shares, $B$ their acquisition cost, $S$ the current price and $c$ the cost per purchase or sale. Buying with budget $A$ acquires $A/[S(1+c)]$ shares and adds $A$ to $B$. Selling $q$ shares yields net proceeds $N=qS(1-c)$ and removes acquisition cost $B_s=Bq/n$ (average-cost method). For listed shares the deduction is $D=\max(B_s,0.2N)$ and the taxable gain is $N-D$. The remaining acquisition cost is $B-B_s$ even when the 20% alternative is used. A full sale sets shares and acquisition cost to zero. The harvest condition is $n>0$ and $nS(1-c)<(1-h)B$, with baseline $h=0.05$. In a harvest, the sale is assumed to settle before the repurchase, so the repurchased shares receive a new acquisition cost equal to the reinvested proceeds. Other orderings are not modelled.

Realized gains and losses are netted within each tax year. For the annual net gain $g$, let $x=g$ if $g\geq0$ and $x=0.7g$ otherwise. With $a^+=\max(a,0)$ and annual usable reduction capacity $H$,

$$
T(g;H)=0.30\,x^+-\min\{H,\ 0.30\min((-x)^+,100000)+0.21(-x-100000)^+\}.
$$

The 100,000 SEK deficit threshold and the capacity $H$ apply to one individual taxpayer and one tax year; the tax reduction can only offset that individual's income tax and property charges, and unused reductions are not carried forward. The model follows a single investor; it does not pool taxes within a household. An unlimited capacity is written as JSON `null`. For an isolated raw loss $d$, uncapped relief is $0.21d$ up to $d=100000/0.7$ and $30000+0.147(d-100000/0.7)$ above it. The symmetric counterfactual sets $T=0.30g$.

For ISK, with $Q_{yq}$ the account value (shares plus cash in the account) at the start of quarter $q$ and $D_y$ the deposits in year $y$,

$$
K_y=\Big(\sum_{q=1}^4Q_{yq}+D_y\Big)/4,\qquad T_y=0.01065\max(K_y-300000,0).
$$

The first January value is zero; the initial budget is deposited immediately afterwards and counted once as a deposit. The 300,000 SEK allowance is assumed not to be used by other ISK, capital-insurance or PEPP savings. Realized gains and losses are not taxed separately in ISK. The ISK tax is paid by selling shares in the account.

Within a month, the model records any quarter-opening value, applies the price return, settles taxes that fall due, performs any month-12 harvest or month-24 sale, and then assesses year-end tax. Assessments occur at months 12 and 24. Taxes settle after a lag of 0, 6 (baseline) or 12 months; with a zero lag a tax settles in its own assessment month. The same lag is used for bills and refunds. This is a modelling convention: in practice refunds are paid with the final tax decision, while tax owed is due some months after it, and both depend on when the decision is issued. Credits arriving at month 24 or later remain cash. After month 24 the model only settles taxes, without further returns, interest or assessments.

A positive bill is paid from cash in the account and then by selling the minimum number of shares needed. If the account cannot cover the bill, the investor pays the remainder from outside the account. This external funding $F$ is recorded separately; it is never invested and trading stops. After all settlements, the net investment outcome is

$$
W=\text{bank}-F=W_0+\text{price P\&L}-\text{fees}-\sum_yT_y,
$$

where bank is the cash held after the account is closed. Signed tax is positive for a bill and negative for a credit. The identity is checked on every primary path; it ensures that no paid tax is counted twice and that external funding never becomes investable cash.

## Analytical benchmark and its domain

Start with one share of acquisition cost $b$ and realize a loss at $p<b$ without costs. Let $d=b-p$, usable credit $R=\lambda d$, price at refund $s$, terminal price $z$ and gains-tax rate $\tau$. Reinvestment buys $R/s$ additional shares, giving $n=1+R/s$ and acquisition cost $p+R$.

Assume $0\leq\tau<1$, $0\leq\lambda\leq1$, $b>p>0$, $s>0$, $z\geq b$, and that the actual acquisition cost exceeds the 20% alternative deduction in both final sales:

$$
b\geq0.2z,\qquad p+R\geq0.2z(1+R/s).
$$

Both final gains are then nonnegative and the acquisition cost is the deduction used. With the loss and the final gain in separate tax years, no interim bill or external funding, and no discounting,

$$
\Delta W=d\{\lambda[(1-\tau)z/s+\tau]-\tau\}.
$$

For $\lambda>0$, harvesting breaks even when

$$
z/s=\frac{\tau(1-\lambda)}{\lambda(1-\tau)}.
$$

At $\lambda=0.21$ and $\tau=0.30$ the ratio is $79/49=1.612244897959\ldots$, measured from the date the relief is received. Symmetric relief, $\lambda=\tau=0.30$, gives a break-even ratio of one. Zero relief with a positive gains tax gives $\Delta W=-\tau d<0$; when both are zero every admissible ratio gives the same wealth. Final losses, costs, a binding alternative deduction or the capacity limit require the full annual tax calculation. The helper `break_even_ratio` raises an error when no unique ratio exists; see [IMPLEMENTATION.md](IMPLEMENTATION.md).

For $b=100$, $p=s=80$ and $z=100$, 21% relief gives $W_H=98.935$ against $W_D=100$. If the same relief arrives when the price is 60, $W_H=100.16$. A later refund is therefore not always worse along a given path: it changes the price at which the refund buys shares.

## Outcomes and uncertainty

Define the two-year net return $r=W/W_0-1$ and loss $L=-r$. Negative $W$ and losses above one are retained. Outcomes are not annualized. For an integrable loss,

$$
\mathrm{ES}_{0.95}(L)=\min_\eta\left\{\eta+\frac{E[(L-\eta)^+]}{0.05}\right\}.
$$

The empirical estimator includes exactly the worst 5% of the sample. With losses in descending order $L_{[i]}$, $u=0.05N$, $k=\lfloor u\rfloor$ and $f=u-k$,

$$
\widehat{\mathrm{ES}}_{0.95}=\frac{\sum_{i=1}^kL_{[i]}+fL_{[k+1]}}{u},
$$

with the last term omitted when $f=0$. At $N=20000$, the tail contains exactly 1,000 observations. Ties are kept.

Paired mean contrasts average $r_a-r_b$ over paths. ES contrasts subtract the two strategies' ES values; they are not the ES of the paired differences. In monetary terms, the baseline mean difference corresponds to the average change in final outcome, while the ES difference compares two tail averages that need not contain the same paths. A separate PCG64 generator produces 2,000 bootstrap draws of complete path indices, reused for every strategy and configuration. Each draw recomputes both strategies' means and ES values. NumPy linear 2.5% and 97.5% percentiles give approximate pointwise 95% Monte Carlo intervals. As a check, the standard error of each mean difference is also computed as $\operatorname{sd}(r_a-r_b)/\sqrt N$ with `ddof=1`. Negative ES95 differences (A minus B) mean lower tail loss for A. A separate 20,000-path baseline run with another seed checks the means against six combined standard errors; its ES differences are reported for information.

## Supplementary analysis: starting wealth and the deficit threshold

The supplementary analysis is separate from the 19 configurations. It reuses the primary innovations and bootstrap indices and keeps every baseline input except the one stated:

- Swedish rules with initial investment 100,000, 200,000, 300,000, 400,000, 500,000, 750,000, 1,000,000 and 2,000,000 SEK (the 500,000 SEK case repeats the baseline and must reproduce it exactly);
- a counterfactual tax schedule at 500,000 SEK that removes the 100,000 SEK deficit threshold, so residual raw losses always receive 21% relief.

The reduction for a deficit $D$ in one year can be written $R(D)=0.21D+0.09\min(D,100000)$. Spreading a deficit over two tax years therefore adds at most $0.09\times100000=9000$ SEK compared with realizing the same total in one year. Without the threshold the tax function is proportional, and with proportional costs and unlimited capacity every depå quantity scales with $W_0$; the depå returns then do not depend on $W_0$ (checked in `tests/test_supplementary.py`).

The results are in [Table S1](../outputs/supplementary/table_s1_wealth_threshold.md). Under Swedish rules, the harvest-minus-hold ES95 interval lies above zero at 100,000–300,000 and 2,000,000 SEK, includes zero at 400,000 SEK and lies below zero at 500,000–1,000,000 SEK. At 100,000 SEK the threshold cannot be reached, because a deficit is at most 70% of the investment; at 200,000 SEK only a few extreme paths exceed it (Table S1 counts the paths whose annual deficit exceeds 100,000 SEK). Both cases give the same ES95 difference as the no-threshold counterfactual at 500,000 SEK, +0.634 pp. The mean difference is negative in every experiment. These results show that the favorable baseline ES95 difference depends on the deficit threshold together with the starting amount. The settlement lag also changes the tail result (Figure 1 and Table 2), consistent with the amount of reinvested credit exposed to year-2 price risk. The experiments do not isolate every channel.

## Price-moment checks

For each of the nine return models, the terminal-price mean is compared with $M=S_0(1+m)^2$, using the theoretical standard error $M\sqrt{(\exp(2\sigma^2)-1)/N}$. For the $J=24N$ log increments, the expected mean is $\mu_x=[\log(1+m)-\sigma^2/2]/12$ and the variance is $v_x=\sigma^2/12$, with standard errors $\sqrt{v_x/J}$ and $v_x\sqrt{2/(J-1)}$ (sample variance with `ddof=1`). Each discrepancy must be at most six standard errors. These checks detect implementation errors; they do not show that the return model describes observed equity prices.

## Assumptions and interpretation

The return models are illustrative and uncalibrated. They describe one non-dividend asset with fractional shares, proportional costs, no interest on cash or external funding, and no contributions after the initial budget. Both model years use the 2026 rules. The depå tax reduction assumes the stated per-person capacity; the ISK allowance assumes no other ISK, capital-insurance or PEPP savings. An immediate sale and repurchase is assumed to be two distinct transactions recognized at one reference price; Skatteverket's public guidance on netting and acquisition cost does not settle whether every such transaction is recognized, and HFD case law was not examined ([SOURCES.md](SOURCES.md)).

Because every position is sold at month 24, the study does not capture the depå's ability to defer gains tax beyond the horizon; this limits what it can say about the account comparison.

The 2,000 bootstrap draws reduce resampling noise in the interval endpoints, but the endpoints remain estimates. The intervals measure simulation error under each model, not parameter, return-model or tax-law uncertainty, and they are not simultaneous across outcomes and configurations. A comparison whose interval includes zero is not resolved by the simulation. Harvesting is not an optimal policy, and the findings do not establish an empirical return advantage, stochastic dominance or a universally better account.

$W$ is an investment outcome after any external funding, not total household wealth. In a deterministic ISK example with strictly positive prices, $W=-1130$ SEK and $F=1130$ SEK because the ISK tax for a year is based on earlier, higher account values. No simulated path required external funding; zero events in $N$ paths give an approximate one-sided 95% upper bound of $3/N=0.015\%$, not a proof that negative outcomes are impossible. Constant-relative-risk-aversion (CRRA) utility is therefore not defined on this outcome, and constant-absolute-risk-aversion (CARA) utility would need a separate integrability argument. Mean return and ES at a fixed level are well defined because each outcome is a finite piecewise-linear function of lognormal prices and price ratios with finite first moments ([MATHEMATICAL_MODEL.md](MATHEMATICAL_MODEL.md#why-mean-and-es-are-well-defined)). No utility ranking is calculated.

[MATHEMATICAL_MODEL.md](MATHEMATICAL_MODEL.md) contains derivations and the hand-worked reference values. [SOURCES.md](SOURCES.md) gives the official and academic references.
