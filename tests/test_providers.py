"""Connector tests against canned API responses (no network needed)."""
import json

import pandas as pd
import pytest

from regimeml import providers as P
from regimeml.broker import AlpacaBroker


class FakeResp:
    def __init__(self, payload, status=200):
        self.status_code = status
        self._p = payload
        self.text = payload if isinstance(payload, str) else json.dumps(payload)
        self.content = self.text.encode()

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self, router):
        self.router, self.headers, self.calls = router, {}, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.router(url, params or {})

    def request(self, method, url, timeout=None, json=None):
        self.calls.append((method, url, json))
        return self.router(url, json or {})


DATES = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2024-01-01", periods=5)]


@pytest.fixture(autouse=True)
def keys(monkeypatch):
    for k in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY", "POLYGON_API_KEY", "TIINGO_API_KEY",
              "FMP_API_KEY", "ALPHAVANTAGE_API_KEY", "TWELVEDATA_API_KEY", "EODHD_API_KEY"):
        monkeypatch.setenv(k, "test")


def _check(df):
    assert list(df.columns) == ["AAA", "BBB"]
    assert len(df) == 5 and df.notna().all().all()


def test_alpaca_paginates():
    pages = [
        {"bars": {"AAA": [{"t": d + "T05:00:00Z", "c": 1.0 + i} for i, d in enumerate(DATES)]},
         "next_page_token": "x"},
        {"bars": {"BBB": [{"t": d + "T05:00:00Z", "c": 2.0} for d in DATES]}, "next_page_token": None},
    ]
    s = FakeSession(lambda u, p: FakeResp(pages.pop(0)))
    _check(P.AlpacaProvider(session=s).get_prices(["AAA", "BBB"], "2024-01-01"))
    assert s.headers["APCA-API-KEY-ID"] == "test"
    assert s.calls[1][1]["page_token"] == "x"


@pytest.mark.parametrize("cls,payload", [
    (P.PolygonProvider, lambda: {"results": [{"t": pd.Timestamp(d).value // 10**6, "c": 1.0} for d in DATES]}),
    (P.TiingoProvider, lambda: [{"date": d + "T00:00:00.000Z", "adjClose": 1.0} for d in DATES]),
    (P.FMPProvider, lambda: [{"date": d, "adjClose": 1.0} for d in DATES]),
    (P.EODHDProvider, lambda: [{"date": d, "adjusted_close": 1.0} for d in DATES]),
    (P.TwelveDataProvider, lambda: {"values": [{"datetime": d, "close": "1.0"} for d in DATES], "status": "ok"}),
    (P.AlphaVantageProvider, lambda: {"Time Series (Daily)": {d: {"5. adjusted close": "1.0"} for d in DATES}}),
    (P.StooqProvider, lambda: "Date,Open,High,Low,Close,Volume\n" + "\n".join(f"{d},1,1,1,1.0,100" for d in DATES)),
])
def test_rest_providers(cls, payload):
    s = FakeSession(lambda u, p: FakeResp(payload()))
    _check(cls(session=s).get_prices(["AAA", "BBB"], "2024-01-01"))


def test_http_error_is_reported():
    s = FakeSession(lambda u, p: FakeResp({"error": "bad key"}, status=403))
    with pytest.raises(P.ProviderError, match="no data"):
        P.TiingoProvider(session=s).get_prices(["AAA"], "2024-01-01")


def test_missing_key(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY")
    with pytest.raises(P.ProviderError, match="POLYGON_API_KEY"):
        P.PolygonProvider(session=FakeSession(None))._fetch_one("AAA", "2024-01-01", None)


def test_broker_plans_deltas_and_defaults_to_paper(monkeypatch):
    monkeypatch.delenv("ALPACA_PAPER", raising=False)
    s = FakeSession(lambda u, p: FakeResp([{"symbol": "AAA", "qty": "10"}, {"symbol": "OLD", "qty": "-5"}]))
    b = AlpacaBroker(session=s)
    assert b.base == AlpacaBroker.PAPER
    w = pd.Series({"AAA": 0.5, "BBB": -0.5})
    px = pd.Series({"AAA": 100.0, "BBB": 50.0, "OLD": 20.0})
    orders = {o.symbol: o for o in b.plan_orders(w, px, capital=10_000, max_order_notional=4_000)}
    assert orders["AAA"].side == "buy" and orders["AAA"].qty == 40
    assert orders["BBB"].side == "sell" and orders["BBB"].qty == 80  # capped at $4k
    assert orders["OLD"].side == "buy" and orders["OLD"].qty == 5    # close stale short
