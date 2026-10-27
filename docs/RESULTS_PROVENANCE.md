# Results provenance

This file records, for every quantitative claim this project has made, whether
the claim is reproducible from code in this repository. A ledger like this is
cheap to maintain and lets a reader check any figure against the cell that
produced it, instead of taking the write-up's word for it.

Audit date: 2026-10-26. Source audited: `notebooks/exploratory_model.ipynb`
(the original Colab notebook, preserved unmodified), plus the LaTeX sources in `paper/`.

Three tiers are used:

- **Reproducible** — the notebook contains the code and its saved output.
- **Pending the controlled re-run** — reported in earlier analysis, but not
  recomputable from the code released here.
- **Updated in this version** — the current write-up and the code now agree;
  these rows record where an earlier description differed.

---

## Reproducible

| Claim | Value | Where |
| --- | --- | --- |
| Dataset | HAM10000, 10,015 images, 7 classes | notebook cells 9-20 |
| Rebalanced pool after oversampling | 35,000 rows (5,000 per class, `replace=True`, seed 42) | cell 22-23 |
| Split sizes | 24,500 train / 5,250 val / 5,250 test | cell 26 |
| Classifier | EfficientNetB0, ImageNet weights, base frozen, GAP + dropout 0.3 + dense(7) | cell 29 |
| Trainable parameters | 8,967 of 4,058,538 | cell 29 output |
| Stage-1 training | 48 epochs, early stopping on val loss (patience 5), Adam, ReduceLROnPlateau | cell 30 |
| Stage-1 best val accuracy | 0.8541 | cell 30 output, epoch 46 |
| Stage-1 test accuracy | 0.85 on 5,250 images (750 per class) | cell 34 output |
| Stage-1 macro F1 | 0.85 | cell 34 output |
| Low-brightness rows found | 40 rows at mean grey intensity < 110 | cell 43 output |
| DCGAN | 64x64, 100-dim noise, 400 epochs, batch 32, Adam 1e-4 both networks | cells 55-57 |
| GAN training input | `X_dark` of shape (40, 64, 64, 3) | cell 50, 58 outputs |
| Synthetic images added | 3,500 (500 per class label) | cell 61-62 outputs |
| Augmented training set | 28,000 rows | cell 62 output |
| Stage-2 training | 50 further epochs, no early stopping | cell 64 |
| Stage-2 test accuracy | 0.80 on 1,050 images (150 per class) | cell 66 output |
| Per-class precision/recall/F1, both stages | as published in the manuscript | cells 34 and 66 outputs, but see the label-order section: the disease names attached to them are wrong |
| Test-set overlap under the original split order | 72% of test rows also in training | `scripts/leakage_demo.py`, simulated |

## Pending the controlled re-run

The following come from earlier analysis whose code was not preserved, so they
cannot be recomputed from this repository. They appear in
`paper/mdpi_version.tex` and in the archived notes under `docs/archive/`, marked
as provisional in both.

| Claim | Reported value |
| --- | --- |
| Equalized-odds difference, stage 1 | 0.13 |
| Equalized-odds difference, stage 2 | 0.07 |
| Dark-skin test subgroup size | N = 12 |
| Light-skin comparison subgroup | 500 images sampled at intensity > 140 |
| Per-group accuracy, TPR, FPR tables | all cells |
| Significance of the accuracy change | p < 0.001, 95% CI -6.2% to -3.8% |
| Effect size | Cohen's h = 0.13 |
| Sample-size ablation | 10 images -> 0.75, 20 -> 0.78, 40 -> 0.80 |
| Minimum data requirement | "> 100-200 samples" |
| Imbalanced baseline accuracy | 76% (the "+9 points" reference point) |
| GAN training cost | 8 hours on an RTX 3080 |

The sample-size ablation needs the most care of these: the notebook trains one
DCGAN on all 40 rows at once, so a 10-image and a 20-image run would have to be
added to support a threshold.

`scripts/run_experiment.py` and `src/skinfair/fairness.py` in this repository now
implement the subgroup and significance analysis these numbers require. They are
reported as provisional until that pipeline has been run end to end.

## Updated in this version

| Earlier description | What the code does |
| --- | --- |
| DullRazor hair removal | no hair removal |
| Histogram equalisation for colour normalisation | none |
| ImageNet mean/std normalisation | `efficientnet.preprocess_input` |
| GAN images resized to 256x256 | 64x64 (`IMG_SIZE = 64`) |
| Augmentation: rotation, flip, brightness, zoom in the baseline | no augmentation layer or `ImageDataGenerator` anywhere |
| Baseline and GAN-augmented are two trained models | stage 2 continues training the stage-1 weights for 50 more epochs |
| Both evaluated on the same test set | stage 1 on 5,250 images, stage 2 on 1,050 |
| 40 dark-skin images | 40 rows containing 29 distinct images, duplicated by oversampling |
| Class-conditional synthetic data | one unconditional generator; the 7 class labels were assigned to its output by filename |
| GAN label smoothing (0.9 real / 0.1 fake) | plain BCE against `tf.ones_like` / `tf.zeros_like`, hard targets |
| GAN Adam with beta1 = 0.5 | `Adam(1e-4)` with the Keras default beta1 = 0.9 |

The two GAN rows surfaced during the manuscript revision rather than the first
pass. `src/skinfair/gan.py` now implements one-sided label smoothing and
beta1 = 0.5 as deliberate choices, so the current code and description agree.

