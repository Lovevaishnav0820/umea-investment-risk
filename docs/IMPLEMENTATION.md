# Implementation, checks and reproduction

The study inputs are [experiment_config.json](../config/experiment_config.json) and [benchmark_fixtures.json](../config/benchmark_fixtures.json). The configuration defines the 19 configurations, the supplementary experiments, the tax constants, calendar, seeds, sample sizes and statistical definitions. `src/umea_risk/config.py` checks every value against the study design and rejects any change, so the published results cannot silently come from different inputs. The fixtures file holds hand-worked reference values derived in [MATHEMATICAL_MODEL.md](MATHEMATICAL_MODEL.md).

| Module | Role |
|---|---|
| `scenarios.py` | Random numbers and the price transformation |
| `tax.py`, `trades.py` | Annual tax functions; purchases, sales and acquisition cost |
| `engine.py` | Scalar engine: one path at a time, with a full event ledger |
| `vector.py` | Vectorized engine: all paths, month by month |
| `metrics.py` | Expected shortfall, paired bootstrap and interval summaries |
| `audit.py`, `verification.py` | Reference-value checks, scalar/vector comparison and statistical diagnostics |
| `study.py` | Runs the complete study |
| `supplementary.py` | Starting-wealth sweep and no-threshold counterfactual |
| `report.py`, `note_content.py` | Tables, figures, research note and appendix |
| `artifacts.py` | Checks the files written by a complete run |
| `compare.py` | Compares a reproduction with the reference results |

## Engines and accounting

The scalar engine processes one price path at a time and records every event. The vectorized engine processes all paths together in a monthly loop. The two engines implement the monthly state transitions (trades, tax settlement, funding and account closure) separately, but they share the tax functions in `tax.py`, the harvest rule and parameter validation. Their agreement therefore checks the state-transition code, not the tax rules. The tax rules, trades, calendar and accounting are checked against the hand-worked reference values, which are the independent checks of the implementation.

