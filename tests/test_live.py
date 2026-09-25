import numpy as np
import pandas as pd
import pytest

from regimeml.broker import AlpacaBroker
from regimeml.engine import Engine, EngineConfig, ReplaySource
from regimeml.model import ModelConfig, adaptive_intervals


def test_adaptive_intervals_fix_miscalibrated_bounds():
    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2020-01-01", periods=600)
    idx = pd.MultiIndex.from_product([dates, [f"A{i}" for i in range(20)]], names=["date", "asset"])
    y = rng.standard_normal(len(idx)) * np.repeat(np.linspace(1, 2.5, 600), 20)  # vol drifts up
    df = pd.DataFrame({"y": y, "pred": 0.0, "lo_raw": -1.28, "hi_raw": 1.28}, index=idx)
    static = ((df.y >= df.lo_raw) & (df.y <= df.hi_raw)).mean()
    cov = {}
    for lr in (0.05, 0.2):
        out = adaptive_intervals(df, alpha=0.2, horizon=5, lr=lr)
        cov[lr] = ((out.y >= out.lo) & (out.y <= out.hi)).mean()
        assert (out.hi >= out.lo).all()
    assert static < 0.6
    assert abs(cov[0.05] - 0.8) < abs(static - 0.8) / 3   # default: most of the gap closed
    assert abs(cov[0.2] - 0.8) < 0.02                    # faster tracking: on target


class FakeResp:
    def __init__(self, js): self._js, self.status_code, self.content = js, 200, b"x"
    def json(self): return self._js


class FakeSession:
    headers = {}
    def __init__(self, positions): self.positions = positions
    def request(self, method, url, timeout=None, json=None): return FakeResp(self.positions)


def test_broker_splits_position_flips(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "k"); monkeypatch.setenv("ALPACA_SECRET_KEY", "s")
    b = AlpacaBroker(session=FakeSession([{"symbol": "AAA", "qty": "10"}]))
    orders = b.plan_orders(pd.Series({"AAA": -0.5}), pd.Series({"AAA": 100.0}), capital=10_000)
    assert [(o.side, o.qty) for o in orders] == [("sell", 10), ("sell", 50)]  # close, then open short


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    d = tmp_path_factory.mktemp("state")
    src = ReplaySource(n_assets=12, n_days=1100, start=700, seed=3)
    cfg = EngineConfig(retrain_every=1000, state_dir=str(d), model=ModelConfig(max_iter=40))
    e = Engine(src, cfg)
    for _ in range(40):
        e.step()
    return e, cfg, src


def test_engine_publishes_consistent_state(engine):
    e, _, _ = engine
    _, s = e.snapshot()
    assert s["status"] in ("running", "retraining") and s["metrics"]["days"] == 39
    w = pd.Series({r["asset"]: r["weight"] for r in s["portfolio"]})
    cap = max(0.10, 2 / len(w))  # cap loosens when few names
    assert abs(w.sum()) < 1e-9 and w.abs().max() <= cap * s["leverage"] + 1e-6
    assert abs(sum(s["regime"]["current"]) - 1) < 1e-6
    assert len(s["coverage"]["dates"]) == 39 - 5 + 1  # labels mature after the 5-day horizon


def test_engine_state_survives_restart(engine):
    e, cfg, src = engine
    e2 = Engine(src, cfg)
    assert len(e2.track) == len(e.track) and e2.last_day == e.last_day
    assert e2.tracker.theta == pytest.approx(e.tracker.theta)
