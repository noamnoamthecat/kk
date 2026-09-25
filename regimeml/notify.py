"""Daily advice e-mail (plain SMTP: works with Gmail app passwords, SendGrid,
Mailgun, AWS SES SMTP, Postmark...).

Environment: SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD,
EMAIL_FROM (defaults to SMTP_USER). Use STARTTLS on 587 or SSL on 465.
"""
from __future__ import annotations

import html
import os
import smtplib
import ssl
from email.message import EmailMessage


def _pct(x: float) -> str:
    return f"{x:.0%}"


def _usd(x: float) -> str:
    return f"${x:,.0f}"


def render(advice: dict, as_of: str | None, source: str) -> tuple[str, str, str]:
    """(subject, text, html) for one person's daily note."""
    act, plan, proj = advice["action"], advice["plan"], advice["projection"]
    name = advice["profile"].get("name") or "there"
    reg = act["regime"]
    regime_txt = f"{reg['label']} ({reg['prob']:.0%})" if reg else "n/a"
    verdict = "HOLD - no changes today" if act["verdict"] == "hold" else "REBALANCE - action needed"
    subject = f"[regimeml] {as_of or ''} {'Hold' if act['verdict'] == 'hold' else 'Rebalance'} · regime {regime_txt}"

    lines = [f"Hi {name},", "", f"Today's call: {verdict}", f"Market regime: {regime_txt} · equity tilt {act['tilt']:+.0%}", ""]
    if act["reasons"]:
        lines += ["Why: " + "; ".join(act["reasons"]), ""]
    if act["trades"]:
        lines.append("Moves:")
        lines += [f"  {t['action'].upper():4s} {_usd(t['amount']):>12s}  {t['label']} ({t['etf']})" for t in act["trades"]]
        lines.append("")
    lines.append("Target allocation (hold for):")
    for s in advice["sleeves"]:
        if s["today"] > 0:
            lines.append(f"  {_pct(s['today']):>4s}  {s['label']} ({s['etf']}) - {s['hold_for']}")
    if act["model_picks"]:
        lines += ["", "Model sleeve picks: " + ", ".join(f"{p['asset']} {_pct(p['weight'])}" for p in act["model_picks"])]
    lines += ["", f"Horizon {plan['horizon_years']:g}y · nominal range of outcomes (10th / median / 90th pct): "
              f"{_usd(proj['p10'])} / {_usd(proj['median'])} / {_usd(proj['p90'])} vs {_usd(proj['contributed'])} contributed"]
    lines += [f"  {n}" for n in plan["notes"]]
    lines += ["", f"Data: {source}", advice["disclaimer"]]
    text = "\n".join(lines)

    e = html.escape
    rows = "".join(
        f"<tr><td style='padding:4px 12px 4px 0'>{e(s['label'])} <span style='color:#898781'>{e(s['etf'])}</span></td>"
        f"<td style='text-align:right;padding:4px 12px'>{_pct(s['today'])}</td>"
        f"<td style='color:#52514e'>{e(s['hold_for'])}</td></tr>"
        for s in advice["sleeves"] if s["today"] > 0)
    trades = "".join(
        f"<li><b>{e(t['action'].upper())}</b> {_usd(t['amount'])} of {e(t['label'])} ({e(t['etf'])})</li>"
        for t in act["trades"]) or "<li>No trades. Stay the course.</li>"
    color = "#0ca30c" if act["verdict"] == "hold" else "#d03b3b"
    body = f"""<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:560px;color:#0b0b0b">
<p>Hi {e(name)},</p>
<p style="font-size:20px;margin:8px 0"><span style="color:{color}">●</span> <b>{e(verdict)}</b></p>
<p style="color:#52514e">Market regime: <b>{e(regime_txt)}</b> · equity tilt {act['tilt']:+.0%}<br>{e('; '.join(act['reasons']))}</p>
<h3 style="margin-bottom:4px">Moves</h3><ul>{trades}</ul>
<h3 style="margin-bottom:4px">Target allocation</h3><table style="border-collapse:collapse;font-size:14px">{rows}</table>
<p style="font-size:14px">Horizon {plan['horizon_years']:g} years. Nominal range of outcomes (10th / median / 90th percentile):
<b>{_usd(proj['p10'])} / {_usd(proj['median'])} / {_usd(proj['p90'])}</b> vs {_usd(proj['contributed'])} contributed.</p>
{''.join(f'<p style="font-size:14px">• {e(n)}</p>' for n in plan['notes'])}
<p style="font-size:12px;color:#898781">Data: {e(source)}. {e(advice['disclaimer'])}</p></div>"""
    return subject, text, body


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER"))


def send(to: str, subject: str, text: str, html_body: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user, pwd = os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", "")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ.get("EMAIL_FROM", user), to
    msg.set_content(text)
    msg.add_alternative(html_body, subtype="html")
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.send_message(msg)