The engines are compared at every month, transaction, assessment and settlement, and at the final outcome, for all 19 full-path examples and for the first 32 paths of each of the 19 configurations and three strategies (1,843 cases). Discrete fields (months, events, methods) must agree exactly; numerical fields within the tolerances in [MATHEMATICAL_MODEL.md](MATHEMATICAL_MODEL.md#ref-validation).

Positive signed tax is owed; negative signed tax is a credit. Assessment and settlement are separate events. Credits received before month 24 buy shares; later credits remain cash. After the final sale, outstanding taxes are settled without further returns or interest.

Purchase budgets include fees, and sale proceeds are net of fees. A sale removes acquisition cost in proportion to the shares sold. The 20%-of-proceeds deduction affects the taxable gain but not the acquisition cost of the remaining shares. A full sale sets shares and acquisition cost to zero.

When a partial sale is sized to pay a bill exactly, floating-point arithmetic can leave a tiny apparent shortfall. Both engines clear that residual only after checking it against the monetary tolerance for that operation. When the whole position cannot pay a bill, every remaining payment is external funding `F`, however small. The reported outcome is `W = bank - F`.

## Randomness and estimation

Separate PCG64 generators use these seeds:

| Use | Seed |
|---|---:|
| Primary price innovations | 20261012 |
| Paired bootstrap samples | 20261013 |
| Selection of paths for diagnostic ledgers | 20261014 |
| Independent baseline check | 20261015 |

All strategies share each price path within a configuration, and all configurations and supplementary experiments share the standard-normal innovations, transformed with their own parameters. The 2,000 bootstrap samples each contain 20,000 complete path indices and are reused for every strategy, configuration and supplementary experiment. Processing 100 draws at a time limits memory use without changing the results.

ES95 averages exactly the largest 5% of losses, including a fractional boundary observation and ties. Each bootstrap sample recomputes both strategies' ES values before subtracting them. A negative ES95 difference means the first strategy has lower tail loss. The standard error of a mean difference is also computed directly as the sample standard deviation of the paired differences divided by $\sqrt N$, and compared with the bootstrap standard deviation.

## Numerical boundaries

The analytical break-even formula applies only within its stated domain. With zero relief and a positive gains tax, no finite break-even ratio exists; with zero relief and zero gains tax, every admissible ratio gives the same wealth. `break_even_ratio` raises distinct errors for these two cases and rejects rates outside the domain.

Flat-price examples have exactly zero price profit or loss, and their expected values use zero. Small floating-point differences in other calculations are judged with absolute and relative tolerances; they are not economic effects.

## Validation

The test suite covers tax arithmetic, trades, the calendar, accounting, parameter validation, scalar/vector agreement, bootstrap pairing, analytical boundary cases, the supplementary experiments and the comparison command. A complete run also checks all 1,140,000 primary strategy-path outcomes against the accounting identity, compares price moments with their theoretical values, and compares the baseline means with an independent 20,000-path run using six combined standard errors. Every check raises an error when it fails, so the run stops; a recorded status of `passed` means that all of its assertions held. Counts in `validation_results.json` and `artifact_validation.json` are computed from the cases actually executed. Seeds are fixed in advance and are not changed after a failed check.

The research note and appendix are generated from the same source as the Markdown note and the tables. A page layout that would cross the bottom margin stops the run. `artifacts.py` re-reads the arrays, recomputes every table value and interval, checks ledger continuity, figure files and PDF page counts and metadata, and writes a file manifest.

## Reproduction and comparison

`python reproduce.py` writes everything to `reproduction/`, which Git ignores. Before and after the run it checks every file in `outputs/` against `outputs/metadata/artifact_manifest.json`, so the reference results cannot be overwritten unnoticed; it also refuses to use `outputs/` as its output directory. Its steps are: tests, complete study (`python -m umea_risk.study --output reproduction`), file checks (`python -m umea_risk.artifacts reproduction`) and comparison with the reference results.

The comparison can be repeated at any time:

```bash
python compare_results.py --reference outputs --candidate reproduction
```

It compares `tables/scenario_metrics.csv`, `tables/contrasts.csv`, both supplementary tables, `validation/validation_results.json` and `validation/test_results.json`:

- Rows are matched by scenario or experiment and by strategy or contrast. A missing, duplicated or unexpected row, a changed column, a nonfinite value or an empty/non-empty mismatch is a failure.
- Identifiers, labels, interval classifications and counts must agree exactly.
- Floating-point values must satisfy $|a-b|\le \text{atol}+\text{rtol}\cdot\max(|a|,|b|)$ with rtol $=10^{-9}$, atol $=10^{-12}$ for returns, losses, probabilities and ratios, and atol $=10^{-6}$ SEK for amounts.
- In the validation results, statuses and all counts must agree exactly. Measured residuals are platform-dependent, so they must satisfy their acceptance bounds instead of matching the reference; the moment and independent-seed diagnostics must agree within rtol $=10^{-6}$.

The tolerances follow from how results can legitimately differ. Running the same code on another platform changes only floating-point rounding (for example in `exp`, `log` and summation order). Between an earlier macOS arm64 run and the Linux x86-64 run that produced the reference results, the largest relative difference in any table cell was below $10^{-13}$, and all counts were identical. The tolerances are several orders of magnitude above that level and far below the precision at which results are reported (three decimals of a percentage, $10^{-5}$ as a fraction), so any difference that could change a reported digit fails. The comparison prints the number of rows and cells and the largest absolute and relative differences for each file, and writes a JSON report to `reproduction/validation/comparison_report.json`. A test in `tests/test_compare.py` confirms that an altered estimate, interval, count, identifier, missing row or nonfinite value is detected.

**Hashes.** SHA-256 file hashes in `artifact_manifest.json` verify that files are intact. Within a run, `reproduction/arrays/registry.json` also records SHA-256 hashes of the raw bytes of every saved array, which `artifacts.py` uses to check that the arrays were saved and read back unchanged. Raw floating-point hashes are not expected to agree across platforms, even for the standard-normal innovations, so cross-platform agreement is judged with the tolerances above. `outputs/metadata/run_metadata.json` records the environment of the reference run (software version, Python, platform and dependency versions), input-file hashes, seeds, price-model hashes and the measured maximum accounting residual for that run.

**Reference results.** `outputs/` contains the subset of a complete run listed in `REFERENCE_FILES` in `compare.py`: the note, figures, tables, supplementary tables, validation summaries and run metadata. It was copied from a complete run with `umea_risk.compare.publish_reference`, which also writes the manifest. Arrays, ledgers and logs are regenerated by `reproduce.py` and are not stored in the repository.

To rebuild the tables, figures and documents from an existing run without simulating again:

```bash
PYTHONPATH=src python -m umea_risk.report reproduction
PYTHONPATH=src python -m umea_risk.artifacts reproduction
```
