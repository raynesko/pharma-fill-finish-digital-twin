import numpy as np
import pandas as pd
import pytest

from ffdt.experiments import stats as S


def test_known_difference_is_recovered():
    rng = np.random.default_rng(1)
    common = rng.normal(1000, 50, size=30)  # shared noise, as with common random numbers
    base = common + rng.normal(0, 5, 30)
    scen = common + 40 + rng.normal(0, 5, 30)
    r = S.paired(base, scen)
    assert r.ci_low < 40 < r.ci_high
    assert r.p < 1e-6
    assert r.half_width < r.unpaired_half_width / 3  # pairing removes the shared noise


def test_no_difference_gives_ci_covering_zero():
    rng = np.random.default_rng(2)
    base = rng.normal(0, 1, 30)
    scen = base + rng.normal(0, 0.1, 30)
    r = S.paired(base, scen)
    assert r.ci_low < 0 < r.ci_high and r.p > 0.05


def test_bootstrap_agrees_with_t_ci():
    rng = np.random.default_rng(3)
    base = rng.normal(100, 10, 30)
    scen = base + rng.normal(2, 1, 30)
    r = S.paired(base, scen)
    for a, b in ((r.ci_low, r.boot_low), (r.ci_high, r.boot_high)):
        assert abs(a - b) < 0.15 * r.half_width + 1e-12


def test_holm_matches_hand_computation():
    p = [0.01, 0.04, 0.03, 0.005]
    # sorted: 0.005*4=0.02, 0.01*3=0.03, 0.03*2=0.06, 0.04*1=0.04 -> monotone max 0.06
    assert S.holm(p) == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert S.holm([0.5, 0.9]).max() <= 1.0


def test_practical_flag():
    assert S.practical_flag("good_per_ppt_hour", 1000, 30) is True
    assert S.practical_flag("good_per_ppt_hour", 1000, 29) is False
    assert S.practical_flag("line_oee", 0.5, -0.02) is True
    assert S.practical_flag("makespan_h", 100, 50) is None


def test_compare_holm_only_on_main_primary():
    rng = np.random.default_rng(4)
    idx = pd.Index(range(10), name="replication")

    def frame(shift):
        d = {m: rng.normal(1, 0.1, 10) + shift for m in S.METRICS}
        return pd.DataFrame(d, index=idx)

    res = {"baseline": frame(0), "a": frame(0.5), "b": frame(0.0), "c": frame(0.2)}
    meta = pd.DataFrame(
        {"name": ["a", "b", "c"], "family": ["F", "F", "G"], "exploratory": [False, False, True]}
    )
    df = S.compare(res, meta)
    holm_rows = df[df["p_holm"].notna()]
    assert set(holm_rows["scenario"]) == {"a", "b"}
    assert (holm_rows["metric"] == S.PRIMARY).all()
    assert (holm_rows["p_holm"] >= holm_rows["p"]).all()


def test_degenerate_differences_flag_bootstrap_disagreement():
    """28 of 30 differences exactly 0 plus one outlier (as with +1 mechanic): the t-CI is
    symmetric around a skewed mean, the bootstrap is not, and the disagreement is flagged."""
    base = np.full(30, 100.0)
    scen = base.copy()
    scen[4] += 120
    scen[1] += 5
    r = S.paired(base, scen)
    assert r.zero_frac == pytest.approx(28 / 30)
    assert not r.boot_agrees
    assert r.boot_low >= 0 > r.ci_low


def test_bootstrap_agreement_flag_on_well_behaved_data():
    rng = np.random.default_rng(5)
    base = rng.normal(100, 10, 30)
    r = S.paired(base, base + rng.normal(2, 1, 30))
    assert r.boot_agrees and r.zero_frac == 0
