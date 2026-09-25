"""Real market-data connectors.

Every provider returns the same thing: a wide DataFrame of split/dividend
adjusted daily closes (index = date, one column per ticker).

| provider   | cost              | credentials (env vars)                           |
|------------|-------------------|--------------------------------------------------|
| yahoo      | free, unofficial  | none                                             |
| stooq      | free              | none                                             |
| alpaca     | free tier         | ALPACA_API_KEY, ALPACA_SECRET_KEY                |
| polygon    | free tier / paid  | POLYGON_API_KEY                                  |
| tiingo     | free tier / paid  | TIINGO_API_KEY                                   |
| fmp        | free tier / paid  | FMP_API_KEY  (Financial Modeling Prep)           |
| alphavantage | free tier / paid | ALPHAVANTAGE_API_KEY                            |
| twelvedata | free tier / paid  | TWELVEDATA_API_KEY                               |
| eodhd      | free tier / paid  | EODHD_API_KEY                                    |
| bloomberg  | Terminal/B-PIPE   | running Terminal or B-PIPE; BLP_HOST, BLP_PORT   |
"""
from __future__ import annotations

import io
import os
import time
from abc import ABC, abstractmethod

import pandas as pd
import requests

DEFAULT_TIMEOUT = 30


class ProviderError(RuntimeError):
    pass


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise ProviderError(f"environment variable {name} is not set")
    return v


class DataProvider(ABC):
    name: str = "base"

    def __init__(self, session: requests.Session | None = None):
        self.http = session or requests.Session()

    @abstractmethod
    def _fetch_one(self, ticker: str, start: str, end: str | None) -> pd.Series:
        """Adjusted close series for one ticker, indexed by tz-naive date."""

    def get_prices(self, tickers: list[str], start: str = "2015-01-01", end: str | None = None,
                   min_history: float = 0.9) -> pd.DataFrame:
        series, failed = {}, []
        for t in tickers:
            try:
                s = self._fetch_one(t, start, end)
                if s is not None and len(s):
                    series[t] = s
                else:
                    failed.append(t)
            except (ProviderError, requests.RequestException, KeyError, ValueError) as e:
                failed.append(f"{t} ({e})")
        if not series:
            raise ProviderError(f"{self.name}: no data returned. failures: {failed}")
        df = pd.DataFrame(series).sort_index()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df = df[~df.index.duplicated(keep="last")]
        # Drop tickers with too little history, then align on common dates.
        keep = df.notna().mean() >= min_history
        df = df.loc[:, keep].ffill(limit=3).dropna()
        if failed:
            print(f"[{self.name}] skipped: {', '.join(failed)}")
        return df

    def _get(self, url: str, **kw) -> requests.Response:
        for attempt in range(4):
            r = self.http.get(url, timeout=DEFAULT_TIMEOUT, **kw)
            if r.status_code != 429:
                break
            time.sleep(2 ** attempt)  # rate limited: back off
        if r.status_code >= 400:
            raise ProviderError(f"HTTP {r.status_code} from {url.split('?')[0]}: {r.text[:200]}")
        return r


class YahooProvider(DataProvider):
    """Yahoo Finance via yfinance. Free, no key, but unofficial -- fine for
    research, not something to bet production money on."""
    name = "yahoo"

    def get_prices(self, tickers, start="2015-01-01", end=None, min_history=0.9):
        import yfinance as yf

        df = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)["Close"]
        if isinstance(df, pd.Series):
            df = df.to_frame(tickers[0])
        df = df.loc[:, df.notna().mean() >= min_history].ffill(limit=3).dropna()
        if df.empty:
            raise ProviderError("yahoo: no data returned (network blocked or bad tickers)")
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df

    def _fetch_one(self, ticker, start, end):  # pragma: no cover - batch download above
        return self.get_prices([ticker], start, end)[ticker]


class StooqProvider(DataProvider):
    """stooq.com daily CSVs. Free, no key. US tickers use the ``.us`` suffix."""
    name = "stooq"
    URL = "https://stooq.com/q/d/l/"

    def _fetch_one(self, ticker, start, end):
        sym = ticker.lower() if "." in ticker else f"{ticker.lower()}.us"
        params = {"s": sym, "i": "d", "d1": start.replace("-", "")}
        if end:
            params["d2"] = end.replace("-", "")
        r = self._get(self.URL, params=params)
        if not r.text.startswith("Date"):
            raise ProviderError(f"stooq: unexpected response for {sym}: {r.text[:80]!r}")
        df = pd.read_csv(io.StringIO(r.text), parse_dates=["Date"], index_col="Date")
        return df["Close"]


