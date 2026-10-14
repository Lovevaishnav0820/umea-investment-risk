# Stochastic simulation of Swedish investment accounts

**Love Vaishnav · 14 October 2026**

Does realizing a loss once and reinvesting the resulting tax relief improve the return or reduce the tail loss of a Swedish investment? This independent study compares three fixed strategies over two years under Sweden's 2026 tax rules:

- **ISK hold**: holding in an investment savings account (*investeringssparkonto*), taxed on a notional return.
- **Depå hold**: holding in an ordinary taxable custody account (*aktiedepå*, labelled `AD` in the code), taxed on realized gains.
- **Depå harvest**: as depå hold, except that the whole position is sold and immediately repurchased at month 12 if net sale proceeds are more than 5% below acquisition cost.

The study simulates 20,000 price paths in 19 parameter configurations. Within a configuration all strategies use the same paths. Every position is sold at month 24 and all taxes are settled before the outcome is measured. The question comes from the project *Analyzing risk and return of Swedish investment vehicles* in Umeå University's internship project list; the study was not supervised by, or carried out in affiliation with, Umeå University.

## Main results

| Baseline strategy | Mean two-year net return | ES95 loss |
|---|---:|---:|
| ISK hold | 11.010% | 49.165% |
| Depå hold | 7.438% | 39.855% |
| Depå harvest | 7.244% | 39.691% |

ES95 (expected shortfall at 95%) is the average loss over the worst 5% of outcomes; lower is better.

- **Harvesting lowers the mean return in every configuration with Swedish tax rules (17 of 17).** In the baseline, harvest minus hold is −0.194 percentage points (pp), 95% Monte Carlo interval [−0.201, −0.186]: about **−968 SEK** in mean final outcome on an initial investment of 500,000 SEK. Harvesting does better than holding on **8.33%** of baseline paths.
- **In the baseline, harvesting also lowers ES95**, by 0.164 pp [−0.202, −0.131], about **−820 SEK** in monetary ES95. This is a difference between two tail averages, not the mean of paired differences, so it is not comparable path by path with the mean result.
- **The ES95 effect depends on the setting.** It changes with starting wealth, settlement timing, tax-reduction capacity and return parameters. Across all 19 configurations the ES95 interval lies above zero (harvesting worse) in 10, below zero (harvesting better) in 8 and includes zero in 1.
- **ISK versus depå.** ISK holding has the highest mean return and the highest ES95. The depå's lower tail loss assumes that each year's tax reduction can be used in full (adequate tax-reduction capacity); with zero capacity the harvest-minus-ISK ES95 difference shrinks from −9.474 to −0.179 pp. Because positions are sold at month 24, the study does not capture the depå's ability to defer gains tax.

All intervals are approximate pointwise 95% Monte Carlo intervals from 2,000 paired bootstrap draws. They measure simulation error conditional on each model, not uncertainty about future returns, tax law or parameters, and they are not simultaneous across comparisons. One percentage point is 100 basis points; for ES95 differences (A minus B), negative values mean lower tail loss for A.

### Why the tail result changes

The Swedish tax reduction on a capital deficit is 30% up to 100,000 SEK per individual and tax year, and 21% above that. Realizing part of a loss in year 1 and the rest in year 2 gives each part its own threshold, which can add at most 9,000 SEK of relief. A supplementary analysis with the same random numbers varies the starting amount from 100,000 to 2,000,000 SEK and adds a counterfactual without the threshold (constant 21% relief on residual losses). Among the eight starting amounts, harvesting lowers ES95 only at 500,000, 750,000 and 1,000,000 SEK; without the threshold it raises ES95 by 0.634 pp at 500,000 SEK. The settlement lag also matters: in the tested cases, the later the refund is invested in shares (or if it stays in cash), the lower the tail loss of harvesting. See [Table S1](outputs/supplementary/table_s1_wealth_threshold.md) and page 4 of the research note.

