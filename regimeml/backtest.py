"""Portfolio construction, cost-aware backtest and honest performance stats."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class BacktestConfig:
    signal: str = "score"          # column of predictions used to rank
    cost_bps: float = 5.0          # one-way cost per unit turnover
    target_vol: float = 0.10       # annualised
    vol_lookback: int = 60
    max_leverage: float = 3.0
    smoothing: float = 0.85        # EWMA on weights to cut turnover (0 = none)


def signal_to_weights(preds: pd.DataFrame, signal: str, smoothing: float = 0.0) -> pd.DataFrame:
    """Dollar-neutral weights, gross exposure 1, from cross-sectional z-scores."""
    s = preds[signal].unstack("asset")
    z = s.sub(s.mean(axis=1), axis=0).div(s.std(axis=1) + 1e-12, axis=0).clip(-3, 3)
    w = z.div(z.abs().sum(axis=1), axis=0).fillna(0.0)
    if smoothing > 0:
        w = w.ewm(alpha=1 - smoothing, adjust=False).mean()
        w = w.div(w.abs().sum(axis=1), axis=0).fillna(0.0)
    return w


def run_backtest(preds: pd.DataFrame, cfg: BacktestConfig | None = None) -> pd.DataFrame:
    """Weights decided at close t earn fwd_ret_1 (t -> t+1). Vol targeting uses
    only strategy returns realised up to t (lagged), so it is causal."""
    cfg = cfg or BacktestConfig()
    w = signal_to_weights(preds, cfg.signal, cfg.smoothing)
    r = preds["fwd_ret_1"].unstack("asset").reindex_like(w).fillna(0.0)
    raw = (w * r).sum(axis=1)
    realised = raw.shift(1)  # return of the book held from t-1 to t, known at t
    vol = realised.rolling(cfg.vol_lookback, min_periods=20).std() * np.sqrt(252)
    lev = (cfg.target_vol / vol).clip(upper=cfg.max_leverage).fillna(1.0)
    pos = w.mul(lev, axis=0)
    turnover = pos.diff().abs().sum(axis=1).fillna(pos.abs().sum(axis=1))
    gross = (pos * r).sum(axis=1)
    net = gross - turnover * cfg.cost_bps / 1e4
    return pd.DataFrame({"gross": gross, "net": net, "turnover": turnover, "leverage": lev})


# -- metrics -----------------------------------------------------------------

def sharpe(r: pd.Series) -> float:
    return float(r.mean() / (r.std() + 1e-12) * np.sqrt(252))


def max_drawdown(r: pd.Series) -> float:
    eq = r.cumsum()
    return float((eq - eq.cummax()).min())


def probabilistic_sharpe(r: pd.Series, sr_benchmark: float = 0.0) -> float:
    """P(true Sharpe > benchmark) accounting for skew/kurtosis (Bailey & Lopez de Prado)."""
    sr = r.mean() / r.std()
    n, g3, g4 = len(r), stats.skew(r), stats.kurtosis(r, fisher=False)
    denom = np.sqrt((1 - g3 * sr + (g4 - 1) / 4 * sr**2) / (n - 1))
    return float(stats.norm.cdf((sr - sr_benchmark) / denom))


def deflated_sharpe(r: pd.Series, n_trials: int, trial_sr_var: float | None = None) -> float:
    """PSR against the max Sharpe expected from ``n_trials`` pure-noise strategies."""
    if n_trials <= 1:
        return probabilistic_sharpe(r)
    var = trial_sr_var if trial_sr_var is not None else 1.0 / (len(r) - 1)
    em = 0.5772156649
    z = (1 - em) * stats.norm.ppf(1 - 1 / n_trials) + em * stats.norm.ppf(1 - 1 / (n_trials * np.e))
    return probabilistic_sharpe(r, np.sqrt(var) * z)


def information_coefficient(preds: pd.DataFrame, col: str = "pred", target: str = "y") -> pd.Series:
    """Daily cross-sectional Spearman rank correlation of prediction vs outcome."""
    d = preds.dropna(subset=[target])
    return d.groupby(level="date").apply(lambda g: g[col].corr(g[target], method="spearman"))


def summarize(bt: pd.DataFrame, preds: pd.DataFrame, n_trials: int = 1) -> dict:
    r = bt["net"]
    ic = information_coefficient(preds)
    covered = preds.dropna(subset=["y"])
    cov = ((covered["y"] >= covered["lo"]) & (covered["y"] <= covered["hi"])).mean()
    return {
        "ann_return": float(r.mean() * 252),
        "ann_vol": float(r.std() * np.sqrt(252)),
        "sharpe_net": sharpe(r),
        "sharpe_gross": sharpe(bt["gross"]),
        "sortino": float(r.mean() / (r[r < 0].std() + 1e-12) * np.sqrt(252)),
        "max_drawdown": max_drawdown(r),
        "hit_rate": float((r > 0).mean()),
        "avg_daily_turnover": float(bt["turnover"].mean()),
        "mean_ic": float(ic.mean()),
        "ic_tstat": float(ic.mean() / (ic.std() + 1e-12) * np.sqrt(ic.count())),
        "interval_coverage": float(cov),
        "prob_sharpe": probabilistic_sharpe(r),
        "deflated_sharpe": deflated_sharpe(r, n_trials),
    }