class AlpacaProvider(DataProvider):
    """Alpaca Market Data API v2. Free tier uses the IEX feed; set
    ALPACA_DATA_FEED=sip on a paid plan for consolidated tape."""
    name = "alpaca"
    URL = "https://data.alpaca.markets/v2/stocks/bars"

    def __init__(self, session=None):
        super().__init__(session)
        self.http.headers.update({
            "APCA-API-KEY-ID": _env("ALPACA_API_KEY"),
            "APCA-API-SECRET-KEY": _env("ALPACA_SECRET_KEY"),
        })
        self.feed = os.environ.get("ALPACA_DATA_FEED", "iex")

    def get_prices(self, tickers, start="2015-01-01", end=None, min_history=0.9):
        bars: dict[str, list] = {t: [] for t in tickers}
        params = {"symbols": ",".join(tickers), "timeframe": "1Day", "start": start,
                  "adjustment": "all", "limit": 10000, "feed": self.feed}
        if end:
            params["end"] = end
        while True:
            payload = self._get(self.URL, params=params).json()
            for sym, rows in (payload.get("bars") or {}).items():
                bars.setdefault(sym, []).extend(rows)
            token = payload.get("next_page_token")
            if not token:
                break
            params["page_token"] = token
        series = {s: pd.Series({r["t"][:10]: r["c"] for r in rows}) for s, rows in bars.items() if rows}
        if not series:
            raise ProviderError("alpaca: no bars returned")
        df = pd.DataFrame(series).sort_index()
        df.index = pd.to_datetime(df.index)
        return df.loc[:, df.notna().mean() >= min_history].ffill(limit=3).dropna()

    def _fetch_one(self, ticker, start, end):
        return self.get_prices([ticker], start, end)[ticker]


class PolygonProvider(DataProvider):
    """Polygon.io aggregates API (adjusted daily bars)."""
    name = "polygon"
    URL = "https://api.polygon.io/v2/aggs/ticker/{t}/range/1/day/{a}/{b}"

    def _fetch_one(self, ticker, start, end):
        end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
        r = self._get(self.URL.format(t=ticker, a=start, b=end),
                      params={"adjusted": "true", "sort": "asc", "limit": 50000,
                              "apiKey": _env("POLYGON_API_KEY")})
        rows = r.json().get("results") or []
        return pd.Series({pd.Timestamp(x["t"], unit="ms"): x["c"] for x in rows}, dtype=float)


class TiingoProvider(DataProvider):
    """Tiingo end-of-day API (``adjClose``)."""
    name = "tiingo"
    URL = "https://api.tiingo.com/tiingo/daily/{t}/prices"

    def _fetch_one(self, ticker, start, end):
        params = {"startDate": start, "token": _env("TIINGO_API_KEY")}
        if end:
            params["endDate"] = end
        rows = self._get(self.URL.format(t=ticker), params=params).json()
        return pd.Series({x["date"][:10]: x["adjClose"] for x in rows}, dtype=float)


class BloombergProvider(DataProvider):
    """Bloomberg Desktop API / B-PIPE through ``blpapi``.

    Needs a licensed Bloomberg Terminal (or B-PIPE / Server API) reachable at
    BLP_HOST:BLP_PORT (default localhost:8194) and the blpapi package:
        pip install blpapi --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/
    Tickers may be plain ("AAPL" -> "AAPL US Equity") or full Bloomberg ids.
    """
    name = "bloomberg"

    def get_prices(self, tickers, start="2015-01-01", end=None, min_history=0.9):
        try:
            import blpapi
        except ImportError as e:
            raise ProviderError("blpapi not installed -- see BloombergProvider docstring") from e

        opts = blpapi.SessionOptions()
        opts.setServerHost(os.environ.get("BLP_HOST", "localhost"))
        opts.setServerPort(int(os.environ.get("BLP_PORT", "8194")))
        session = blpapi.Session(opts)
        if not session.start() or not session.openService("//blp/refdata"):
            raise ProviderError("could not connect to Bloomberg (is the Terminal running?)")
        ids = {t if " " in t else f"{t} US Equity": t for t in tickers}
        req = session.getService("//blp/refdata").createRequest("HistoricalDataRequest")
        for sec in ids:
            req.getElement("securities").appendValue(sec)
        req.getElement("fields").appendValue("PX_LAST")
        req.set("startDate", start.replace("-", ""))
        req.set("endDate", (end or pd.Timestamp.today().strftime("%Y-%m-%d")).replace("-", ""))
        req.set("periodicitySelection", "DAILY")
        req.set("adjustmentNormal", True)
        req.set("adjustmentAbnormal", True)
        req.set("adjustmentSplit", True)
        session.sendRequest(req)

        out: dict[str, dict] = {}
        try:
            while True:
                ev = session.nextEvent(5000)
                for msg in ev:
                    if not msg.hasElement("securityData"):
                        continue
                    sd = msg.getElement("securityData")
                    sec = sd.getElementAsString("security")
                    fd = sd.getElement("fieldData")
                    rows = out.setdefault(ids.get(sec, sec), {})
                    for i in range(fd.numValues()):
                        pt = fd.getValueAsElement(i)
                        if pt.hasElement("PX_LAST"):
                            rows[pd.Timestamp(str(pt.getElementAsDatetime("date")))] = pt.getElementAsFloat("PX_LAST")
                if ev.eventType() == blpapi.Event.RESPONSE:
                    break
        finally:
            session.stop()
        df = pd.DataFrame(out).sort_index()
        return df.loc[:, df.notna().mean() >= min_history].ffill(limit=3).dropna()

    def _fetch_one(self, ticker, start, end):  # pragma: no cover
        return self.get_prices([ticker], start, end)[ticker]


