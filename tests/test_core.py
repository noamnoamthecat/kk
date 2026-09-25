import numpy as np
import pandas as pd
import pytest

from regimeml.backtest import deflated_sharpe, probabilistic_sharpe, run_backtest
from regimeml.cv import PurgedWalkForward
from regimeml.data import SimConfig, simulate_market
from regimeml.features import build_features
from regimeml.model import ModelConfig, walk_forward_predict
from regimeml.regimes import GaussianHMM


@pytest.fixture(scope="module")
def small():
    return simulate_market(SimConfig(n_assets=15, n_days=1100, seed=1))


def test_features_have_no_lookahead(small):
    p1 = build_features(small.prices)
    shocked = small.prices.copy()
    shocked.iloc[800:] *= 1.5  # change the future only
    p2 = build_features(shocked)
    cols = [c for c in p1.columns if c.startswith("f_")]
    cutoff = small.prices.index[798]
    a = p1.loc[p1.index.get_level_values("date") <= cutoff, cols]
    b = p2.loc[p2.index.get_level_values("date") <= cutoff, cols]
    pd.testing.assert_frame_equal(a, b)


def test_purged_splits_do_not_overlap_labels():
    dates = pd.bdate_range("2020-01-01", periods=1000)
    cv = PurgedWalkForward(horizon=5, min_train_days=300, test_days=100, embargo_days=5)
    folds = list(cv.split(dates))
    assert len(folds) == 7
    for tr, te in folds:
        gap = dates.get_loc(te[0]) - dates.get_loc(tr[-1])
        assert gap > 5  # last training label window ends before the test block


def test_hmm_filter_is_causal_and_recovers_states():
    rng = np.random.default_rng(0)
    states = np.repeat([0, 1, 0, 2, 0, 1], 250)
    # Feature 0 ~ log dispersion (level shifts), feature 1 ~ return (vol shifts).
    disp = np.array([-1.0, 0.0, 1.2])[states] + 0.4 * rng.standard_normal(len(states))
    ret = np.array([0.5, 1.0, 3.0])[states] * rng.standard_normal(len(states))
    X = np.column_stack([disp, ret])
    hmm = GaussianHMM(3, seed=0).fit(X)
    p = hmm.filter(X)
    assert np.allclose(p.sum(1), 1)
    assert (p.argmax(1) == states).mean() > 0.8
    # causality: filtered probs up to t unchanged when future data changes
    X2 = X.copy()
    X2[1000:] *= 5
    assert np.allclose(hmm.filter(X2)[:1000], p[:1000])


def test_walk_forward_conformal_coverage_and_signal(small):
    panel = build_features(small.prices)
    cv = PurgedWalkForward(horizon=5, min_train_days=600, test_days=200, embargo_days=5)
    cfg = ModelConfig(max_iter=60, alpha=0.2)
    preds = walk_forward_predict(panel, cv, cfg)
    d = preds.dropna(subset=["y"])
    coverage = ((d.y >= d.lo) & (d.y <= d.hi)).mean()
    assert 0.7 < coverage < 0.9
    bt = run_backtest(preds)
    assert np.isfinite(bt["net"]).all() and len(bt) > 300


def test_deflated_sharpe_penalises_many_trials():
    r = pd.Series(np.random.default_rng(3).normal(0.0005, 0.01, 1000))
    assert deflated_sharpe(r, 100) < probabilistic_sharpe(r)


def test_live_target_portfolio(small):
    from regimeml.live import target_portfolio

    w, info = target_portfolio(small.prices, long_only=False)
    assert abs(w.sum()) < 1e-9 and abs(w.abs().sum() - 1) < 1e-9  # dollar neutral, gross 1
    assert abs(sum(info["regime_probs"].values()) - 1) < 1e-2
    w_lo, _ = target_portfolio(small.prices, long_only=True, gross=0.5)
    assert (w_lo >= 0).all() and abs(w_lo.sum() - 0.5) < 1e-9
