"""End-to-end experiment: features -> purged walk-forward -> backtest -> report."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import BacktestConfig, run_backtest, summarize
from .cv import PurgedWalkForward
from .data import REGIME_NAMES, MarketData, SimConfig, load_csv, load_yahoo, simulate_market
from .features import build_features
from .model import ModelConfig, walk_forward_predict

VARIANTS = {
    # name: (model config overrides, signal column)
    "regime_conformal": ({"use_regimes": True}, "score"),
    "regime_point": ({"use_regimes": True}, "pred"),
    "blind_point": ({"use_regimes": False}, "pred"),
}


def run(data: MarketData, horizon: int = 5, out_dir: str = "reports", verbose: bool = True,
        test_days: int = 252, min_train_days: int = 750) -> dict:
    t0 = time.time()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    panel = build_features(data.prices, horizon=horizon)
    splitter = PurgedWalkForward(horizon=horizon, min_train_days=min_train_days,
                                 test_days=test_days, embargo_days=horizon)
    if verbose:
        n_dates = panel.index.get_level_values("date").nunique()
        print(f"panel: {len(panel):,} rows, {n_dates} dates, {data.prices.shape[1]} assets")

    cache: dict[bool, pd.DataFrame] = {}
    results, backtests = {}, {}
    for name, (overrides, signal) in VARIANTS.items():
        cfg = ModelConfig(horizon=horizon, **overrides)
        if cfg.use_regimes not in cache:
            if verbose:
                print(f"walk-forward ({'regime-aware' if cfg.use_regimes else 'regime-blind'}):")
            cache[cfg.use_regimes] = walk_forward_predict(panel, splitter, cfg, verbose=verbose)
        preds = cache[cfg.use_regimes]
        bt = run_backtest(preds, BacktestConfig(signal=signal))
        backtests[name] = bt
        results[name] = summarize(bt, preds, n_trials=len(VARIANTS))

    preds = cache[True]
    if data.true_signal is not None:
        oracle = preds[["fwd_ret_1", "y", "lo", "hi"]].copy()
        oracle["pred"] = data.true_signal.stack().reindex(oracle.index).values
        bt = run_backtest(oracle, BacktestConfig(signal="pred"))
        backtests["oracle_true_signal"] = bt
        results["oracle_true_signal"] = summarize(bt, oracle, n_trials=1)

    regime_report = None
    rcols = [c for c in preds.columns if c.startswith("f_regime_")]
    probs = preds[rcols].groupby(level="date").first()
    if data.true_regime is not None:
        truth = data.true_regime.reindex(probs.index)
        guess = probs.values.argmax(1)
        regime_report = {
            "filtered_accuracy": float((guess == truth.values).mean()),
            "confusion": pd.crosstab(truth.map(dict(enumerate(REGIME_NAMES))),
                                     pd.Series(guess, index=probs.index, name="hmm_state")).to_dict(),
        }

    summary = {"metrics": results, "regimes": regime_report, "horizon": horizon,
               "runtime_sec": round(time.time() - t0, 1)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    _plot(data, backtests, preds, probs, out)
    if verbose:
        print_report(summary)
        print(f"\nartifacts written to {out.resolve()}")
    return summary


def print_report(summary: dict) -> None:
    df = pd.DataFrame(summary["metrics"]).T
    cols = ["sharpe_net", "sharpe_gross", "ann_return", "max_drawdown", "mean_ic", "ic_tstat",
            "interval_coverage", "deflated_sharpe", "avg_daily_turnover"]
    with pd.option_context("display.float_format", "{:,.3f}".format, "display.width", 160):
        print("\n=== out-of-sample results (net of costs) ===")
        print(df[cols])
    if summary["regimes"]:
        print(f"\nHMM filtered regime accuracy vs ground truth: {summary['regimes']['filtered_accuracy']:.1%}")


def _plot(data, backtests, preds, probs, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(12, 11), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.3, 1.3]})
    ax = axes[0]
    colors = {"regime_conformal": "#2a6fdb", "regime_point": "#7fa7ea",
              "blind_point": "#e07b39", "oracle_true_signal": "#999999"}
    for name, bt in backtests.items():
        ls = "--" if name.startswith("oracle") else "-"
        ax.plot(bt["net"].cumsum(), label=name, color=colors.get(name), ls=ls, lw=1.6)
    ax.set_title("Out-of-sample cumulative log return, net of 5bp costs (10% vol target)")
    ax.legend(loc="upper left", frameon=False)
    ax.grid(alpha=0.3)

    ax = axes[1]
    ax.stackplot(probs.index, probs.T.values, labels=REGIME_NAMES[: probs.shape[1]],
                 colors=["#8cc084", "#f2c14e", "#d1495b"], alpha=0.85)
    ax.set_ylabel("P(regime)\nfiltered")
    ax.legend(loc="upper left", ncol=3, frameon=False, fontsize=8)
    if data.true_regime is not None:
        tr = data.true_regime.reindex(probs.index)
        ax.plot(tr.index, 1.02 + 0 * tr, alpha=0)  # keep limits
        for k, c in enumerate(["#8cc084", "#f2c14e", "#d1495b"]):
            m = tr == k
            ax.scatter(tr.index[m], np.full(m.sum(), 1.05), s=2, color=c, marker="|")
        ax.set_ylim(0, 1.1)

    ax = axes[2]
    d = preds.dropna(subset=["y"])
    cov = ((d["y"] >= d["lo"]) & (d["y"] <= d["hi"])).groupby(level="date").mean()
    ax.plot(cov.rolling(21).mean(), color="#2a6fdb")
    ax.axhline(0.8, color="k", ls=":", lw=1)
    ax.set_ylabel("conformal\ncoverage (21d)")
    ax.set_ylim(0.5, 1.0)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "dashboard.png", dpi=130)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Regime-aware conformal ML trading research pipeline")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--csv", help="wide CSV of adjusted closes (date index, one column per asset)")
    src.add_argument("--tickers", nargs="+", help="download from Yahoo Finance (needs network)")
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--assets", type=int, default=40, help="simulated assets")
    ap.add_argument("--days", type=int, default=3000, help="simulated days")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--out", default="reports")
    a = ap.parse_args(argv)
    if a.csv:
        data = load_csv(a.csv)
    elif a.tickers:
        data = load_yahoo(a.tickers, a.start)
    else:
        data = simulate_market(SimConfig(n_assets=a.assets, n_days=a.days, seed=a.seed))
    run(data, horizon=a.horizon, out_dir=a.out)


if __name__ == "__main__":
    main()
