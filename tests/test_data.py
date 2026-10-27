"""Tests for the split policy. The leakage test is the point of this file."""

import numpy as np
import pandas as pd
import pytest

from skinfair import data
from skinfair.config import CLASSES, DataConfig


def make_metadata(n_lesions: int = 400, seed: int = 0) -> pd.DataFrame:
    """Synthetic metadata shaped like HAM10000: skewed classes, repeat lesions."""
    rng = np.random.default_rng(seed)
    weights = np.array([0.033, 0.051, 0.110, 0.011, 0.111, 0.670, 0.014])
    weights = weights / weights.sum()
    rows = []
    for lesion in range(n_lesions):
        dx = CLASSES[rng.choice(len(CLASSES), p=weights)]
        for image in range(rng.choice([1, 1, 2, 3])):
            rows.append(
                {
                    "lesion_id": f"HAM_{lesion:05d}",
                    "image_id": f"ISIC_{lesion:05d}_{image}",
                    "dx": dx,
                    "label": CLASSES.index(dx),
                    "image_path": f"/fake/ISIC_{lesion:05d}_{image}.jpg",
                }
            )
    return pd.DataFrame(rows)


def test_grouped_split_shares_no_lesion_or_image():
    df = make_metadata()
    train, val, test = data.grouped_split(df, DataConfig())

    for key in ("lesion_id", "image_id"):
        assert not set(train[key]) & set(test[key])
        assert not set(train[key]) & set(val[key])
        assert not set(val[key]) & set(test[key])
    assert len(train) + len(val) + len(test) == len(df)


def test_grouped_split_keeps_every_class_in_the_test_set():
    df = make_metadata(n_lesions=600, seed=3)
    _, _, test = data.grouped_split(df, DataConfig())
    assert set(test["dx"]) == set(df["dx"].unique())


def test_grouped_split_is_deterministic_for_a_seed():
    df = make_metadata()
    first = data.grouped_split(df, DataConfig(seed=7))[2]["image_id"].tolist()
    second = data.grouped_split(df, DataConfig(seed=7))[2]["image_id"].tolist()
    assert first == second
    other = data.grouped_split(df, DataConfig(seed=8))[2]["image_id"].tolist()
    assert first != other


def test_assert_no_leakage_rejects_a_shared_image():
    df = make_metadata()
    train, val, test = data.grouped_split(df, DataConfig())
    poisoned = pd.concat([train, test.head(1)], ignore_index=True)
    with pytest.raises(data.LeakageError, match="appears in split"):
        data.assert_no_leakage(poisoned, val, test)


def test_resampling_before_splitting_leaks_which_is_the_original_defect():
    """Regression test for the notebook's ordering bug.

    The notebook oversampled to 5,000 rows per class and split afterwards, so
    the same image landed in train and test. This test asserts that the broken
    order really does leak, so the guard above cannot be quietly removed.
    """
    df = make_metadata()
    pool = data.rebalance(df, samples_per_class=500, seed=42)
    cut = int(len(pool) * 0.7)
    bad_train, bad_test = pool.iloc[:cut], pool.iloc[cut:]
    assert set(bad_train["image_id"]) & set(bad_test["image_id"])

    train, val, test = data.grouped_split(df, DataConfig())
    good_train = data.rebalance(train, samples_per_class=500, seed=42)
    assert not set(good_train["image_id"]) & set(test["image_id"])
    data.assert_no_leakage(good_train, val, test)


def test_rebalance_hits_the_target_and_flags_duplicates():
    df = make_metadata()
    out = data.rebalance(df, samples_per_class=300, seed=1)
    counts = out["label"].value_counts()
    assert set(counts.values) == {300}
    assert len(counts) == len(CLASSES)
    # A rare class oversampled to 300 must contain duplicated images.
    rare = out[out["dx"] == "df"]
    assert rare["is_duplicate"].any()


def test_rebalance_none_leaves_the_distribution_alone():
    df = make_metadata()
    out = data.rebalance(df, samples_per_class=None, seed=1)
    assert len(out) == len(df)
    assert not out["is_duplicate"].any()


def test_assign_subgroup_and_report_expose_the_diagnosis_confound():
    df = make_metadata(n_lesions=200)
    rng = np.random.default_rng(0)
    # Melanoma darker than the rest, the pattern seen in the real data.
    df["brightness"] = np.where(
        df["dx"] == "mel", rng.uniform(80, 105, len(df)), rng.uniform(145, 200, len(df))
    )
    tagged = data.assign_subgroup(df, DataConfig())
    report = data.subgroup_report(tagged)

    assert report["low_brightness"]["dx_counts"].get("mel", 0) > 0
    assert report["low_brightness"]["dx_distribution"]["mel"] > report["overall_dx_distribution"]["mel"]
    assert report["low_brightness"]["n_unique_images"] <= report["low_brightness"]["n_rows"]


def test_assign_subgroup_requires_brightness():
    with pytest.raises(ValueError, match="attach_brightness"):
        data.assign_subgroup(make_metadata(), DataConfig())


def test_load_metadata_rejects_unknown_diagnosis(tmp_path):
    bad = make_metadata(n_lesions=5)
    bad.loc[0, "dx"] = "not_a_class"
    path = tmp_path / "meta.csv"
    bad.to_csv(path, index=False)
    with pytest.raises(ValueError, match="unexpected diagnosis codes"):
        data.load_metadata(DataConfig(metadata_csv=path))


def test_leakage_demo_protocols_differ_in_contamination():
    """The simulation's two protocols must really differ in what they leak.

    Small and fast: this guards the mechanism, not the effect size. The effect
    size is measured by scripts/leakage_demo.py, which needs scikit-learn.
    """
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "leakage_demo", Path(__file__).resolve().parents[1] / "scripts" / "leakage_demo.py"
    )
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)

    rng = np.random.default_rng(0)
    X, y, lesions = demo.make_dataset(200, 4, 0.15, 0.8, rng)

    a = demo.protocol_a(X, y, lesions, 40, 0.15, 0, "logreg")
    b = demo.protocol_b(X, y, lesions, 40, 0.15, 0, "logreg")

    # The notebook's order contaminates most of its own test set.
    assert a["fraction_of_test_seen_in_training"] > 0.3
    assert a["distinct_images_in_both_splits"] > 0
    # The corrected order contaminates none of it.
    assert b["fraction_of_test_seen_in_training"] == 0.0
    assert b["distinct_images_in_both_splits"] == 0
