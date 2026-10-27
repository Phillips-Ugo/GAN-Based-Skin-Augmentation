# Experiment plan for the corrected run

Written before running `scripts/run_experiment.py`, so the analysis is fixed in
advance rather than chosen after seeing the numbers. Fixing the decision rules
up front is the cheapest safeguard available against reading a null result as a
positive one.

Status: not yet run. Needs the HAM10000 image archives and a GPU.

## The question

Does adding DCGAN-generated images to a rebalanced HAM10000 training set change
classification performance, and does it change performance on the
low-brightness subgroup specifically?

The prior, after the exploratory stage: **no useful effect, and plausibly a
harmful one.** A generator trained on 29 distinct images has very little to
learn from. This run is designed to measure that cleanly.

## Arms

All three share one test set, one preprocessing path, and one initialisation
scheme. They differ only in training rows.

| Arm | Training data |
| --- | --- |
| `imbalanced` | the natural training split, no rebalancing |
| `resampling_only` | rebalanced to 5,000 rows per class, training split only |
| `synthetic_augmented` | `resampling_only` plus 500 conditional-DCGAN images per class |

`--unconditional-gan` adds a fourth condition reproducing the original
label-assignment scheme, to test whether the label noise, rather than synthetic
data as such, accounts for the earlier drop.

## Design commitments

1. **Split on `lesion_id`, before any resampling.** Asserted by
   `assert_no_leakage`, which runs after the split and again after rebalancing.
2. **The test set is fixed, natural-distribution, and never resampled.** It is
   identical across arms and seeds, so predictions are paired.
3. **Three seeds per arm**, each a fresh initialisation. No arm continues
   another's weights.
4. **Primary metric: macro-F1.** Not accuracy. A leakage-free HAM10000 test set
   is 66% nevi, so accuracy is dominated by one class and a 66% score is
   obtainable by always predicting it.
5. **Paired significance by exact McNemar**, on the shared test set, for
   `resampling_only` against `synthetic_augmented`.
6. **Subgroup metrics carry their uncertainty.** Equalized-odds difference is
   reported with `min_group_n` and a stratified bootstrap interval, and returns
   nothing at all when a rate is undefined.

## Decision rules, fixed in advance

- Synthetic augmentation **helps** only if mean macro-F1 rises in every seed and
  McNemar favours it at p < 0.05 in the majority of seeds.
- Synthetic augmentation **hurts** if mean macro-F1 falls in every seed.
- Anything else is **no detectable effect**, and will be reported as that. A
  change in a subgroup metric alone does not upgrade this verdict.
- Any fairness claim requires the bootstrap interval for the equalized-odds
  difference to exclude the other arm's point estimate. With a subgroup of
  roughly a dozen images this will almost certainly fail, and the expected
  reportable outcome is "underpowered", not a number.

## Checks that would invalidate a positive subgroup result

These are the ways a fairness improvement could be an artefact. Each is
computed and reported, not left to the reader.

1. **The diagnosis confound.** In the low-brightness rows, 24 of 40
   were melanoma. A model that always predicts melanoma scores 60% accuracy on
   that subgroup while being useless. `subgroup_report()` prints each subgroup's
   diagnosis mix against the dataset base rate, and a trivial always-melanoma
   baseline will be scored on the subgroup for comparison.
2. **Generator memorisation.** If the DCGAN reproduces its 29 training images,
   synthetic augmentation is duplication wearing a different hat.
   `nearest_neighbour_distances` reports the distance from each synthetic image
   to its closest real one.
3. **Subgroup instability.** If flipping one test image moves the
   equalized-odds difference by more than the effect being claimed, there is no
   effect to claim. The bootstrap interval captures this.
4. **Brightness threshold sensitivity.** The 110 cutoff is arbitrary. Any
   subgroup conclusion that does not survive a sweep of the threshold is a
   property of the cutoff, not of the model.

## What this run cannot settle

Validated skin-tone fairness. HAM10000 has no Fitzpatrick labels, and no
analysis of brightness proxies will produce them. That needs a dataset with
expert skin-tone annotation, Fitzpatrick17k being the obvious candidate, and
that is the next project rather than a fix to this one.

## Reporting commitment

Whatever the outcome, the result goes into `README.md` and
`docs/RESULTS_PROVENANCE.md` with the arms, seeds, intervals and the decision
rule that was applied. A null result is the expected outcome and is reportable
as one. Numbers the pipeline does not produce do not get reported.
