"""Market data: a regime-switching simulator with planted ground-truth alpha,
plus loaders for real prices (CSV or Yahoo Finance).

The simulator exists so the whole pipeline can be *validated*: we know the
true regimes and the true (weak, regime-dependent) predictability, so we can
check that the model recovers them instead of fitting noise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

REGIME_NAMES = ("calm", "stressed", "crisis")


@dataclass
class SimConfig:
    n_assets: int = 40
    n_days: int = 3000
    seed: int = 7
    # Daily market drift / vol per regime (calm, stressed, crisis).
    mkt_mu: tuple = (0.0006, -0.0003, -0.0020)
    mkt_vol: tuple = (0.007, 0.014, 0.030)
    # Multiplier on idiosyncratic vol per regime.
    idio_vol_mult: tuple = (1.0, 1.4, 2.2)
    # Row-stochastic regime transition matrix (persistent regimes).
    transition: np.ndarray = field(
        default_factory=lambda: np.array(
            [[0.990, 0.009, 0.001],
             [0.020, 0.965, 0.015],
             [0.010, 0.050, 0.940]]
        )
    )
    # Planted alpha strength: daily IC of the true signal.
    alpha_ic: float = 0.035


@dataclass
class MarketData:
    prices: pd.DataFrame          # dates x assets, adjusted close
    true_regime: pd.Series | None = None
    true_signal: pd.DataFrame | None = None

    @property
    def returns(self) -> pd.DataFrame:
        return np.log(self.prices).diff()


def simulate_market(cfg: SimConfig | None = None) -> MarketData:
    """Simulate a panel of assets driven by a hidden 3-state Markov regime.

    Ground-truth predictability (weak, like real markets):
      * calm regime     -> short-term (5d) idiosyncratic *reversal*
      * stressed/crisis -> medium-term (20d) idiosyncratic *momentum*
    A regime-blind model sees these two effects partially cancel.
    """
    cfg = cfg or SimConfig()
    rng = np.random.default_rng(cfg.seed)
    T, N = cfg.n_days, cfg.n_assets

    regime = np.zeros(T, dtype=int)
    for t in range(1, T):
        regime[t] = rng.choice(3, p=cfg.transition[regime[t - 1]])

    beta = rng.uniform(0.6, 1.4, N)
    idio_sigma = rng.uniform(0.008, 0.02, N)
    mu = np.asarray(cfg.mkt_mu)[regime]
    sig = np.asarray(cfg.mkt_vol)[regime]
    mkt = mu + sig * rng.standard_t(df=5, size=T) / np.sqrt(5 / 3)

    idio = np.zeros((T, N))
    signal = np.zeros((T, N))
    for t in range(T):
        s_idio = idio_sigma * cfg.idio_vol_mult[regime[t]]
        if t >= 20:
            if regime[t - 1] == 0:
                raw = -idio[t - 5:t].sum(0) / (idio_sigma * np.sqrt(5))
            else:
                raw = idio[t - 20:t].sum(0) / (idio_sigma * np.sqrt(20))
            raw = (raw - raw.mean()) / (raw.std() + 1e-12)
            signal[t] = raw
        noise = rng.standard_t(df=4, size=N) / np.sqrt(2)
        idio[t] = s_idio * (cfg.alpha_ic * signal[t] + np.sqrt(1 - cfg.alpha_ic**2) * noise)

    rets = beta[None, :] * mkt[:, None] + idio
    dates = pd.bdate_range("2012-01-02", periods=T)
    assets = [f"A{i:03d}" for i in range(N)]
    prices = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)), index=dates, columns=assets)
    return MarketData(
        prices=prices,
        true_regime=pd.Series(regime, index=dates, name="regime"),
        true_signal=pd.DataFrame(signal, index=dates, columns=assets),
    )


def load_csv(path: str) -> MarketData:
    """Load a wide CSV: first column = date, remaining columns = adjusted closes."""
    df = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
    return MarketData(prices=df.dropna(axis=1, how="all").ffill().dropna())


def load_yahoo(tickers: list[str], start: str = "2010-01-01") -> MarketData:
    """Download adjusted closes via yfinance (optional dependency, needs network)."""
    import yfinance as yf

    df = yf.download(tickers, start=start, auto_adjust=True, progress=False)["Close"]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0])
    df = df.dropna(axis=1, how="all").ffill().dropna()
    if df.empty:
        raise RuntimeError("No data downloaded (network blocked or bad tickers).")
    return MarketData(prices=df)
