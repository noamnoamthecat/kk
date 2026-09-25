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

    def clock(self) -> dict:
        """Market clock: {'is_open': bool, 'next_open': iso, 'next_close': iso, 'timestamp': iso}."""
        return self._req("GET", "/v2/clock")

    def plan_orders(self, target_weights: pd.Series, prices: pd.Series, capital: float,
                    max_order_notional: float = float("inf"), min_notional: float = 50.0) -> list[Order]:
        """Orders that move current holdings to ``target_weights * capital``.

        A trade that crosses zero (long -> short or short -> long) is split into
        a closing order and an opening order: brokers reject a single order
        that reverses a position.
        """
        held = self.positions()
        cur = held.reindex(target_weights.index.union(held.index)).fillna(0.0)
        tgt = target_weights.reindex(cur.index).fillna(0.0) * capital
        orders = []
        for sym in cur.index:
            px = prices.get(sym)
            if px is None or not math.isfinite(px) or px <= 0:
                continue
            now, want = int(cur[sym]), int(tgt[sym] / px)  # whole shares, toward zero
            legs = [(now, 0), (0, want)] if now * want < 0 else [(now, want)]
            for a, b in legs:
                delta = b - a
                if delta == 0 or abs(delta) * px < min_notional:
                    continue
                if abs(delta) * px > max_order_notional:
                    delta = int(math.copysign(max_order_notional // px, delta))
                    if delta == 0:
                        continue
                orders.append(Order(sym, "buy" if delta > 0 else "sell", abs(delta), abs(delta) * px))
        return orders

    def submit(self, orders: list[Order]) -> list[dict]:
        """Submit each order; a rejected order is reported, not fatal to the batch."""
        out = []
        for o in orders:
            try:
                r = self._req("POST", "/v2/orders", json={
                    "symbol": o.symbol, "qty": str(o.qty), "side": o.side,
                    "type": "market", "time_in_force": "day",
                })
                out.append({"symbol": o.symbol, "ok": True, "id": (r or {}).get("id")})
            except ProviderError as e:
                out.append({"symbol": o.symbol, "ok": False, "error": str(e)})
        return out
