"""Personal allocation advisor: profile -> strategic plan -> daily tactical action.

Method (transparent, rules-based, in the spirit of standard planning practice):
  1. Foundations first: emergency fund, then high-interest debt.
  2. Money needed within ~2 years does not belong in stocks.
  3. Equity share = min(capacity from horizon, willingness from risk score,
     age guard-rail for retirement goals).
  4. Diversified low-cost core (US + international stocks, bonds, T-bills),
     plus a small, capped "model sleeve" of the ML stock picks for long
     horizons and higher risk tolerance only.
  5. A bounded tactical tilt from the regime model (at most -12pp equities in a
     crisis) moves money to T-bills and back.
  6. Daily action is "hold" unless a sleeve drifts outside its band or the
     tilt changes materially -- trading every day destroys returns via costs
     and taxes.

Educational tool, not individualized financial advice.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

GOALS = {
    "retirement": "Retirement",
    "wealth": "Grow wealth",
    "house": "Buy a home",
    "education": "Education",
    "income": "Generate income",
    "preservation": "Preserve capital",
}

SLEEVES = {
    # key: (label, example ETF, expected nominal return, volatility, min holding period)
    "us_equity": ("US stocks", "VTI", 0.070, 0.16, "5+ years"),
    "intl_equity": ("International stocks", "VXUS", 0.070, 0.17, "5+ years"),
    "model": ("Model stock picks (active)", "top-ranked stocks", 0.075, 0.20, "reviewed daily, held ~1-4 weeks"),
    "bonds": ("Core bonds", "BND", 0.042, 0.06, "3-5 years"),
    "tips": ("Inflation-protected bonds", "SCHP", 0.040, 0.06, "3-5 years"),
    "cash": ("T-bills / cash", "SGOV", 0.035, 0.005, "any; fully liquid"),
}

RISK_EQUITY = {1: 0.20, 2: 0.40, 3: 0.60, 4: 0.75, 5: 0.90}
BAND = 0.05  # absolute rebalance band per sleeve


@dataclass
class Profile:
    age: int
    net_worth: float
    investable: float                     # total money to invest (incl. current holdings)
    goal: str = "wealth"
    horizon_years: float | None = None    # derived from goal/age when missing
    risk_tolerance: int = 3               # 1 (very cautious) .. 5 (aggressive)
    monthly_expenses: float = 0.0
    monthly_contribution: float = 0.0
    emergency_fund: float = 0.0           # cash already set aside
    high_interest_debt: float = 0.0       # e.g. credit cards > ~8% APR
    name: str = ""
    email: str = ""
    current: dict = field(default_factory=dict)  # sleeve -> $ currently held (for rebalancing)

    def validate(self) -> "Profile":
        if not 16 <= self.age <= 100:
            raise ValueError("age must be between 16 and 100")
        if self.investable < 0 or self.net_worth < 0:
            raise ValueError("amounts must be non-negative")
        if self.goal not in GOALS:
            raise ValueError(f"goal must be one of {list(GOALS)}")
        if self.risk_tolerance not in RISK_EQUITY:
            raise ValueError("risk_tolerance must be 1..5")
        return self

    def horizon(self) -> float:
        if self.horizon_years:
            return float(self.horizon_years)
        if self.goal == "retirement":
            return float(max(65 - self.age, 5))
        return {"house": 4, "education": 8, "income": 10, "preservation": 3}.get(self.goal, 10)


def _equity_capacity(h: float) -> float:
    """Maximum stock share that the time horizon can absorb."""
    if h < 2:
        return 0.0
    if h < 5:
        return 0.40
    if h < 10:
        return 0.70
    return 0.90


def regime_tilt(regime_probs: list[float] | None, horizon: float) -> float:
    """Tactical equity shift in [-0.12, +0.03] from P(calm, stressed, crisis)."""
    if not regime_probs or horizon < 3:
        return 0.0
    p = list(regime_probs) + [0.0] * (3 - len(regime_probs))
    return float(np.clip(0.03 * p[0] - 0.04 * p[1] - 0.12 * p[2], -0.12, 0.03))


def strategic_plan(p: Profile) -> dict:
    p.validate()
    h = p.horizon()
    notes = []

    # 1) foundations
    ef_target = 6 * p.monthly_expenses
    ef_gap = max(0.0, ef_target - p.emergency_fund)
    reserve = min(p.investable, ef_gap)
    debt_pay = min(p.investable - reserve, p.high_interest_debt)
    investable = p.investable - reserve - debt_pay
    if reserve > 0:
        notes.append(f"Set aside ${reserve:,.0f} first to complete a 6-month emergency fund (in T-bills / high-yield savings).")
    if debt_pay > 0:
        notes.append(f"Pay down ${debt_pay:,.0f} of high-interest debt before investing: a guaranteed return no portfolio can match.")
    if p.investable > 0 and p.net_worth > 0 and p.investable / p.net_worth > 0.9 and p.age > 55:
        notes.append("This money is most of your net worth: keep risk moderate and consider a fee-only fiduciary adviser.")

    # 2-3) equity share
    eq = min(_equity_capacity(h), RISK_EQUITY[p.risk_tolerance])
    if p.goal == "retirement":
        eq = min(eq, max(0.2, (120 - p.age) / 100))
    if p.goal == "preservation":
        eq = min(eq, 0.25)
    if p.goal == "income":
        eq = min(eq, 0.50)

    # 4) sleeves
    model_share = 0.10 * eq if (h >= 5 and p.risk_tolerance >= 3) else 0.0
    w = {
        "us_equity": 0.6 * (eq - model_share),
        "intl_equity": 0.4 * (eq - model_share),
        "model": model_share,
    }
    rest = 1 - eq
    if h < 2:
        w.update(bonds=0.0, tips=0.0, cash=rest)
    elif h < 5:
        w.update(bonds=0.5 * rest, tips=0.0, cash=0.5 * rest)
    else:
        tips = 0.25 * rest if p.goal in ("retirement", "income", "preservation") else 0.10 * rest
        w.update(bonds=0.9 * rest - tips, tips=tips, cash=0.1 * rest)
    if h < 2:
        notes.append("Your horizon is under 2 years: stocks can fall 30%+ in that window, so this plan holds none.")

    return {"horizon_years": h, "equity_share": eq, "weights": w, "invest_now": investable,
            "reserve": reserve, "debt_paydown": debt_pay, "notes": notes}


def project(weights: dict, amount: float, monthly: float, years: float,
            n_paths: int = 4000, seed: int = 0) -> dict:
    """Monte-Carlo range of outcomes from long-run sleeve assumptions (not a forecast)."""
    mu = sum(weights[k] * SLEEVES[k][2] for k in weights)
    stock = sum(weights[k] for k in ("us_equity", "intl_equity", "model"))
    # Stocks ~0.85 correlated with each other, ~0 with bonds: approximate portfolio vol.
    vol = float(np.sqrt((stock * 0.165) ** 2 + ((weights["bonds"] + weights["tips"]) * 0.06) ** 2))
    n = max(int(round(years * 12)), 1)
    rng = np.random.default_rng(seed)
    r = rng.normal(mu / 12 - vol**2 / 24, vol / np.sqrt(12), (n_paths, n))
    v = np.full(n_paths, float(amount))
    for t in range(n):
        v = v * np.exp(r[:, t]) + monthly
    contributed = amount + monthly * n
    q = np.percentile(v, [10, 50, 90])
    return {"expected_return": mu, "volatility": vol, "contributed": contributed,
            "p10": float(q[0]), "median": float(q[1]), "p90": float(q[2]), "years": years}


def daily_action(p: Profile, plan: dict, regime_probs: list[float] | None,
                 model_picks: list[dict] | None = None, prev_tilt: float | None = None) -> dict:
    """Today's target, the trades needed (if any), and the reasoning."""
    h = plan["horizon_years"]
    tilt = regime_tilt(regime_probs, h)
    target = dict(plan["weights"])
    eq_keys = ["us_equity", "intl_equity", "model"]
    eq = sum(target[k] for k in eq_keys)
    if eq > 0 and tilt != 0:
        new_eq = float(np.clip(eq + tilt, 0.0, 1.0))
        for k in eq_keys:
            target[k] *= new_eq / eq
        target["cash"] += eq - new_eq

    total = sum(p.current.values()) if p.current else 0.0
    base = total if total > 0 else plan["invest_now"]
    trades, reasons = [], []
    if total > 0:
        cur = {k: p.current.get(k, 0.0) / total for k in target}
        drift = {k: cur[k] - target[k] for k in target}
        out = {k: d for k, d in drift.items() if abs(d) > BAND}
        if out:
            reasons.append("sleeves outside the ±5pp band: " + ", ".join(SLEEVES[k][0] for k in out))
            for k, d in sorted(drift.items(), key=lambda kv: kv[1]):
                amt = -d * total
                if abs(amt) >= 1:
                    trades.append({"sleeve": k, "label": SLEEVES[k][0], "etf": SLEEVES[k][1],
                                   "action": "buy" if amt > 0 else "sell", "amount": abs(amt)})
    else:
        reasons.append("initial investment")
        trades = [{"sleeve": k, "label": SLEEVES[k][0], "etf": SLEEVES[k][1], "action": "buy",
                   "amount": target[k] * base} for k in target if target[k] * base >= 1]

    if prev_tilt is not None and abs(tilt - prev_tilt) >= 0.03:
        reasons.append(f"market regime shifted the equity tilt from {prev_tilt:+.0%} to {tilt:+.0%}")
        if not trades and total > 0:
            for k in target:
                amt = (target[k] - p.current.get(k, 0.0) / total) * total
                if abs(amt) >= 1:
                    trades.append({"sleeve": k, "label": SLEEVES[k][0], "etf": SLEEVES[k][1],
                                   "action": "buy" if amt > 0 else "sell", "amount": abs(amt)})

    verdict = "rebalance" if trades else "hold"
    labels = ["calm", "stressed", "crisis"]
    regime = None
    if regime_probs:
        k = int(np.argmax(regime_probs))
        regime = {"label": labels[k], "prob": float(regime_probs[k])}
    return {
        "verdict": verdict, "tilt": tilt, "target": target, "trades": trades, "reasons": reasons,
        "regime": regime,
        "model_picks": (model_picks or [])[:10] if target.get("model", 0) > 0 else [],
        "holding": {k: SLEEVES[k][4] for k in target if target[k] > 0},
    }


