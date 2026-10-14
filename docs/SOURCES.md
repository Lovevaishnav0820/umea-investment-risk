# Sources

The labels match the references in the research note. The tax model uses the rules for income year 2026 in both model years. The Skatteverket pages below were consulted on 14 October 2026. Keeping the 2026 rules in both years and the choice of settlement lags are modelling assumptions.

## Swedish tax guidance

| Label | Source | Used for |
|---|---|---|
| S1 | Skatteverket, [Kan jag kvitta vinst mot förlust när jag har sålt värdepapper?](https://www.skatteverket.se/privat/etjansterochblanketter/svarpavanligafragor/vardepapper/privatvardepapperfaq/kanjagkvittavinstmotforlustnarjagharsaltvardepapper.5.2b543913a42158acf800015357.html) and [Kvittning och kvotering](https://www.skatteverket.se/privat/skatter/vardepapper/kvittningochkvotering.4.7be5268414bea0646945a21.html) | Netting of gains and losses within the year; 70% of a remaining loss is deductible; 30% tax on positive capital income |
| S2 | Skatteverket, [Skattereduktioner](https://www.skatteverket.se/privat/skatter/arbeteochinkomst/skattereduktioner.4.3810a01c150939e893f1a17e.html) | Reduction for a capital deficit: 30% up to 100,000 SEK and 21% above; total reductions limited to the individual's income tax and property charges; no carry-forward of unused reductions |
| S3 | Skatteverket, [Räkna ut omkostnadsbelopp](https://www.skatteverket.se/privat/skatter/vardepapper/omkostnadsbelopp.4.12815e4f14a62bc048fa7bc.html) | Average-cost method including brokerage fees; alternative deduction of 20% of the sale price after fees for listed shares |
| S4 | Skatteverket, [Skatt på investeringssparkonto](https://www.skatteverket.se/privat/skatter/vardepapper/investeringssparkontoisk.4.5fc8c94513259a4ba1d800037851.html) | For income year 2026: notional-income rate 3.55% (government bond rate of 2.55% on 30 November 2025 plus one percentage point), effective tax 1.065%, tax-free amount 300,000 SEK shared with capital insurance and PEPP savings, and the capital base from quarterly values and deposits |
| S5 | Skatteverket, [Betala kvarskatt](https://www.skatteverket.se/privat/deklaration/betalakvarskatt.4.12815e4f14a62bc048f106ca.html) | Payment dates depend on when the final tax decision is issued; refunds are paid with the decision. The 0-, 6- and 12-month lags in the study are modelling conventions |

The 21% relief on an isolated residual share loss is the product of the 70% deductible fraction and the 30% reduction rate. Above the 100,000 SEK deficit threshold the marginal relief on a raw loss is 14.7%. Limited tax-reduction capacity can lower either amount. A constant 21% credit is therefore not the full Swedish schedule; it is used only as the labelled counterfactual in the supplementary analysis.

**Immediate sale and repurchase.** The study assumes that the sale and the repurchase are two distinct transactions, recognized for tax purposes at the same reference price, with the sale settled first. The public guidance above describes netting and acquisition cost but does not establish that every such transaction is recognized, nor what prices can be executed. Case law of the Supreme Administrative Court (Högsta förvaltningsdomstolen, HFD) on such transactions was not examined, so this remains an open legal question for the study.

## Research literature

All bibliographic details below were checked against Crossref or RePEc on 14 October 2026.

- **[P1]** Farago, A., Hjalmarsson, E. and Kiss, T. (2025). Understanding Wealth-Tax Rates: An Investor-Utility Mapping to Capital-Gains Taxes. *European Financial Management*, 31(4), 1413–1420. [doi:10.1111/eufm.12541](https://doi.org/10.1111/eufm.12541). Background on comparing a wealth-type tax with a capital-gains tax. The illustration in [MATHEMATICAL_MODEL.md](MATHEMATICAL_MODEL.md#ref-funding) is our own and is not taken from the article.
- **[P2]** Dammon, R. M., Spatt, C. S. and Zhang, H. H. (2001). Optimal Consumption and Investment with Capital Gains Taxes. *The Review of Financial Studies*, 14(3), 583–616. [doi:10.1093/rfs/14.3.583](https://doi.org/10.1093/rfs/14.3.583). Background on acquisition cost and the timing of realized gains.
- **[P3]** Chaudhuri, S. E., Burnham, T. C. and Lo, A. W. (2020). An Empirical Evaluation of Tax-Loss-Harvesting Alpha. *Financial Analysts Journal*, 76(3), 99–108. [doi:10.1080/0015198X.2020.1760064](https://doi.org/10.1080/0015198X.2020.1760064). Background on tax-loss harvesting. Only the [CFA Institute summary](https://rpc.cfainstitute.org/research/financial-analysts-journal/2020/empirical-evaluation-tax-loss-harvesting-alpha) of this article was consulted; its empirical estimates are not used.
- **[P4]** Rockafellar, R. T. and Uryasev, S. (2002). Conditional Value-at-Risk for General Loss Distributions. *Journal of Banking & Finance*, 26(7), 1443–1471. [doi:10.1016/S0378-4266(02)00271-6](https://doi.org/10.1016/S0378-4266(02)00271-6) ([author manuscript](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf)). Definition of expected shortfall, including distributions with atoms.

## Project context

- **[U1]** Umeå University, Department of Mathematics and Mathematical Statistics. *Internship Programme: project list for the calendar year 2027* ([PDF](https://www.umu.se/globalassets/organisation/fakulteter/teknat/institutionen-for-matematik-och-matematisk-statistik/dokument/internshipprojects-autumn2026.pdf)). The project *Analyzing risk and return of Swedish investment vehicles* is on PDF page 13 (printed page 10). This study addresses one part of that question independently.

Publications are linked rather than copied into the repository. All inputs needed to reproduce the study are in the repository.
