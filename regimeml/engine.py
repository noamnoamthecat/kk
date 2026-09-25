"""Always-on engine behind the web dashboard.

It loops forever:
  * pull prices from a :class:`PriceSource` (real market or simulated replay)
  * retrain the model in a background thread on completed daily bars
  * when a new trading day closes: realise yesterday's P&L, update the
    adaptive conformal tracker with labels that just matured, and set the
    new target book
  * intraday: re-score on live prices (provisional signal) and mark the
    book to market
  * optionally rebalance through Alpaca shortly before the close

State is published as one JSON-able dict that the web server streams.
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dtime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .backtest import neutralize
from .data import SimConfig, simulate_market
from .features import build_features
from .model import ModelConfig, QuantileTracker, RegimeConformalModel, apply_interval

log = logging.getLogger("regimeml.engine")
ET = ZoneInfo("America/New_York")
REGIMES = ["calm", "stressed", "crisis"]


# --------------------------------------------------------------------------- sources

@dataclass
class Snapshot:
    completed: pd.DataFrame            # daily closes of finished sessions only
    live_prices: pd.Series | None      # latest intraday prices (None outside hours)
    market_open: bool
    now: datetime


class ReplaySource:
    """Replays a simulated market one trading day per poll (no network needed)."""
    label = "Simulated replay"
    is_live = False

    def __init__(self, n_assets: int = 30, n_days: int = 4000, start: int = 1000, seed: int = 11):
        self.data = simulate_market(SimConfig(n_assets=n_assets, n_days=n_days, seed=seed))
        self.t = start

    def poll(self) -> Snapshot:
        self.t = min(self.t + 1, len(self.data.prices))  # holds on the last day when done
        return Snapshot(self.data.prices.iloc[: self.t], None, False, datetime.now(timezone.utc))


class MarketSource:
    """Real prices from any provider in :mod:`regimeml.providers`."""
    is_live = True

    def __init__(self, provider: str, tickers: list[str], start: str = "2015-01-01",
                 history_refresh_sec: int = 900):
        from .providers import get_provider

        self.provider = get_provider(provider)
        self.label = f"Live market · {provider}"
        self.tickers, self.start, self.refresh = tickers, start, history_refresh_sec
        self._hist: pd.DataFrame | None = None
        self._fetched = 0.0

    @staticmethod
    def session_state(now_et: datetime) -> tuple[bool, bool]:
        """(market_open, today_closed) for regular US hours; holidays show as closed
        because no bar/quote for them ever arrives."""
        weekday = now_et.weekday() < 5
        t = now_et.time()
        return weekday and dtime(9, 30) <= t < dtime(16, 0), weekday and t >= dtime(16, 15)

    def poll(self) -> Snapshot:
        now = datetime.now(ET)
        market_open, closed = self.session_state(now)
        today = pd.Timestamp(now.date())
        age = time.time() - self._fetched
        stale_close = closed and self._hist is not None and self._hist.index[-1] < today and age > 120
        if self._hist is None or age > self.refresh or stale_close:
            self._hist = self.provider.get_prices(self.tickers, start=self.start)
            self._fetched = time.time()
        hist = self._hist
        # A bar for today is only "completed" after the close.
        completed = hist if closed else hist[hist.index < today]
        live = None
        if market_open:
            try:
                live = self.provider.latest_prices(list(completed.columns))
            except Exception as e:  # quotes are best-effort; the daily loop must not die
                log.warning("latest_prices failed: %s", e)
        return Snapshot(completed, live, market_open, now)


# --------------------------------------------------------------------------- engine

@dataclass
class EngineConfig:
    horizon: int = 5
    alpha: float = 0.2
    aci_lr: float = 0.05
    smoothing: float = 0.85
    max_weight: float = 0.10
    target_vol: float = 0.10
    max_leverage: float = 3.0
    cost_bps: float = 5.0
    retrain_every: int = 21            # trading days between refits
    train_lookback: int = 2520
    predict_lookback: int = 400        # history used for features + HMM filter
    poll_seconds: float = 60.0
    state_dir: str | None = None       # persist track record across restarts
    autotrade: bool = False
    autotrade_minutes_before_close: int = 10
    autotrade_max_gross: float = 1.0   # cap on gross exposure sent to the broker
    long_only: bool = False
    model: ModelConfig = field(default_factory=ModelConfig)


def _clean(x):
    """Make numpy/pandas values JSON-safe (NaN/inf -> None)."""
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not math.isfinite(float(x)) else float(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (pd.Timestamp, datetime)):
        return x.isoformat()
    return x


class Engine:
    def __init__(self, source, cfg: EngineConfig | None = None, broker=None):
        self.src, self.cfg, self.broker = source, cfg or EngineConfig(), broker
        self.cfg.model.horizon = self.cfg.horizon
        self.cfg.model.alpha = self.cfg.alpha
        self._lock = threading.Lock()
        self._train_lock = threading.Lock()
        self._stop = threading.Event()
        self.version = 0
        self.state: dict = {"status": "starting", "source": source.label, "is_live": source.is_live}
        self.events: list[dict] = []
        self.on_new_day: list = []                   # callbacks(state) after each daily close

        self.model: RegimeConformalModel | None = None
        self.model_info: dict = {}
        self.trained_through: pd.Timestamp | None = None
        self.training = False

        self.tracker = QuantileTracker(self.cfg.alpha, self.cfg.aci_lr)
        self.last_day: pd.Timestamp | None = None
        self.ewm_w: pd.Series | None = None          # unnormalised EWMA state
        self.book: pd.Series | None = None           # held weights (after leverage)
        self.pending: dict[str, dict] = {}           # date -> raw intervals awaiting labels
        self.track: list[dict] = []                  # realised daily P&L records
        self.coverage: list[dict] = []               # realised interval coverage per date
        self.traded_on: str | None = None
        self.last_turnover = 0.0                     # charged on the next realised day
        self._load()

    # -- persistence -------------------------------------------------------------
    def _path(self) -> Path | None:
        return Path(self.cfg.state_dir) / "engine_state.json" if self.cfg.state_dir else None

    def _load(self) -> None:
        p = self._path()
        if not p or not p.exists():
            return
        s = json.loads(p.read_text())
        self.track, self.coverage = s.get("track", []), s.get("coverage", [])
        self.tracker.theta = s.get("theta", 0.0)
        self.last_day = pd.Timestamp(s["last_day"]) if s.get("last_day") else None
        self.ewm_w = pd.Series(s["ewm_w"]) if s.get("ewm_w") else None
        self.book = pd.Series(s["book"]) if s.get("book") else None
        self.pending = s.get("pending", {})
        self.traded_on = s.get("traded_on")
        self.last_turnover = s.get("last_turnover", 0.0)
        self._event(f"restored {len(self.track)} days of track record")

    def _save(self) -> None:
        p = self._path()
        if not p:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(_clean({
            "track": self.track, "coverage": self.coverage, "theta": self.tracker.theta,
            "last_day": self.last_day, "ewm_w": None if self.ewm_w is None else self.ewm_w.to_dict(),
            "book": None if self.book is None else self.book.to_dict(), "pending": self.pending,
            "traded_on": self.traded_on, "last_turnover": self.last_turnover,
        })))
        tmp.replace(p)  # atomic

    def _event(self, msg: str, level: str = "info") -> None:
        log.info(msg)
        self.events = ([{"t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         "msg": msg, "level": level}] + self.events)[:30]

    # -- training (background thread) ----------------------------------------------
    def _needs_training(self, completed: pd.DataFrame) -> bool:
        if self.model is None:
            return True
        n_new = int((completed.index > self.trained_through).sum())
        return n_new >= self.cfg.retrain_every

    def _train(self, completed: pd.DataFrame) -> None:
        if not self._train_lock.acquire(blocking=False):
            return
        self.training = True
        try:
            t0 = time.time()
            prices = completed.iloc[-self.cfg.train_lookback:]
            panel = build_features(prices, horizon=self.cfg.horizon)
            train = panel[panel["y"].notna()]
            model = RegimeConformalModel(self.cfg.model).fit(train)
            with self._lock:
                self.model = model
                self.trained_through = completed.index[-1]
                self.model_info = {
                    "trained_through": str(completed.index[-1].date()),
                    "train_rows": int(len(train)), "n_features": len(model.cols_),
                    "n_assets": int(prices.shape[1]), "qhat": model.qhat_,
                    "fit_seconds": round(time.time() - t0, 1),
                    "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            self._event(f"model retrained on {len(train):,} rows in {time.time() - t0:.0f}s")
        except Exception as e:
            log.exception("training failed")
            self._event(f"training failed: {e}", "error")
        finally:
            self.training = False
            self._train_lock.release()

    # -- scoring ---------------------------------------------------------------------
    def _score(self, prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Predictions for the last date, regime history, and the feature panel."""
        panel = build_features(prices.iloc[-self.cfg.predict_lookback:], horizon=self.cfg.horizon)
        dates = panel.index.get_level_values("date")
        preds = self.model.predict(panel[dates == dates.max()], context=panel)
        preds = apply_interval(preds, self.tracker.theta).droplevel("date")
        probs = self.model.regime_probs(panel)
        return preds, probs, panel

    def _target(self, preds: pd.DataFrame, update_state: bool) -> pd.Series:
        s = preds["score"]
        if self.cfg.long_only:
            s = (s - s.median()).clip(lower=0)
            return s / s.sum() if s.sum() > 0 else s
        z = ((s - s.mean()) / (s.std() + 1e-12)).clip(-3, 3)
        w = neutralize(z.to_frame().T, self.cfg.max_weight).iloc[0]
        prev = self.ewm_w.reindex(w.index).fillna(0.0) if self.ewm_w is not None else None
        a = 1 - self.cfg.smoothing
        ewm = w if prev is None else a * w + (1 - a) * prev
        if update_state:
            self.ewm_w = ewm
        return neutralize(ewm.to_frame().T, self.cfg.max_weight).iloc[0]

    def _leverage(self) -> float:
        if self.cfg.long_only:
            return 1.0
        r = pd.Series([x["net"] for x in self.track[-60:]], dtype=float)
        if len(r) < 20 or r.std() == 0:
            return 1.0
        return float(min(self.cfg.max_leverage, self.cfg.target_vol / (r.std() * np.sqrt(252))))

    # -- daily roll ------------------------------------------------------------------
    def _new_day(self, completed: pd.DataFrame) -> None:
        day = completed.index[-1]
        # 1) realise P&L of the book held from the previous close to this one
        if self.book is not None and self.last_day is not None and self.last_day in completed.index:
            r = completed.loc[day] / completed.loc[self.last_day] - 1
            gross = float((self.book * r.reindex(self.book.index).fillna(0.0)).sum())
            cost = self.last_turnover * self.cfg.cost_bps / 1e4
            self.track.append({"date": str(day.date()), "gross": gross,
                               "turnover": self.last_turnover, "net": gross - cost})

        # 2) new predictions + mature labels for the conformal tracker
        preds, _, panel = self._score(completed)
        ys = panel["y"].dropna()
        for d in sorted(list(self.pending)):
            ts = pd.Timestamp(d)
            if ts in ys.index.get_level_values("date"):
                y = ys.xs(ts, level="date")
                p = pd.DataFrame(self.pending.pop(d))
                y = y.reindex(p.index)
                ok = y.notna()
                th = p["theta"].iloc[0]
                miss = ((y[ok] < p.loc[ok, "lo_raw"] - th) | (y[ok] > p.loc[ok, "hi_raw"] + th)).mean()
                self.tracker.update(float(miss))
                self.coverage.append({"date": d, "coverage": 1 - float(miss), "theta": self.tracker.theta})
        self.pending[str(day.date())] = {
            "lo_raw": preds["lo_raw"].to_dict(), "hi_raw": preds["hi_raw"].to_dict(),
            "theta": {k: self.tracker.theta for k in preds.index},
        }
        for d in sorted(self.pending)[:-4 * self.cfg.horizon]:  # labels that can no longer mature
            self.pending.pop(d)

        # 3) new book with vol targeting; charge costs on the turnover
        w = self._target(apply_interval(preds, self.tracker.theta), update_state=True)
        book = w * self._leverage()
        prev = self.book.reindex(book.index.union(self.book.index)).fillna(0.0) if self.book is not None else 0 * book
        self.last_turnover = float((book.reindex(prev.index).fillna(0.0) - prev).abs().sum())
        self.book, self.last_day = book, day
        self._save()

    # -- autotrade -------------------------------------------------------------------
    def _maybe_trade(self, snap: Snapshot, book: pd.Series, prices: pd.Series) -> None:
        if not (self.cfg.autotrade and self.broker is not None and snap.market_open):
            return
        today = str(snap.now.date())
        if self.traded_on == today:
            return
        clock = self.broker.clock()
        close = pd.Timestamp(clock["next_close"]).tz_convert("UTC")
        mins = (close - pd.Timestamp.now(tz="UTC")).total_seconds() / 60
        if not clock.get("is_open") or mins > self.cfg.autotrade_minutes_before_close:
            return
        capital = self.broker.equity()
        gross = float(book.abs().sum())
        if gross > self.cfg.autotrade_max_gross:
            book = book * (self.cfg.autotrade_max_gross / gross)
        orders = self.broker.plan_orders(book, prices, capital)
        res = self.broker.submit(orders)
        ok = sum(r["ok"] for r in res)
        self.traded_on = today
        self._save()
        self._event(f"rebalanced {self.broker.base}: {ok}/{len(res)} orders accepted",
                    "info" if ok == len(res) else "warn")

    # -- main loop -------------------------------------------------------------------
    def step(self) -> None:
        snap = self.src.poll()
        completed = snap.completed
        if len(completed) < 300:
            raise RuntimeError(f"need >= 300 days of history, got {len(completed)}")

        if self._needs_training(completed):
            if self.model is None:
                self._set(status="training")
                self._train(completed)          # first fit is synchronous
            elif not self.training:
                threading.Thread(target=self._train, args=(completed,), daemon=True).start()
        if self.model is None:
            return

        day = completed.index[-1]
        advanced = self.last_day is None or day > self.last_day
        if advanced:
            self._new_day(completed)

        # Current view: provisional intraday prices if the market is open.
        view = completed
        provisional = snap.live_prices is not None and len(snap.live_prices) > 0
        if provisional:
            live = snap.live_prices.reindex(completed.columns).fillna(completed.iloc[-1])
            view = pd.concat([completed, live.to_frame(pd.Timestamp(snap.now.date())).T])
        preds, probs, _ = self._score(view)
        target = self._target(apply_interval(preds, self.tracker.theta), update_state=False)
        last_px = view.iloc[-1]
        ref_px = completed.iloc[-1]
        intraday = None
        if provisional and self.book is not None:
            r = last_px / ref_px - 1
            intraday = float((self.book * r.reindex(self.book.index).fillna(0)).sum())
        self._maybe_trade(snap, target * self._leverage(), last_px)
        self._publish(snap, preds, probs, target, last_px, ref_px, provisional, intraday)
        if advanced:
            for cb in self.on_new_day:
                try:
                    cb(self.state)
                except Exception as e:  # a notifier must never stop the engine
                    log.exception("new-day callback failed")
                    self._event(f"notification failed: {e}", "error")

    def _publish(self, snap, preds, probs, target, last_px, ref_px, provisional, intraday) -> None:
        tr = pd.DataFrame(self.track)
        metrics = {"days": len(tr)}
        if len(tr):
            net = tr["net"].astype(float)
            eq = (1 + net).cumprod()
            metrics.update({
                "cum_return": float(eq.iloc[-1] - 1),
                "sharpe": float(net.mean() / net.std() * np.sqrt(252)) if len(net) > 20 and net.std() > 0 else None,
                "max_drawdown": float((eq / eq.cummax() - 1).min()),
                "hit_rate": float((net > 0).mean()),
                "last_day_pnl": float(net.iloc[-1]),
                "ann_vol": float(net.std() * np.sqrt(252)) if len(net) > 1 else None,
            })
        cov = pd.DataFrame(self.coverage)
        if len(cov):
            metrics["coverage_63d"] = float(cov["coverage"].tail(63).mean())
        lev = self._leverage()
        rows = []
        for a in preds.index:
            rows.append({
                "asset": a, "weight": float(target.get(a, 0.0)) * lev, "pred": preds.at[a, "pred"],
                "lo": preds.at[a, "lo"], "hi": preds.at[a, "hi"], "score": preds.at[a, "score"],
                "price": float(last_px.get(a, np.nan)),
                "change": float(last_px.get(a, np.nan) / ref_px.get(a, np.nan) - 1) if provisional else None,
            })
        rows.sort(key=lambda r: -r["weight"])
        ph = probs.tail(250)
        eq_dates = tr["date"].tolist() if len(tr) else []
        self._set(
            status="retraining" if self.training else "running",
            source=self.src.label, is_live=self.src.is_live,
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            as_of=str(self.last_day.date()) if self.last_day is not None else None,
            market_open=snap.market_open, provisional=provisional,
            regime={"labels": REGIMES[: probs.shape[1]], "current": probs.iloc[-1].tolist(),
                    "dates": [str(d.date()) for d in ph.index], "probs": ph.values.T.tolist()},
            portfolio=rows, leverage=lev,
            track={"dates": eq_dates, "equity": ((1 + tr["net"]).cumprod() - 1).tolist() if len(tr) else [],
                   "net": tr["net"].tolist() if len(tr) else []},
            coverage={"dates": cov["date"].tolist() if len(cov) else [],
                      "rolling": cov["coverage"].rolling(21, min_periods=5).mean().tolist() if len(cov) else [],
                      "target": 1 - self.cfg.alpha},
            metrics=metrics, intraday_pnl=intraday, theta=self.tracker.theta,
            model=self.model_info, autotrade=self.cfg.autotrade, events=self.events,
            error=None,
        )

    def _set(self, **kw) -> None:
        with self._lock:
            self.state = {**self.state, **_clean(kw)}
            self.version += 1

    def snapshot(self) -> tuple[int, dict]:
        with self._lock:
            return self.version, self.state

    def run_forever(self) -> None:
        backoff = self.cfg.poll_seconds
        while not self._stop.is_set():
            try:
                self.step()
                backoff = self.cfg.poll_seconds
            except Exception as e:
                log.exception("engine step failed")
                self._event(f"step failed: {e}", "error")
                self._set(status="error", error=str(e), events=self.events)
                backoff = min(max(backoff * 2, 5), 900)
            self._stop.wait(backoff)

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self.run_forever, daemon=True, name="regimeml-engine")
        t.start()
        return t

    def stop(self) -> None:
        self._stop.set()