def advise(p: Profile, regime_probs: list[float] | None = None, model_picks: list[dict] | None = None,
           prev_tilt: float | None = None) -> dict:
    plan = strategic_plan(p)
    act = daily_action(p, plan, regime_probs, model_picks, prev_tilt)
    proj = project(act["target"], plan["invest_now"],
                   p.monthly_contribution, plan["horizon_years"])
    sleeves = [{"key": k, "label": SLEEVES[k][0], "etf": SLEEVES[k][1], "strategic": plan["weights"][k],
                "today": act["target"][k], "hold_for": SLEEVES[k][4]} for k in SLEEVES]
    return {"profile": {k: v for k, v in asdict(p).items() if k != "email"}, "goal_label": GOALS[p.goal],
            "plan": plan, "action": act, "projection": proj, "sleeves": sleeves,
            "disclaimer": "Educational output from a quantitative model, not individualized financial, "
                          "tax or legal advice. Past and simulated performance do not guarantee future results."}


def picks_from_state(state: dict, n: int = 10) -> list[dict]:
    """Long-only model picks: highest-scoring names from the engine's latest book."""
    rows = [r for r in state.get("portfolio", []) if r.get("score") is not None]
    rows.sort(key=lambda r: -r["score"])
    top = [r for r in rows[:n] if r["score"] > 0]
    tot = sum(r["score"] for r in top) or 1.0
    return [{"asset": r["asset"], "weight": r["score"] / tot, "price": r.get("price")} for r in top]
