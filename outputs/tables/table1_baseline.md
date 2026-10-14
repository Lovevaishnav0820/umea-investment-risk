# Table 1. Baseline results

Returns, losses and intervals are in percent; contrasts are in percentage points (pp). Intervals are approximate pointwise 95% Monte Carlo intervals conditional on the model (N = 20,000 paths, 2,000 paired bootstrap draws). For ES95 differences (A minus B), negative values mean lower tail loss for A.

| Strategy | Mean return [MC interval] | ES95 [MC interval] | P(W < W0) | P(W ≤ 0) | Funding events | Mean fees, SEK | Harvest frequency |
|---|---|---|---|---|---|---|---|
| ISK hold | 11.010 [10.473, 11.559] | 49.165 [48.563, 49.763] | 44.995% | 0.000% | 0 of 20,000 | 1,059.91 | 0.00% |
| Depå hold | 7.438 [7.045, 7.841] | 39.855 [39.336, 40.372] | 44.155% | 0.000% | 0 of 20,000 | 1,059.97 | 0.00% |
| Depå harvest | 7.244 [6.850, 7.647] | 39.691 [39.177, 40.218] | 44.850% | 0.000% | 0 of 20,000 | 1,379.42 | 37.83% |

No path required external funding. With zero events in N = 20,000 paths, an approximate one-sided 95% upper bound on the probability is 3/N = 0.015% under this model.

| Contrast | Mean difference [MC interval], pp | ES95 difference [MC interval], pp | P(difference > 0) | SE of mean difference, pp |
|---|---|---|---|---|
| Harvest − hold | -0.194 [-0.201, -0.186] | -0.164 [-0.202, -0.131] | 8.33% | 0.00362 |
| Harvest − ISK | -3.765 [-3.913, -3.622] | -9.474 [-9.564, -9.386] | 45.38% | 0.07567 |
| Hold − ISK | -3.572 [-3.720, -3.430] | -9.310 [-9.394, -9.227] | 47.48% | 0.07597 |
