import pytest
from fastapi.testclient import TestClient

from regimeml.engine import Engine, EngineConfig, ReplaySource
from regimeml.model import ModelConfig


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import os
    os.environ["REGIMEML_TOKEN"] = "t0k"
    os.environ["REGIMEML_PROFILES"] = str(tmp_path_factory.mktemp("s") / "subs.json")
    from regimeml.server import create_app
    eng = Engine(ReplaySource(n_assets=10, n_days=900, start=700, seed=5),
                 EngineConfig(model=ModelConfig(max_iter=30), retrain_every=1000))
    for _ in range(8):
        eng.step()
    with TestClient(create_app(eng, start_engine=False)) as c:
        yield c
    del os.environ["REGIMEML_TOKEN"]


def test_auth_and_public_routes(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/chart.umd.js").status_code == 200
    assert client.get("/api/state").status_code == 401
    s = client.get("/api/state?token=t0k").json()
    assert s["regime"]["labels"] == ["calm", "stressed", "crisis"] and s["portfolio"]


def test_advice_and_subscribe(client):
    body = {"age": 40, "net_worth": 300000, "investable": 100000, "goal": "retirement", "email": "a@b.co"}
    a = client.post("/api/advice?token=t0k", json=body).json()
    assert abs(sum(a["action"]["target"].values()) - 1) < 1e-9 and "email" not in a["profile"]
    assert client.post("/api/advice?token=t0k", json={**body, "age": 5}).status_code == 400
    r = client.post("/api/subscribe?token=t0k", json=body).json()
    assert r["subscribed"] == "a@b.co" and "SMTP not configured" in r["first_email"]
    assert client.delete("/api/subscribe?token=t0k&email=a@b.co").json() == {"removed": True}
