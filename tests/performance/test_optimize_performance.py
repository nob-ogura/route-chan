import importlib
import re
import sys
import time
from pathlib import Path

import pytest
import responses


# Ensure project root is on sys.path so that `import server` works reliably
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _reload_module(mod_name: str):
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


@pytest.fixture()
def app_client(monkeypatch):
    # Keep limits and timeouts tight and deterministic for performance test
    monkeypatch.setenv("OSRM_BASE_URL", "https://osrm.test")
    monkeypatch.setenv("RATE_LIMIT_RULE", "100/second")  # avoid limiter interference
    monkeypatch.setenv("TIMEOUT_CONNECT", "0.5")
    monkeypatch.setenv("TIMEOUT_READ", "0.5")
    # Ensure solver has a sane upper bound; typical cases finish far faster
    # Keep under 3s end-to-end per spec; leave headroom
    monkeypatch.setenv("SOLVER_TIME_LIMIT_MS", "2500")

    # Reload config and app to apply env
    _reload_module("server.config")
    app_mod = _reload_module("server.app")
    app = app_mod.app
    app.testing = True
    return app.test_client()


def _payload(n_locations: int):
    depot = {"lat": 35.681236, "lng": 139.767125}
    locations = [
        {"lat": depot["lat"] + i * 0.01, "lng": depot["lng"] + i * 0.01}
        for i in range(n_locations)
    ]
    return {"depot": depot, "locations": locations}


@responses.activate
def test_optimize_ten_locations_under_3s(app_client):
    """End-to-end performance: ensure 10 locations complete under ~3s.

    OSRM HTTP calls are mocked for determinism; we still measure the app's
    full processing including request parsing, distance matrix use, OR-Tools
    solve, route geometry assembly, and JSON serialization.
    """
    import server.osrm_client as oc

    client = app_client
    base_url = "https://osrm.test"
    payload = _payload(10)

    # Coords as the app builds them: [depot] + locations
    coords = [(payload["depot"]["lat"], payload["depot"]["lng"])]
    coords += [(loc["lat"], loc["lng"]) for loc in payload["locations"]]

    # Mock OSRM table with a simple deterministic matrix
    table_path = oc._coords_to_path(coords)
    table_url = f"{base_url}/table/v1/driving/{table_path}?annotations=distance"
    n = len(coords)
    dm = [[0 if i == j else abs(i - j) * 10 for j in range(n)] for i in range(n)]
    responses.add(responses.GET, table_url, json={"distances": dm}, status=200)

    # Mock OSRM route with 11 legs (visit 10 locations and return to depot)
    route_re = re.compile(
        r"^https://osrm\.test/route/v1/driving/.+\?overview=full&geometries=polyline6$"
    )
    legs = [{"geometry": f"L{i}"} for i in range(11)]
    responses.add(responses.GET, route_re, json={"routes": [{"legs": legs}]}, status=200)

    # Warm-up once (per docs recommendation) to avoid one-time init costs
    _ = client.post("/api/optimize", json=payload)

    c_before = len(responses.calls)
    t0 = time.perf_counter()
    resp = client.post("/api/optimize", json=payload)
    elapsed = time.perf_counter() - t0

    # Basic correctness
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data.keys()) >= {"route", "total_distance", "route_geometries"}
    assert len(data["route"]) == 10
    assert len(data["route_geometries"]) == 11

    # Performance target per spec: within ~3 seconds
    assert elapsed < 3.0, f"optimize took {elapsed:.3f}s, exceeds 3s target"

    # Ensure only the minimal OSRM calls are made during the measured request
    assert len(responses.calls) - c_before == 2