## Three design points that the 85% vs 80% comparison turns on

1. **Oversampling precedes the split.** `resample(..., replace=True)` runs in cell 22,
   `train_test_split` in cell 26. Identical images therefore appear in train, val and
   test. Both accuracies are optimistic and neither is an estimate of generalisation.
   Evidence: the 40 low-brightness rows contain 29 distinct `image_id` values, and
   `ISIC_0027669` appears four times in that subset alone. HAM10000 also contains
   multiple images per `lesion_id` -- 1,956 of 7,470 lesions, covering 4,501 of
   10,015 images -- so a lesion-level split is required, not merely a
   deduplicated one.

   **How large is the inflation? Measured, and smaller than expected.**
   `scripts/leakage_demo.py` simulates this protocol on synthetic data matched to
   HAM10000's class imbalance and repeat-image structure, then trains under both
   split orders. Two findings, over 3 seeds:

   - Oversampling to 5,000 rows per class and splitting afterwards leaves
     **72% of the test set also present in the training set**. That is a property
     of the protocol and does not depend on the model.
   - How much that inflates the reported accuracy depends on model capacity. A
     random forest, which can memorise individual rows, gains between 7 and 34
     accuracy points. A multinomial linear head on fixed features gains
     essentially nothing: between -0.9 and +3.4 points, straddling zero.

   The real experiment froze EfficientNetB0 and trained 8,967 parameters, which
   is the linear-head case. So the honest conclusion is narrower than "the 85% is
   inflated": the memorisation channel was largely unavailable to this model, and
   the leakage may have cost little accuracy. What remains true regardless is
   that the figure was measured on a test set that was both contaminated and
   re-balanced by duplication, so it is not comparable to any accuracy measured
   on HAM10000's natural distribution, and it is not a generalisation estimate.
   Points 2 and 3 below are untouched by this result.

   The simulation has its own confound, stated in its output: protocol A's test
   set is class-balanced while protocol B's is natural, so the accuracy columns
   are not strictly comparable. Macro-F1 is reported alongside for that reason,
   and it conflates the same two effects in the opposite direction. The only way
   to settle the real magnitude is to rerun the real experiment.

2. **The test sets differ.** Stage 1 reports support of 750 per class, stage 2 reports
   150 per class. A 5-point drop between two different test sets of different size
   is not a measured effect of the intervention.

3. **The synthetic labels carry no class information.** One unconditional DCGAN
   trained on 29 distinct images produced all 3,500 samples; cell 61 then labelled
   500 of them `class_0`, 500 `class_1`, and so on, by filename. 12.5% of the
   augmented training set is therefore label noise drawn from a single distribution.
   This is sufficient on its own to explain a drop in accuracy, so the experiment
   does not isolate "GAN augmentation" as the cause.

A fourth issue limits any fairness reading: mean grey intensity under 110 selects
dark *lesions*, not dark *skin*. Of the 40 rows, 24 are melanoma and 9 are nevi,
both classes whose lesions are heavily pigmented. HAM10000 ships no Fitzpatrick
or skin-tone labels, so the subgroup is confounded with diagnosis, and a model
that appears to improve on it may simply be predicting melanoma more often.

## Class label order: per-class rows need their disease names corrected

Cell 22 builds the label mapping from `df['dx'].unique()`, the order the
diagnoses first appear in the metadata CSV. On the copy of
`HAM10000_metadata.csv` in this repository that order is:

    0 bkl   1 nv   2 df   3 mel   4 vasc   5 bcc   6 akiec

Cell 14 separately hardcodes an unrelated list, `['bkl', 'bcc', 'akiec',
'vasc', 'nv', 'mel', 'df']`, which is never used to build the mapping. The
Streamlit app and the archived results notes both read index to disease name
off that second list. Only index 0 agrees between the two orderings.

Consequences:

- **The app showed a different disease name than the model intended, for six of
  seven classes.** Index 1
  means melanocytic nevi, a benign mole, and was shown as basal cell carcinoma.
  The logged history in the original repository shows `ISIC_0024307`, whose true
  diagnosis is `nv`, reported as Dermatofibroma, which is consistent with the
  mapping. `app.py` now derives the order from the metadata, or reads it from
  `models/label_order.json`.
- **Per-class rows need relabelling.** The row reported as `vasc` with F1 0.72
  is index 3, which is melanoma. The per-class numbers are genuine outputs; only
  the disease names attached to them need correcting. Macro and overall figures
  are unaffected, since they do not depend on the order.

This is also why `src/skinfair/config.py` fixes `CLASSES` alphabetically and
`gan.save_synthetic` writes the diagnosis code into each filename: no part of
the pipeline should depend on the row order of a CSV.

## What a defensible version of this experiment requires

Implemented in `scripts/run_experiment.py`:

- group-aware split on `lesion_id` before any resampling, asserted non-overlapping;
- rebalancing applied to the training split only;
- one fixed test set shared by every arm, never resampled;
- each arm trained from the same initialisation, independently, over several seeds;
- a class-conditional generator, so synthetic labels mean something;
- subgroup metrics with bootstrap intervals and McNemar's test on paired predictions;
- the brightness proxy reported as a proxy, with its diagnosis confound measured;
- a label order that does not depend on CSV row order, recorded with the weights.

Until those runs exist, the summary in `README.md` stands: a 7-class baseline
whose headline number is measured on a contaminated and rebalanced test set, and
a synthetic-augmentation arm whose comparison was not controlled.
