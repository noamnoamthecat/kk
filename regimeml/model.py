"""Regime-aware ensemble with conformalized quantile regression (CQR).

Per fold:
  1. Fit a Gaussian HMM on market-state features of the training window and
     append *filtered* regime probabilities as features (causal).
  2. Fit a gradient-boosted point model plus a ridge model (ensemble).
  3. Fit lower/upper quantile boosters, then conformalize them on a
     time-ordered, purged calibration slice so intervals have finite-sample
     coverage guarantees (Romano, Patterson & Candes, 2019).
The trading signal is the predicted return divided by the conformal
interval width: bet big only when the model is both bullish *and* sure.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import feature_columns
from .regimes import GaussianHMM

HMM_COLS = ["f_log_dispersion_1", "f_mkt_ret_1"]


@dataclass
class ModelConfig:
    use_regimes: bool = True
    n_regimes: int = 3
    alpha: float = 0.2            # 1 - target interval coverage
    calib_frac: float = 0.2
    horizon: int = 5
    learning_rate: float = 0.05
    max_iter: int = 200
    max_leaf_nodes: int = 15
    min_samples_leaf: int = 200
    l2: float = 1.0
    ridge_weight: float = 0.3
    aci_lr: float = 0.05          # online conformal step size (0 = static intervals)
    seed: int = 0


def _gbm(cfg: ModelConfig, **kw) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        learning_rate=cfg.learning_rate, max_iter=cfg.max_iter, max_leaf_nodes=cfg.max_leaf_nodes,
        min_samples_leaf=cfg.min_samples_leaf, l2_regularization=cfg.l2,
        early_stopping=False, random_state=cfg.seed, **kw,
    )


class RegimeConformalModel:
    def __init__(self, cfg: ModelConfig | None = None):
        self.cfg = cfg or ModelConfig()

    # -- regimes ------------------------------------------------------------
    def _market_obs(self, panel: pd.DataFrame) -> pd.DataFrame:
        return panel[HMM_COLS].groupby(level="date").first()

    def fit_regimes(self, train_panel: pd.DataFrame) -> None:
        obs = self._market_obs(train_panel)
        self.hmm_mu_, self.hmm_sd_ = obs.mean(), obs.std()
        self.hmm_ = GaussianHMM(self.cfg.n_regimes, seed=self.cfg.seed).fit(
            ((obs - self.hmm_mu_) / self.hmm_sd_).values
        )

    def regime_probs(self, panel: pd.DataFrame) -> pd.DataFrame:
        obs = self._market_obs(panel)
        p = self.hmm_.filter(((obs - self.hmm_mu_) / self.hmm_sd_).values)
        return pd.DataFrame(p, index=obs.index, columns=[f"f_regime_{k}" for k in range(p.shape[1])])

    def _with_regimes(self, panel: pd.DataFrame, probs: pd.DataFrame) -> pd.DataFrame:
        out = panel.join(probs, on="date")
        # Interactions let the linear model flip signs by regime, too.
        for k in range(1, self.cfg.n_regimes):
            for c in ("f_idio_5", "f_idio_20"):
                out[f"{c}_x_r{k}"] = out[c] * out[f"f_regime_{k}"]
        return out

    # -- fit / predict ----------------------------------------------------------
    def fit(self, train: pd.DataFrame, context: pd.DataFrame | None = None) -> "RegimeConformalModel":
        """``context`` = all rows up to the end of the prediction period, used
        only to run the causal HMM filter forward (features, never labels)."""
        cfg = self.cfg
        train = train.dropna(subset=["y"])
        if cfg.use_regimes:
            self.fit_regimes(train)
            train = self._with_regimes(train, self.regime_probs(train))
        self.cols_ = feature_columns(train)

        dates = train.index.get_level_values("date").unique()
        cut = dates[int(len(dates) * (1 - cfg.calib_frac))]
        purge = dates[max(0, dates.get_loc(cut) - cfg.horizon)]
        d = train.index.get_level_values("date")
        proper, calib = train[d < purge], train[d >= cut]

        X, y = proper[self.cols_].values, proper["y"].clip(-5, 5).values
        self.gbm_ = _gbm(cfg).fit(X, y)
        self.ridge_ = make_pipeline(StandardScaler(), Ridge(alpha=10.0)).fit(X, y)
        self.q_lo_ = _gbm(cfg, loss="quantile", quantile=cfg.alpha / 2).fit(X, y)
        self.q_hi_ = _gbm(cfg, loss="quantile", quantile=1 - cfg.alpha / 2).fit(X, y)

        Xc, yc = calib[self.cols_].values, calib["y"].values
        lo, hi = self.q_lo_.predict(Xc), self.q_hi_.predict(Xc)
        scores = np.maximum(lo - yc, yc - hi)
        n = len(scores)
        q = min(1.0, np.ceil((n + 1) * (1 - cfg.alpha)) / n)
        self.qhat_ = float(np.quantile(scores, q, method="higher"))
        return self

    def predict(self, test: pd.DataFrame, context: pd.DataFrame | None = None) -> pd.DataFrame:
        cfg = self.cfg
        if cfg.use_regimes:
            ctx = context if context is not None else test
            probs = self.regime_probs(ctx)
            test = self._with_regimes(test, probs)
        X = test[self.cols_].values
        w = cfg.ridge_weight
        mean = (1 - w) * self.gbm_.predict(X) + w * self.ridge_.predict(X)
        lo = self.q_lo_.predict(X) - self.qhat_
        hi = self.q_hi_.predict(X) + self.qhat_
        # Guard against quantile crossing, then compute interval/score columns.
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
        out = pd.DataFrame({"pred": mean, "lo_raw": lo, "hi_raw": hi}, index=test.index)
        out = apply_interval(out, 0.0)
        if cfg.use_regimes:
            out = out.join(test[[c for c in test.columns if c.startswith("f_regime_")]])
        return out


class QuantileTracker:
    """Online conformal quantile tracking (Angelopoulos, Candes & Tibshirani, 2023).

    Widens every interval by ``theta`` and nudges ``theta`` after each realised
    outcome: up when coverage fell short of 1 - alpha, down when it overshot.
    That keeps long-run coverage on target even when the market drifts away
    from the calibration period, which static split-conformal cannot promise.
    """

    def __init__(self, alpha: float, lr: float = 0.05, theta: float = 0.0,
                 min_theta: float = -np.inf):
        self.alpha, self.lr, self.theta, self.min_theta = alpha, lr, theta, min_theta

    def update(self, miss_rate: float) -> float:
        if np.isfinite(miss_rate):
            self.theta = max(self.min_theta, self.theta + self.lr * (miss_rate - self.alpha))
        return self.theta


def apply_interval(out: pd.DataFrame, theta) -> pd.DataFrame:
    """Recompute lo/hi/width/score after widening raw CQR bounds by ``theta``."""
    lo, hi = out["lo_raw"] - theta, out["hi_raw"] + theta
    mid = (out["lo_raw"] + out["hi_raw"]) / 2
    out["lo"], out["hi"] = np.minimum(lo, mid), np.maximum(hi, mid)  # never cross
    out["width"] = (out["hi"] - out["lo"]).clip(lower=1e-6)
    out["score"] = out["pred"] / out["width"]
    return out


def adaptive_intervals(preds: pd.DataFrame, alpha: float, horizon: int, lr: float) -> pd.DataFrame:
    """Sequentially apply quantile tracking to walk-forward predictions.

    The label of date t is only known at the close of t + horizon, so the
    update for date t is applied before predicting date t + horizon -- causal.
    """
    d = preds.index.get_level_values("date")
    dates = d.unique().sort_values()
    # Bound how far intervals may shrink when the model has been over-covering.
    tracker = QuantileTracker(alpha, lr, min_theta=-0.25 * float((preds["hi_raw"] - preds["lo_raw"]).median()))
    labelled = preds.dropna(subset=["y"])
    groups = {k: (g["y"].values, g["lo_raw"].values, g["hi_raw"].values)
              for k, g in labelled.groupby(level="date")}
    thetas = np.zeros(len(dates))
    for i in range(len(dates)):
        j = i - horizon
        if j >= 0 and dates[j] in groups:
            y, lo, hi = groups[dates[j]]
            th = thetas[j]
            tracker.update(float(((y < lo - th) | (y > hi + th)).mean()))
        thetas[i] = tracker.theta
    thetas = pd.Series(thetas, index=dates)
    out = preds.copy()
    out["theta"] = thetas.reindex(d).values
    return apply_interval(out, out["theta"])


def walk_forward_predict(panel: pd.DataFrame, splitter, cfg: ModelConfig, verbose: bool = False) -> pd.DataFrame:
    """Train on each purged training window, predict the following test block."""
    dates = panel.index.get_level_values("date")
    preds = []
    for i, (tr, te) in enumerate(splitter.split(dates)):
        train = panel[dates.isin(tr)]
        test = panel[dates.isin(te)]
        context = panel[dates <= te[-1]]
        m = RegimeConformalModel(cfg).fit(train)
        preds.append(m.predict(test, context=context))
        if verbose:
            print(f"  fold {i + 1:2d}: train {tr[0].date()}..{tr[-1].date()} "
                  f"({len(train):,} rows) -> test {te[0].date()}..{te[-1].date()}")
    out = pd.concat(preds).join(panel[["y", "fwd_ret_1"]])
    if cfg.aci_lr > 0:
        out = adaptive_intervals(out, cfg.alpha, cfg.horizon, cfg.aci_lr)
    return out
