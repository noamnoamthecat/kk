"""Web dashboard + JSON/SSE API around the live engine.

    uvicorn regimeml.server:app --host 0.0.0.0 --port 8000

Environment: see ``engine_from_env`` (REGIMEML_MODE=replay|live, REGIMEML_PROVIDER, ...).
Set REGIMEML_TOKEN to require ``?token=...`` on every request.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .advisor import advise, picks_from_state
from .engine import Engine, engine_from_env
from .subscribers import SubscriberStore, profile_from_dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
WEB = Path(__file__).parent / "web"


def create_app(engine: Engine | None = None, start_engine: bool = True) -> FastAPI:
    token = os.environ.get("REGIMEML_TOKEN")
    store = SubscriberStore(os.environ.get("REGIMEML_PROFILES", "state/subscribers.json"))
    email_in_replay = os.environ.get("REGIMEML_EMAIL_IN_REPLAY", "false").lower() == "true"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine or engine_from_env()
        eng = app.state.engine
        # Daily e-mails only follow real market closes (replay advances every few seconds).
        if eng.src.is_live or email_in_replay:
            eng.on_new_day.append(lambda st: eng._event(f"daily emails: {store.send_all(st)}"))
        if start_engine:
            app.state.engine.start()
        yield
        app.state.engine.stop()

    app = FastAPI(title="regimeml", lifespan=lifespan)

    @app.middleware("http")
    async def auth(request: Request, call_next):
        # The page shell and static assets are public; all data endpoints need the token.
        public = request.url.path in ("/", "/healthz") or request.url.path.startswith("/static/")
        if token and not public:
            given = request.query_params.get("token") or request.headers.get("x-token") or ""
            if not hmac.compare_digest(given, token):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)

    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (WEB / "index.html").read_text()

    @app.get("/healthz")
    def health():
        return {"ok": True}

    @app.get("/api/state")
    def state(request: Request):
        version, st = request.app.state.engine.snapshot()
        return {"version": version, **st}

    @app.post("/api/advice")
    def advice(request: Request, body: dict = Body(...)):
        try:
            p = profile_from_dict(body)
        except (TypeError, ValueError) as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        _, st = request.app.state.engine.snapshot()
        return advise(p, (st.get("regime") or {}).get("current"), picks_from_state(st))

    @app.post("/api/subscribe")
    def subscribe(request: Request, body: dict = Body(...)):
        if not token:
            return JSONResponse({"error": "set REGIMEML_TOKEN on the server to enable e-mail "
                                          "subscriptions (prevents strangers using it to send mail)"},
                                status_code=403)
        try:
            p = profile_from_dict(body)
            store.upsert(p)
        except (TypeError, ValueError) as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        _, st = request.app.state.engine.snapshot()
        result = {"subscribed": p.email}
        if st.get("regime"):
            from .notify import render, send, smtp_configured
            adv = advise(p, st["regime"]["current"], picks_from_state(st))
            subject, text, body = render(adv, st.get("as_of"), st.get("source", ""))
            if smtp_configured():
                try:
                    send(p.email, subject, text, body)
                    result["first_email"] = "sent"
                except Exception as e:
                    result["first_email"] = f"failed: {e}"
            else:
                result["first_email"] = "SMTP not configured on the server"
        return result

    @app.delete("/api/subscribe")
    def unsubscribe(email: str):
        return {"removed": store.remove(email)}

    @app.get("/api/stream")
    async def stream(request: Request):
        """Server-sent events: pushes the full state whenever it changes."""
        eng = request.app.state.engine

        async def gen():
            seen, idle = -1, 0
            while not await request.is_disconnected():
                version, st = eng.snapshot()
                if version != seen:
                    seen, idle = version, 0
                    yield f"data: {json.dumps({'version': version, **st})}\n\n"
                else:
                    idle += 1
                    if idle % 15 == 0:
                        yield ": keep-alive\n\n"
                await asyncio.sleep(1.0)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return app


app = create_app()
