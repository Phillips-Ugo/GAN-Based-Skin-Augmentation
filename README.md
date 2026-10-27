# Skin Disease Diagnosis: An Exploratory Study in Medical AI Safety

An exploratory project on measurement validity in dermatology AI: whether the
accuracy and fairness numbers a skin-lesion classifier reports actually measure
what they are taken to measure.

The system under study is an EfficientNetB0 classifier trained on HAM10000 with
class rebalancing and DCGAN-generated synthetic images, together with a
Streamlit application that delivers predictions, condition information and
nearby-care lookup. The manuscript in `paper/` reports the experiment as
*Exploratory Evaluation of Class Rebalancing and GAN Augmentation for
Skin-Lesion Classification*.

The project's useful output turned out to be methodological. Four questions
about evaluation came up while building it, each of which has a general answer
worth documenting, and each of which is examined here with code rather than
argued in the abstract. Every number below is tied to an artifact in this
repository.

Not a medical device. Not validated for clinical use. See
[Intended use](#intended-use).

---

## Four questions about evaluating a medical classifier

**1. Does a brightness proxy measure skin tone?** HAM10000 carries no
Fitzpatrick annotation, so subgroup analysis needs a proxy, and mean image
intensity is the obvious candidate. It does not hold up. Of the 40
low-brightness rows, 24 are melanoma and 9 are nevi, against an 11% melanoma
base rate in the dataset. Mean intensity selects dark *lesions*, not dark
*skin*, so the subgroup is confounded with the diagnosis label: a model scoring
better on it may only be predicting melanoma more often, and always predicting
melanoma scores 60% there while being clinically useless.

The general point is that a proxy correlated with the target rather than the
protected attribute will reward the wrong behaviour, and the fairness metric
computed on it gives no indication. `src/skinfair/data.py` reports each
subgroup's diagnosis mix against the dataset base rate, so the confound is
visible beside any number derived from it.

**2. How much does split order change a reported accuracy?** Oversampling to
5,000 rows per class before the train/test split, rather than after, places
identical images on both sides. I measured the size of that effect instead of
assuming it:

| | Result |
| --- | --- |
| Test rows also present in training | 72% |
| Accuracy gained by a high-capacity model | up to 34 points |
| Accuracy gained by a frozen linear head | about zero |

The result is more interesting than the obvious prediction. Contamination is
substantial, but exploiting it requires capacity to memorise individual rows,
and this classifier trained 8,967 parameters on a frozen base. The reported 85%
is therefore close to what that architecture would score anyway, while still not
being a generalisation estimate, since the test set was both contaminated and
rebalanced by duplication. Reproduce with `python scripts/leakage_demo.py`.

Two related design points stand independently of that finding. The two training
arms were scored on test sets of different size, 750 against 150 images per
class, so the 85% and 80% are not comparable quantities. And the 3,500 synthetic
images came from a single unconditional generator with class labels assigned by
output filename, which makes roughly an eighth of the augmented training set
label noise drawn from one distribution. The 85-to-80 difference is a
consequence of the design, not a measurement of synthetic augmentation.

**3. What can metrics not detect?** The application mapped class indices to
disease names using a hardcoded list, while training derived its label order
from the order diagnoses appear in the metadata CSV. The two orders agree only
at index 0. Index 1 denotes melanocytic nevi, a benign mole, and reached the
user as basal cell carcinoma.

This is the most instructive finding in the project, because the model was
correct and every metric was computed on integer labels and was therefore
unaffected. Accuracy, F1 and subgroup rates were all blind to it. The failure
lived entirely in the translation from an integer to the words a person reads,
which no metric scored. The same mismatch means the per-class rows in earlier
write-ups carry the wrong disease names: the row labelled vascular lesions is
melanoma. `app.py` now derives the order from the metadata and surfaces its
provenance in the result view, and the pipeline fixes the order alphabetically
so nothing depends on CSV row order.

**4. Which reported numbers does the released code reproduce?** Not all of
them. The equalized-odds improvement from 0.13 to 0.07, the 12-image subgroup,
the per-group rate tables, the significance tests and a sample-size ablation
come from earlier analysis whose code was not preserved, so they cannot be
recomputed here. They are marked as such wherever they appear rather than
restated as findings, and `src/skinfair/fairness.py` now implements the analysis
that would produce them.

[`docs/RESULTS_PROVENANCE.md`](docs/RESULTS_PROVENANCE.md) sorts every
quantitative claim into reproducible from code, pending the controlled re-run,
or updated in this version, naming the notebook cell behind each one. Keeping
that ledger explicit is cheap and makes the rest of the repository easier to
trust.

## What is reproducible today

| | Value | Status |
| --- | --- | --- |
| Dataset | HAM10000, 10,015 images, 7 classes | reproducible |
| Classifier | EfficientNetB0, frozen base, 8,967 trainable parameters | reproducible |
| Stage-1 test accuracy | 0.85, macro-F1 0.85 | reproducible, contaminated test set |
| Stage-2 test accuracy | 0.80 | reproducible, different test set |
| Low-brightness rows | 40 rows / 29 distinct images | reproducible |
| Test-set contamination, original split order | 72% of test rows seen in training | simulated |
| DCGAN | 64x64, 400 epochs, 29 distinct training images | reproducible |
| Per-class metrics by disease | as published | disease names corrected, see question 3 |
| Equalized-odds difference | 0.13 -> 0.07 | pending the re-run |
| Sample-size threshold | ">100-200 images" | pending dedicated runs |

**What the study supports:** a documented end-to-end pipeline from HAM10000 to a
working demonstrator, and the narrow negative result that a DCGAN trained on 29
distinct images does not yield useful augmentation. Establishing *how much* data
would suffice requires runs at several subset sizes, which this study did not
perform.

## The controlled pipeline

`scripts/run_experiment.py` is the design the original questions need, with each
component addressing one of the points above:

- **Lesion-grouped split, before any resampling.** 1,956 of HAM10000's 7,470
  lesions contribute more than one image, 4,501 images in total, so even a
  deduplicated image-level split leaks near-identical views of one lesion.
  `assert_no_leakage` runs after the split and again after rebalancing, and
  raises on any shared lesion or image, so the property is checked rather than
  assumed.
- **Rebalancing confined to the training split.** The test set is never
  resampled.
- **One shared test set across every arm**, which makes predictions paired and
  an exact McNemar test meaningful.
- **Fresh initialisation per arm, three seeds**, so arms differ only in their
  training data.
- **A class-conditional generator**, so a synthetic image labelled `mel` comes
  from the melanoma condition. This does not make 29 images sufficient; it
  removes one confound so the question can be asked cleanly.
- **Metrics that decline to report what they cannot support.** The
  equalized-odds difference returns nothing when a rate is undefined, carries
  `min_group_n`, and ships with a stratified bootstrap interval. A value
  computed over 12 images moves by more than its own magnitude when one image
  changes label, and the interval makes that legible.
- **A generator memorisation check**, since a DCGAN reproducing its training
  images would make augmentation a form of duplication.

[`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md) fixes the arms, the primary
metric, the decision rules and the checks that would invalidate a positive
subgroup result, before the run rather than after. Macro-F1 is the primary
metric rather than accuracy, because a leakage-free HAM10000 test set is 66%
nevi and 66% is reachable by always guessing the majority class.

Three things run immediately, with no images and no GPU:

```bash
python scripts/leakage_demo.py                      # sizes the contamination effect
python scripts/run_experiment.py --metadata-only    # audits the corrected split
pytest tests/ -q                                    # 24 tests, about one second
```

The split audit yields 7,025 / 1,486 / 1,504 with zero lesion overlap between
any pair of splits and all seven classes present in test. The leakage study is a
simulation of the mechanism rather than a re-run, and it reports its own
confound: protocol A's test set is balanced while protocol B's is natural, so
accuracy is not strictly comparable across those columns, and macro-F1 is given
alongside.

The full run needs the image archives and a GPU:

```bash
python scripts/run_experiment.py \
    --image-dir data/HAM10000_images_part_1 \
    --image-dir data/HAM10000_images_part_2 \
    --arms imbalanced resampling_only synthetic_augmented \
    --seeds 0 1 2
```

Results land in `results/` as JSON. Adding `--unconditional-gan` reproduces the
original label-assignment condition for comparison.

## Install

```bash
git clone https://github.com/Phillips-Ugo/GAN-Based-Skin-Augmentation.git
cd GAN-Based-Skin-Augmentation
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Tests need neither TensorFlow nor the images:

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
```

### Data

`data/HAM10000_metadata.csv` is included. The images are not, at 2.9GB. Download
`HAM10000_images_part_1` and `HAM10000_images_part_2` from the
[Harvard Dataverse record](https://doi.org/10.7910/DVN/DBW86T) or
[the Kaggle mirror](https://www.kaggle.com/datasets/kmader/skin-cancer-mnist-ham10000)
and unzip both into `data/`.

## The demonstrator app

```bash
streamlit run app.py
```

Three components: EfficientNetB0 lesion classification with confidence scores, a
Gemini-backed chatbot for condition information, and a geolocation hospital
lookup. The chatbot needs `GEMINI_API_KEY` and the hospital lookup needs
`GOOGLE_API_KEY`, read from the environment or a local `.env`; each degrades to
an explanatory message when its key is absent, and classification works without
any key. Every page carries the research disclaimer, and the result view names
the label-order provenance.

The bundled weights in `models/` are a pickled Keras object from the original
Colab session, which is why `app.py` carries a fallback loader: a pickled model
cannot be read by a different TensorFlow version. Models written by the current
pipeline use the portable `.keras` format and record their label order.

## Intended use

A research demonstrator for studying dataset bias, synthetic augmentation and
evaluation methodology. It is **not** a medical device, has not been clinically
validated, and must not be used for diagnosis or to inform a care decision. Its
training data is dermatoscopic images from a predominantly light-skinned
European population, so its behaviour on darker skin is both untested and the
open question this project exists to study. Anyone concerned about a skin lesion
should see a clinician.

## Repository layout

```
app.py                      Streamlit demonstrator
src/skinfair/               pipeline: config, data, classifier, gan, fairness
scripts/run_experiment.py   the controlled comparison, with --metadata-only audit
scripts/leakage_demo.py     sizes the effect of split order on reported accuracy
tests/                      24 tests for the split policy and fairness metrics
notebooks/                  the original Colab notebook, preserved unmodified
paper/                      LaTeX manuscript, bibliography, figures
docs/RESULTS_PROVENANCE.md  which claims the released code reproduces
docs/EXPERIMENT_PLAN.md     hypotheses and decision rules, fixed before the run
docs/archive/               earlier drafts and process notes
data/                       HAM10000 metadata, chatbot fine-tuning data
models/                     weights from the original Colab session
results/                    split audit and leakage study output (JSON)
.github/workflows/          CI: tests, the split audit, and a lint pass
```

`notebooks/exploratory_model.ipynb` is preserved exactly as it ran, with a
banner describing its known limitations. It is the record the provenance ledger
refers to, so editing it in place would break that reference.

## Known limitations

- The 85% and 80% figures are not estimates of generalisation, and the
  controlled pipeline has not yet been run to replace them.
- The subgroup and fairness figures in `paper/` are not reproducible from this
  code and are marked accordingly.
- Brightness is a proxy for skin tone, confounded with diagnosis, and no
  validated skin-tone labels exist for HAM10000. Fitzpatrick17k is the obvious
  next dataset, and the real test of question 1 above.
- A subgroup of 12 test images cannot support a two-decimal fairness claim at
  any level of statistical care.
- The DCGAN sees 29 distinct images, which no architectural choice compensates
  for.
- The leakage study is synthetic. It sizes a mechanism; it does not predict what
  the real re-run will produce.
- `models/` holds pickled Keras objects, unloadable across TensorFlow versions.
  `models/label_order.json` records the inferred label order, which is an
  inference from the metadata rather than a record of the training run.
- The chatbot is a general-purpose model with a system prompt, not a clinically
  validated information source.

## Citation

Please cite this as an exploratory study and carry the caveats with the numbers.

```bibtex
@misc{ogwumike2026skinfair,
  author = {Ogwumike, Ugochukwu Belusochim Phillips},
  title  = {Exploratory Evaluation of Class Rebalancing and GAN Augmentation
            for Skin-Lesion Classification},
  year   = {2026},
  note   = {Exploratory study; see docs/RESULTS_PROVENANCE.md for claim provenance},
  url    = {https://github.com/Phillips-Ugo/GAN-Based-Skin-Augmentation}
}
```

## Acknowledgments

HAM10000 is by Tschandl, Rosendahl and Kittler
([Scientific Data, 2018](https://doi.org/10.1038/sdata.2018.161)). Built with
TensorFlow, Keras and Streamlit.

## License

MIT, see [LICENSE](LICENSE). HAM10000 is distributed under CC BY-NC 4.0 and is
not redistributed here.
