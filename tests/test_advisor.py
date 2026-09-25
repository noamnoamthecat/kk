import smtplib

import pytest

from regimeml.advisor import Profile, advise, daily_action, regime_tilt, strategic_plan
from regimeml.notify import render, send


def total(w):
    return sum(w.values())


@pytest.mark.parametrize("p", [
    Profile(age=25, net_worth=50_000, investable=40_000, goal="wealth", risk_tolerance=5),
    Profile(age=45, net_worth=900_000, investable=500_000, goal="retirement", risk_tolerance=3),
    Profile(age=70, net_worth=2e6, investable=1.5e6, goal="income", risk_tolerance=2),
    Profile(age=30, net_worth=90_000, investable=80_000, goal="house", horizon_years=1),
    Profile(age=55, net_worth=300_000, investable=200_000, goal="preservation", risk_tolerance=1),
])
def test_plans_are_valid_allocations(p):
    plan = strategic_plan(p)
    assert abs(total(plan["weights"]) - 1) < 1e-9
    assert all(v >= -1e-12 for v in plan["weights"].values())
    act = daily_action(p, plan, [0.0, 0.2, 0.8])
    assert abs(total(act["target"]) - 1) < 1e-9 and all(v >= -1e-12 for v in act["target"].values())


def test_short_horizon_holds_no_stocks_and_foundations_come_first():
    p = Profile(age=30, net_worth=50_000, investable=30_000, goal="house", horizon_years=1.5,
                monthly_expenses=3000, emergency_fund=5000, high_interest_debt=4000)
    plan = strategic_plan(p)
    assert plan["equity_share"] == 0
    assert plan["reserve"] == 13_000 and plan["debt_paydown"] == 4000
    assert plan["invest_now"] == 13_000


def test_equity_falls_with_age_for_retirement():
    eq = [strategic_plan(Profile(age=a, net_worth=1e5, investable=1e5, goal="retirement",
                                 risk_tolerance=5))["equity_share"] for a in (25, 45, 60, 75)]
    assert eq == sorted(eq, reverse=True) and eq[0] > eq[-1]


def test_regime_tilt_bounded_and_skipped_for_short_horizons():
    assert regime_tilt([0, 0, 1], 20) == pytest.approx(-0.12)
    assert regime_tilt([1, 0, 0], 20) == pytest.approx(0.03)
    assert regime_tilt([0, 0, 1], 2) == 0.0


def test_hold_inside_band_rebalance_outside():
    p = Profile(age=40, net_worth=2e5, investable=1e5, goal="wealth", risk_tolerance=3)
    plan = strategic_plan(p)
    on_target = {k: v * 1e5 for k, v in daily_action(p, plan, [1, 0, 0])["target"].items()}
    p.current = on_target
    assert daily_action(p, plan, [1, 0, 0], prev_tilt=regime_tilt([1, 0, 0], 10))["verdict"] == "hold"
    drifted = dict(on_target)
    drifted["us_equity"] += 20_000
    drifted["bonds"] -= 20_000
    p.current = drifted
    act = daily_action(p, plan, [1, 0, 0])
    assert act["verdict"] == "rebalance"
    buys = sum(t["amount"] for t in act["trades"] if t["action"] == "buy")
    sells = sum(t["amount"] for t in act["trades"] if t["action"] == "sell")
    assert buys == pytest.approx(sells)  # rebalancing is self-financing


def test_validation():
    with pytest.raises(ValueError):
        strategic_plan(Profile(age=10, net_worth=1, investable=1))
    with pytest.raises(ValueError):
        strategic_plan(Profile(age=30, net_worth=1, investable=1, goal="lottery"))


def test_email_render_and_send(monkeypatch):
    p = Profile(age=34, net_worth=2.5e5, investable=1e5, goal="retirement", name="Sam <b>", email="s@x.io")
    subject, text, html = render(advise(p, [0.1, 0.2, 0.7], [{"asset": "AAA", "weight": 1.0}]), "2026-01-02", "test")
    assert "Rebalance" in subject and "Sam <b>" in text and "Sam &lt;b&gt;" in html  # html is escaped
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None): sent["host"] = (host, port)
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self, context=None): sent["tls"] = True
        def login(self, u, pw): sent["login"] = u
        def send_message(self, msg): sent["to"] = msg["To"]

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    send("s@x.io", subject, text, html)
    assert sent == {"host": ("smtp.example.com", 587), "tls": True, "login": "bot@example.com", "to": "s@x.io"}


def test_model_picks_are_capped():
    from regimeml.advisor import picks_from_state
    rows = [{"asset": f"A{i}", "score": s, "price": 1.0} for i, s in enumerate([9, 1, 1, 1, 1, 0.5, -1])]
    picks = picks_from_state({"portfolio": rows})
    w = [p["weight"] for p in picks]
    assert len(picks) == 6 and abs(sum(w) - 1) < 1e-9 and max(w) <= 0.2 + 1e-9