class FMPProvider(DataProvider):
    """Financial Modeling Prep dividend-adjusted EOD prices."""
    name = "fmp"
    URL = "https://financialmodelingprep.com/stable/historical-price-eod/dividend-adjusted"

    def _fetch_one(self, ticker, start, end):
        params = {"symbol": ticker, "from": start, "apikey": _env("FMP_API_KEY")}
        if end:
            params["to"] = end
        rows = self._get(self.URL, params=params).json()
        if isinstance(rows, dict):  # legacy v3 shape / error payload
            rows = rows.get("historical") or []
        return pd.Series({x["date"][:10]: x.get("adjClose", x.get("close")) for x in rows}, dtype=float)


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage TIME_SERIES_DAILY_ADJUSTED (free tier: ~25 calls/day)."""
    name = "alphavantage"
    URL = "https://www.alphavantage.co/query"

    def _fetch_one(self, ticker, start, end):
        js = self._get(self.URL, params={"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": ticker,
                                         "outputsize": "full", "apikey": _env("ALPHAVANTAGE_API_KEY")}).json()
        ts = js.get("Time Series (Daily)")
        if ts is None:
            raise ProviderError(f"alphavantage: {js.get('Note') or js.get('Information') or js}")
        s = pd.Series({d: float(v["5. adjusted close"]) for d, v in ts.items()})
        s.index = pd.to_datetime(s.index)
        s = s.sort_index()
        return s[start:end] if end else s[start:]


class TwelveDataProvider(DataProvider):
    """Twelve Data /time_series with full split+dividend adjustment."""
    name = "twelvedata"
    URL = "https://api.twelvedata.com/time_series"

    def _fetch_one(self, ticker, start, end):
        params = {"symbol": ticker, "interval": "1day", "start_date": start, "outputsize": 5000,
                  "adjust": "all", "apikey": _env("TWELVEDATA_API_KEY")}
        if end:
            params["end_date"] = end
        js = self._get(self.URL, params=params).json()
        if js.get("status") == "error":
            raise ProviderError(f"twelvedata: {js.get('message')}")
        return pd.Series({x["datetime"][:10]: float(x["close"]) for x in js.get("values", [])})


class EODHDProvider(DataProvider):
    """EOD Historical Data end-of-day API (``adjusted_close``)."""
    name = "eodhd"
    URL = "https://eodhd.com/api/eod/{t}"

    def _fetch_one(self, ticker, start, end):
        sym = ticker if "." in ticker else f"{ticker}.US"
        params = {"from": start, "fmt": "json", "api_token": _env("EODHD_API_KEY")}
        if end:
            params["to"] = end
        rows = self._get(self.URL.format(t=sym), params=params).json()
        return pd.Series({x["date"]: x["adjusted_close"] for x in rows}, dtype=float)


PROVIDERS: dict[str, type[DataProvider]] = {
    p.name: p for p in (YahooProvider, StooqProvider, AlpacaProvider, PolygonProvider,
                        TiingoProvider, FMPProvider, AlphaVantageProvider, TwelveDataProvider,
                        EODHDProvider, BloombergProvider)
}


def get_provider(name: str) -> DataProvider:
    try:
        return PROVIDERS[name.lower()]()
    except KeyError:
        raise ProviderError(f"unknown provider {name!r}; choose from {sorted(PROVIDERS)}") from None