![Harvest minus hold under two tax schedules and two settlement lags](outputs/figures/figure1_tax_and_lag.png)

## Read the study

- [Research note (five pages)](outputs/note/research_note.pdf), [appendix (one page)](outputs/note/research_appendix.pdf) and the [Markdown version](outputs/note/research_note.md).
- Tables: [baseline](outputs/tables/table1_baseline.md), [sensitivity](outputs/tables/table2_sensitivity.md), [supplementary Table S1](outputs/supplementary/table_s1_wealth_threshold.md), and the complete results for [all strategies](outputs/tables/scenario_metrics.csv) and [all contrasts](outputs/tables/contrasts.csv).
- Documentation: [methodology](docs/METHODOLOGY.md), [mathematical model and worked examples](docs/MATHEMATICAL_MODEL.md), [implementation and reproduction](docs/IMPLEMENTATION.md), [output files](docs/OUTPUT_SCHEMA.md) and [sources](docs/SOURCES.md).

## Reproduce the results

The reference results in `outputs/` were produced with Python 3.13.5 and the versions pinned in `requirements-lock.txt`.

```bash
python3.13 -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python reproduce.py
```

`reproduce.py` runs the tests, simulates the 19 configurations and the supplementary analysis, rebuilds the tables, figures and PDFs in `reproduction/`, checks the generated files, and compares the results with `outputs/`. It does not modify `outputs/`: it verifies the reference files against their SHA-256 manifest before and after the run. A full run takes a few minutes and needs no network access once the dependencies are installed.

To compare an existing reproduction again:

```bash
python compare_results.py --reference outputs --candidate reproduction
```

Rows are matched by scenario and strategy or contrast. Identifiers and counts must agree exactly; floating-point values must agree within a relative tolerance of 1e-9 (absolute 1e-12 for fractions, 1e-6 SEK for amounts). Results from different platforms differ only in the last digits, so raw array hashes are not expected to match across machines. [IMPLEMENTATION.md](docs/IMPLEMENTATION.md#reproduction-and-comparison) explains the tolerances. Tests alone run with `python -m pytest`.

The test suite has 152 tests. It checks the tax arithmetic, trades, calendar, accounting identity, scalar/vector agreement, bootstrap pairing, the supplementary experiments and the comparison command. In the reference run all 1,140,000 primary strategy-path outcomes satisfy the accounting identity; the largest residual, recorded with its environment in [run_metadata.json](outputs/metadata/run_metadata.json), was below 1e-9 SEK.

```text
config/                 Study configuration and hand-worked reference values
src/umea_risk/          Simulation, statistics, comparison and report generation
tests/                  Unit, accounting, statistical and comparison tests
docs/                   Methods, derivations, implementation, outputs and sources
outputs/                Reference results: note, figures, tables, validation, metadata
reproduce.py            Full reproduction into reproduction/ (ignored by Git)
compare_results.py      Compare a reproduction with outputs/
```

## Scope

Returns are illustrative and uncalibrated: one non-dividend asset, fractional shares, proportional trading costs, zero interest and fixed trading rules. Both model years use the 2026 tax rules. The ISK calculation assumes the 300,000 SEK allowance is not used by other savings. The depå calculation assumes an individual taxpayer with enough income tax each year to use the tax reduction, except in the zero-capacity sensitivity case. The sale in a harvest is assumed to settle before the repurchase, and both are assumed to be recognized for tax purposes at the modelled price; their treatment under Swedish Supreme Administrative Court (HFD) case law was not examined. The 0-, 6- and 12-month settlement lags are modelling conventions applied equally to bills and refunds.

The project list is available from Umeå University ([PDF](https://www.umu.se/globalassets/organisation/fakulteter/teknat/institutionen-for-matematik-och-matematisk-statistik/dokument/internshipprojects-autumn2026.pdf), PDF page 13, printed page 10). [SOURCES.md](docs/SOURCES.md) lists the tax guidance and research literature.
