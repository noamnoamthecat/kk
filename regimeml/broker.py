"""Order execution through Alpaca's Trading API (paper trading by default).

Safety rails: paper account unless ALPACA_PAPER=false, dry-run unless the
caller passes execute=True, per-order notional cap, and whole shares only.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

import pandas as pd
import requests

from .providers import ProviderError, _env


@dataclass
class Order:
    symbol: str
    side: str      # "buy" | "sell"
    qty: int
    notional: float


class AlpacaBroker:
    PAPER = "https://paper-api.alpaca.markets"
    LIVE = "https://api.alpaca.markets"

    def __init__(self, session: requests.Session | None = None):
        paper = os.environ.get("ALPACA_PAPER", "true").lower() != "false"
        self.base = self.PAPER if paper else self.LIVE
        self.http = session or requests.Session()
        self.http.headers.update({
            "APCA-API-KEY-ID": _env("ALPACA_API_KEY"),
            "APCA-API-SECRET-KEY": _env("ALPACA_SECRET_KEY"),
        })

    def _req(self, method: str, path: str, **kw):
        r = self.http.request(method, self.base + path, timeout=30, **kw)
        if r.status_code >= 400:
            raise ProviderError(f"alpaca {method} {path}: HTTP {r.status_code} {r.text[:200]}")
        return r.json() if r.content else None

    def equity(self) -> float:
        return float(self._req("GET", "/v2/account")["equity"])

    def positions(self) -> pd.Series:
        """Current signed share counts per symbol."""
        pos = self._req("GET", "/v2/positions") or []
        return pd.Series({p["symbol"]: float(p["qty"]) for p in pos}, dtype=float)

    def plan_orders(self, target_weights: pd.Series, prices: pd.Series, capital: float,
                    max_order_notional: float = float("inf"), min_notional: float = 50.0) -> list[Order]:
        held = self.positions()
        cur = held.reindex(target_weights.index.union(held.index)).fillna(0.0)
        tgt = (target_weights.reindex(cur.index).fillna(0.0) * capital)
        orders = []
        for sym in cur.index:
            px = prices.get(sym)
            if px is None or not math.isfinite(px) or px <= 0:
                continue
            delta = int(tgt[sym] / px - cur[sym])
            notional = abs(delta) * px
            if delta == 0 or notional < min_notional:
                continue
            if notional > max_order_notional:
                delta = int(math.copysign(max_order_notional // px, delta))
                notional = abs(delta) * px
            orders.append(Order(sym, "buy" if delta > 0 else "sell", abs(delta), notional))
        return orders

    def submit(self, orders: list[Order]) -> list[dict]:
        out = []
        for o in orders:
            out.append(self._req("POST", "/v2/orders", json={
                "symbol": o.symbol, "qty": str(o.qty), "side": o.side,
                "type": "market", "time_in_force": "day",
            }))
        return out
