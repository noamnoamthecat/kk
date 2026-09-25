"""Subscriber store + the daily e-mail job run after each market close."""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, fields
from datetime import date
from pathlib import Path

from .advisor import Profile, advise, picks_from_state
from .notify import render, send, smtp_configured

log = logging.getLogger("regimeml.subscribers")


def profile_from_dict(d: dict) -> Profile:
    names = {f.name for f in fields(Profile)}
    return Profile(**{k: v for k, v in d.items() if k in names and v not in (None, "")}).validate()


class SubscriberStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self._lock = threading.Lock()

    def _read(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self.path)

    def upsert(self, p: Profile) -> None:
        if not p.email or "@" not in p.email:
            raise ValueError("a valid email is required to subscribe")
        with self._lock:
            data = self._read()
            prev = data.get(p.email.lower(), {})
            data[p.email.lower()] = {"profile": asdict(p), "last_sent": prev.get("last_sent"),
                                     "last_tilt": prev.get("last_tilt")}
            self._write(data)

    def remove(self, email: str) -> bool:
        with self._lock:
            data = self._read()
            found = data.pop(email.lower(), None) is not None
            self._write(data)
            return found

    def count(self) -> int:
        return len(self._read())

    def advice_for(self, rec: dict, state: dict) -> dict:
        p = profile_from_dict(rec["profile"])
        return advise(p, state.get("regime", {}).get("current"), picks_from_state(state), rec.get("last_tilt"))

    def send_all(self, state: dict, force: bool = False) -> dict:
        """Send today's note to every subscriber (once per calendar day each)."""
        today = state.get("as_of") or str(date.today())
        sent, skipped, failed = 0, 0, 0
        with self._lock:
            data = self._read()
            for email, rec in data.items():
                if rec.get("last_sent") == today and not force:
                    skipped += 1
                    continue
                try:
                    adv = self.advice_for(rec, state)
                    subject, text, body = render(adv, state.get("as_of"), state.get("source", ""))
                    if smtp_configured():
                        send(email, subject, text, body)
                    else:
                        log.info("SMTP not configured; would send to %s: %s", email, subject)
                    rec["last_sent"], rec["last_tilt"] = today, adv["action"]["tilt"]
                    sent += 1
                except Exception:
                    log.exception("email to %s failed", email)
                    failed += 1
            self._write(data)
        return {"sent": sent, "skipped": skipped, "failed": failed, "smtp": smtp_configured()}
