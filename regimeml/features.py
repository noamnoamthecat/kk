"""Leak-free feature engineering on a (date x asset) price panel.

Every feature at date t uses information available at the close of t only.
Targets are forward returns over (t, t+h].
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _cs_rank(df: pd.DataFrame) -> pd.DataFrame:
    return df.rank(axis=1, pct=True) - 0.5


def _rsi(r: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    up = r.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-r.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return up / (up + dn + 1e-12) - 0.5


def market_state(returns: pd.DataFrame) -> pd.DataFrame:
    """Market-level observables used for regime detection (one row per date)."""
    mkt = returns.mean(axis=1)
    out = pd.DataFrame(index=returns.index)
    out["mkt_ret_5"] = mkt.rolling(5).sum()
    out["mkt_logvol_20"] = np.log(mkt.rolling(20).std() * np.sqrt(252) + 1e-6)
    out["dispersion_20"] = np.log(returns.std(axis=1).rolling(20).mean() + 1e-6)
    # Daily observables for the HMM: noisy alone, sharp when filtered through time.
    out["log_dispersion_1"] = np.log(returns.std(axis=1) + 1e-6)
    out["mkt_ret_1"] = mkt
    return out


def build_features(prices: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    """Return a long panel indexed by (date, asset) with features and targets.

    Columns prefixed ``f_`` are features; ``y`` is the training target
    (cross-sectionally demeaned, vol-scaled forward ``horizon``-day return);
    ``fwd_ret_1`` is the next-day raw return used for backtesting.
    """
    r = np.log(prices).diff()
    mkt = r.mean(axis=1)
    idio = r.sub(mkt, axis=0)

    vol20 = r.rolling(20).std()
    vol60 = r.rolling(60).std()
    ivol20 = idio.rolling(20).std()

    feats: dict[str, pd.DataFrame] = {}
    for n in (1, 5, 20, 60):
        feats[f"f_ret_{n}"] = r.rolling(n).sum() / (vol20 * np.sqrt(n))
        feats[f"f_idio_{n}"] = idio.rolling(n).sum() / (ivol20 * np.sqrt(n))
    feats["f_rank_idio_5"] = _cs_rank(idio.rolling(5).sum())
    feats["f_rank_idio_20"] = _cs_rank(idio.rolling(20).sum())
    feats["f_logvol_20"] = np.log(vol20 * np.sqrt(252))
    feats["f_vol_ratio"] = np.log(vol20 / vol60)
    feats["f_rank_vol"] = _cs_rank(vol20)
    logp = np.log(prices)
    feats["f_ma_gap_20"] = (logp - logp.rolling(20).mean()) / (vol20 * np.sqrt(20))
    feats["f_rsi_14"] = _rsi(r)
    feats["f_skew_60"] = r.rolling(60).skew()
    feats["f_beta_60"] = r.rolling(60).cov(mkt).div(mkt.rolling(60).var(), axis=0)

    ms = market_state(r)
    for c in ms.columns:
        feats[f"f_{c}"] = pd.DataFrame(
            np.repeat(ms[c].values[:, None], r.shape[1], axis=1), index=r.index, columns=r.columns
        )

    fwd = r.rolling(horizon).sum().shift(-horizon)
    fwd_idio = fwd.sub(fwd.mean(axis=1), axis=0)
    feats["y"] = fwd_idio / (vol20 * np.sqrt(horizon))
    feats["fwd_ret_1"] = r.shift(-1)

    panel = pd.concat({k: v.stack(future_stack=True) for k, v in feats.items()}, axis=1)
    panel.index.names = ["date", "asset"]
    feat_cols = [c for c in panel.columns if c.startswith("f_")]
    panel = panel.replace([np.inf, -np.inf], np.nan).dropna(subset=feat_cols)
    return panel


def feature_columns(panel: pd.DataFrame) -> list[str]:
    return [c for c in panel.columns if c.startswith("f_")]
