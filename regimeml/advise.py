"""One-shot daily advice job (for cron / GitHub Actions / any scheduler).

    python -m regimeml.advise --profile me.json                   # print today's note (simulated market)
    python -m regimeml.advise --profile me.json --provider yahoo  # real market data
    python -m regimeml.advise --subscribers state/subscribers.json --provider alpaca --email

The profile JSON holds the fields of :class:`regimeml.advisor.Profile`
(age, net_worth, investable, goal, risk_tolerance, email, ...).
"""
from __future__ import annotations

import argparse
import json
import os

from .advisor import advise, picks_from_state
from .engine import Engine, EngineConfig, MarketSource, ReplaySource
from .notify import render, send, smtp_configured
from .subscribers import SubscriberStore, profile_from_dict
from .universe import LARGE_CAP_US


def market_state(provider: str | None, tickers: list[str]) -> dict:
    """Train on the latest data once and return the engine's published state."""
    src = MarketSource(provider, tickers) if provider else ReplaySource(start=2000)
    eng = Engine(src, EngineConfig())
    eng.step()
    _, state = eng.snapshot()
    if not state.get("regime"):
        raise RuntimeError(f"engine produced no signal: {state.get('error') or state.get('status')}")
    return state


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument("--profile", help="JSON file with one profile")
    who.add_argument("--subscribers", help="subscriber store JSON (as written by the web app)")
    ap.add_argument("--provider", help="real data provider (default: simulated market)")
    ap.add_argument("--tickers", nargs="+", default=LARGE_CAP_US)
    ap.add_argument("--email", action="store_true", help="send the note by e-mail (needs SMTP_* env)")
    a = ap.parse_args(argv)

    state = market_state(a.provider, a.tickers)
    if a.subscribers:
        print(json.dumps(SubscriberStore(a.subscribers).send_all(state) if a.email else
                         {"subscribers": SubscriberStore(a.subscribers).count(), "email": False}))
        return

    with open(a.profile) as f:
        p = profile_from_dict(json.load(f))
    adv = advise(p, state["regime"]["current"], picks_from_state(state))
    subject, text, body = render(adv, state.get("as_of"), state.get("source", ""))
    print(subject, "\n", text, sep="")
    if a.email:
        if not smtp_configured():
            raise SystemExit("SMTP not configured: set SMTP_HOST, SMTP_USER, SMTP_PASSWORD (see README)")
        to = os.environ.get("EMAIL_TO") or p.email
        if not to:
            raise SystemExit("no recipient: set EMAIL_TO or put an email in the profile")
        send(to, subject, text, body)
        print(f"\nsent to {to}")


if __name__ == "__main__":
    main()
