"""Production entry point: real data -> fresh model -> today's target book.

    python -m regimeml.live --provider alpaca              # dry run, prints the plan
    python -m regimeml.live --provider alpaca --execute    # sends orders (paper by default)

Designed to run once a day after the close (cron, GitHub Actions, k8s CronJob).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .backtest import signal_to_weights
from .features import build_features
from .model import ModelConfig, RegimeConformalModel
from .providers import get_provider
from .universe import LARGE_CAP_US

REGIME_LABELS = ["calm", "stressed", "crisis"]


def target_portfolio(prices: pd.DataFrame, horizon: int = 5, long_only: bool = False,
                     gross: float = 1.0, lookback_days: int = 2520) -> tuple[pd.Series, dict]:
    """Fit on all labelled history, score the latest date, return weights."""
    prices = prices.iloc[-lookback_days:]
    panel = build_features(prices, horizon=horizon)
    dates = panel.index.get_level_values("date")
    last = dates.max()
    model = RegimeConformalModel(ModelConfig(horizon=horizon)).fit(panel[panel["y"].notna()])
    preds = model.predict(panel[dates == last], context=panel)

    if long_only:
        s = preds["score"].droplevel("date")
        s = (s - s.median()).clip(lower=0)
        w = s / s.sum() if s.sum() > 0 else s
    else:
        w = signal_to_weights(preds, "score").iloc[-1]
    w = (w * gross).rename("weight")

    regime = preds[[c for c in preds.columns if c.startswith("f_regime_")]].iloc[0]
    info = {
        "as_of": str(last.date()),
        "n_assets": int(prices.shape[1]),
        "regime_probs": {REGIME_LABELS[i]: round(float(p), 3) for i, p in enumerate(regime.values)},
        "conformal_qhat": model.qhat_,
    }
    return w, info


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", default="yahoo",
                    help="yahoo|stooq|alpaca|polygon|tiingo|fmp|alphavantage|twelvedata|eodhd|bloomberg")
    ap.add_argument("--tickers", nargs="+", default=LARGE_CAP_US)
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--long-only", action="store_true", help="no shorting (cash accounts)")
    ap.add_argument("--gross", type=float, default=1.0, help="gross exposure as fraction of capital")
    ap.add_argument("--capital", type=float, help="capital to allocate (default: broker equity)")
    ap.add_argument("--max-order", type=float, default=25_000, help="per-order notional cap")
    ap.add_argument("--execute", action="store_true", help="actually submit orders to Alpaca")
    ap.add_argument("--out", default="signals")
    a = ap.parse_args(argv)

    prices = get_provider(a.provider).get_prices(a.tickers, start=a.start)
    print(f"[{a.provider}] {prices.shape[1]} tickers, {len(prices)} days, last = {prices.index[-1].date()}")
    w, info = target_portfolio(prices, a.horizon, a.long_only, a.gross)
    print(json.dumps(info, indent=2))
    print(w[w.abs() > 1e-4].sort_values().to_string(float_format="{:+.2%}".format))

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    w.to_csv(out / f"weights_{info['as_of']}.csv")
    (out / f"run_{stamp}.json").write_text(json.dumps({**info, "weights": w.round(6).to_dict()}, indent=2))

    if a.execute or a.capital is not None:
        from .broker import AlpacaBroker

        broker = AlpacaBroker()
        capital = a.capital if a.capital is not None else broker.equity()
        orders = broker.plan_orders(w, prices.iloc[-1], capital, max_order_notional=a.max_order)
        print(f"\n{len(orders)} orders for capital ${capital:,.0f} ({broker.base}):")
        for o in orders:
            print(f"  {o.side:4s} {o.qty:6d} {o.symbol:6s} ~${o.notional:,.0f}")
        if a.execute:
            results = broker.submit(orders)
            bad = [r for r in results if not r["ok"]]
            print(f"submitted {len(results) - len(bad)}/{len(results)} orders.")
            for r in bad:
                print(f"  REJECTED {r['symbol']}: {r['error']}")
        else:
            print("dry run -- pass --execute to send.")


if __name__ == "__main__":
    main()