def engine_from_env() -> Engine:
    """Build an engine from REGIMEML_* environment variables (see README)."""
    from .universe import LARGE_CAP_US

    mode = os.environ.get("REGIMEML_MODE", "replay").lower()
    cfg = EngineConfig(
        poll_seconds=float(os.environ.get("REGIMEML_POLL_SECONDS", "2" if mode == "replay" else "60")),
        state_dir=os.environ.get("REGIMEML_STATE_DIR", "state") if mode != "replay" else None,
        autotrade=os.environ.get("REGIMEML_AUTOTRADE", "false").lower() == "true",
        long_only=os.environ.get("REGIMEML_LONG_ONLY", "false").lower() == "true",
        retrain_every=int(os.environ.get("REGIMEML_RETRAIN_EVERY", "21" if mode == "replay" else "1")),
    )
    if mode == "replay":
        return Engine(ReplaySource(), cfg)
    provider = os.environ.get("REGIMEML_PROVIDER", "yahoo")
    tickers = os.environ.get("REGIMEML_TICKERS")
    tickers = tickers.split(",") if tickers else LARGE_CAP_US
    broker = None
    if cfg.autotrade:
        from .broker import AlpacaBroker
        broker = AlpacaBroker()
    return Engine(MarketSource(provider, tickers, os.environ.get("REGIMEML_START", "2015-01-01")), cfg, broker)
