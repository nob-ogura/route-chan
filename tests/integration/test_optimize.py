import importlib
import json
import re
import sys
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
    # Configure environment for predictable tests
    monkeypatch.setenv("OSRM_BASE_URL", "https://osrm.test")
    monkeypatch.setenv("RATE_LIMIT_RULE", "2/second")
    monkeypatch.setenv("TIMEOUT_CONNECT", "0.2")
    monkeypatch.setenv("TIMEOUT_READ", "0.2")

    # Reload config and app to apply env
    _reload_module("server.config")
    app_mod = _reload_module("server.app")
    app = app_mod.app
    app.testing = True
    client = app.test_client()
    return client


def _payload(n_locations: int):
    depot = {"lat": 35.0, "lng": 135.0}
    locations = [
        {"lat": 35.0 + i * 0.01, "lng": 135.0 + i * 0.01} for i in range(n_locations)
    ]
    return {"depot": depot, "locations": locations}


def _tour_cost(dm, order):
    total = 0
    for i in range(len(order) - 1):
        total += int(dm[order[i]][order[i + 1]])
    return total


@responses.activate
def test_optimize_success_two_locations(app_client):
    import server.osrm_client as oc

    client = app_client
    base_url = "https://osrm.test"

    payload = _payload(2)

    # Build coords as app does: [depot] + locations
    coords = [
        (payload["depot"]["lat"], payload["depot"]["lng"])
    ] + [
        (loc["lat"], loc["lng"]) for loc in payload["locations"]
    ]

    # Mock OSRM table (distance matrix)
    table_path = oc._coords_to_path(coords)
    table_url = f"{base_url}/table/v1/driving/{table_path}?annotations=distance"

    # Deterministic asymmetric matrix
    dm = [
        [0, 100, 300],
        [120, 0, 200],
        [280, 220, 0],
    ]
    responses.add(responses.GET, table_url, json={"distances": dm}, status=200)

    # Mock OSRM route geometry for any path
    route_re = re.compile(
        r"^https://osrm\.test/route/v1/driving/.+\?overview=full&geometries=polyline6$"
    )
    responses.add(
        responses.GET,
        route_re,
        json={"routes": [{"legs": [{"geometry": "poly0"}, {"geometry": "poly1"}, {"geometry": "poly2"}]}]},
        status=200,
    )

    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data["route"]) == {0, 1}
    # total_distance should equal cost along 0 -> (route+1) -> 0 on dm
    tour_nodes = [0] + [r + 1 for r in data["route"]] + [0]
    assert data["total_distance"] == _tour_cost(dm, tour_nodes)
    assert data["route_geometries"] == ["poly0", "poly1", "poly2"]


def test_optimize_bad_json_returns_400(app_client):
    client = app_client
    resp = client.post(
        "/api/optimize", data="not-json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("error") == "BAD_REQUEST"


def test_optimize_validation_error_returns_400(app_client):
    client = app_client
    # invalid lat range
    payload = _payload(1)
    payload["depot"]["lat"] = 123.456
    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 400
    assert resp.get_json().get("error") == "VALIDATION_ERROR"


@responses.activate
def test_optimize_osrm_table_failure_returns_502(app_client):
    import server.osrm_client as oc

    client = app_client
    base_url = "https://osrm.test"
    payload = _payload(1)
    coords = [
        (payload["depot"]["lat"], payload["depot"]["lng"])
    ] + [
        (loc["lat"], loc["lng"]) for loc in payload["locations"]
    ]
    table_path = oc._coords_to_path(coords)
    table_url = f"{base_url}/table/v1/driving/{table_path}?annotations=distance"
    responses.add(responses.GET, table_url, status=503)

    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 502
    assert resp.get_json().get("error") == "OSRM_TABLE_FAILED"


@responses.activate
def test_optimize_osrm_route_failure_returns_502(app_client):
    import server.osrm_client as oc

    client = app_client
    base_url = "https://osrm.test"
    payload = _payload(1)
    coords = [
        (payload["depot"]["lat"], payload["depot"]["lng"])
    ] + [
        (loc["lat"], loc["lng"]) for loc in payload["locations"]
    ]
    table_path = oc._coords_to_path(coords)
    table_url = f"{base_url}/table/v1/driving/{table_path}?annotations=distance"
    dm = [
        [0, 10],
        [20, 0],
    ]
    responses.add(responses.GET, table_url, json={"distances": dm}, status=200)

    route_re = re.compile(
        r"^https://osrm\.test/route/v1/driving/.+\?overview=full&geometries=polyline6$"
    )
    responses.add(responses.GET, route_re, status=500)

    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 502
    assert resp.get_json().get("error") == "OSRM_ROUTE_FAILED"


@responses.activate
def test_optimize_rate_limited_returns_429(app_client, monkeypatch):
    import server.osrm_client as oc

    client = app_client
    base_url = "https://osrm.test"

    # Simple payload with one location
    payload = _payload(1)
    coords = [
        (payload["depot"]["lat"], payload["depot"]["lng"])
    ] + [
        (loc["lat"], loc["lng"]) for loc in payload["locations"]
    ]
    table_url = f"{base_url}/table/v1/driving/{oc._coords_to_path(coords)}?annotations=distance"
    responses.add(responses.GET, table_url, json={"distances": [[0, 1], [2, 0]]}, status=200)

    route_re = re.compile(r"^https://osrm\.test/route/v1/driving/.+\?overview=full&geometries=polyline6$")
    responses.add(
        responses.GET,
        route_re,
        json={"routes": [{"legs": [{"geometry": "p0"}, {"geometry": "p1"}]}]},
        status=200,
    )

    # First two requests succeed
    assert client.post("/api/optimize", json=payload).status_code == 200
    assert client.post("/api/optimize", json=payload).status_code == 200
    # Third request within window should be rate-limited
    r3 = client.post("/api/optimize", json=payload)
    assert r3.status_code == 429
    assert r3.get_json().get("error") == "RATE_LIMITED"


def test_optimize_zero_locations_returns_400(app_client):
    client = app_client
    payload = _payload(0)
    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 400
    # Validation error should be returned for 0 locations
    assert resp.get_json().get("error") == "VALIDATION_ERROR"


@responses.activate
def test_optimize_one_location_success(app_client):
    import server.osrm_client as oc

    client = app_client
    base_url = "https://osrm.test"

    payload = _payload(1)
    coords = [
        (payload["depot"]["lat"], payload["depot"]["lng"])
    ] + [
        (loc["lat"], loc["lng"]) for loc in payload["locations"]
    ]
    table_url = f"{base_url}/table/v1/driving/{oc._coords_to_path(coords)}?annotations=distance"

    # Asymmetric but deterministic 2x2 matrix
    dm = [
        [0, 7],
        [3, 0],
    ]
    responses.add(responses.GET, table_url, json={"distances": dm}, status=200)

    route_re = re.compile(r"^https://osrm\.test/route/v1/driving/.+\?overview=full&geometries=polyline6$")
    responses.add(
        responses.GET,
        route_re,
        json={"routes": [{"legs": [{"geometry": "g0"}, {"geometry": "g1"}]}]},
        status=200,
    )

    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["route"] in ([0],)
    # total should equal 0->1 + 1->0 = 7 + 3
    assert data["total_distance"] == _tour_cost(dm, [0, 1, 0])
    assert data["route_geometries"] == ["g0", "g1"]


@responses.activate
def test_optimize_ten_locations_success(app_client):
    import server.osrm_client as oc

    client = app_client
    base_url = "https://osrm.test"

    payload = _payload(10)
    coords = [
        (payload["depot"]["lat"], payload["depot"]["lng"])
    ] + [
        (loc["lat"], loc["lng"]) for loc in payload["locations"]
    ]
    table_url = f"{base_url}/table/v1/driving/{oc._coords_to_path(coords)}?annotations=distance"

    # Construct a simple deterministic distance matrix: cost = |i - j| * 10
    n = len(coords)
    dm = [[0 if i == j else abs(i - j) * 10 for j in range(n)] for i in range(n)]
    responses.add(responses.GET, table_url, json={"distances": dm}, status=200)

    # Return 11 legs (10 locations + return to depot)
    route_re = re.compile(r"^https://osrm\.test/route/v1/driving/.+\?overview=full&geometries=polyline6$")
    legs = [{"geometry": f"L{i}"} for i in range(11)]
    responses.add(responses.GET, route_re, json={"routes": [{"legs": legs}]}, status=200)

    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data.keys()) >= {"route", "total_distance", "route_geometries"}
    assert len(data["route"]) == 10
    assert len(data["route_geometries"]) == 11


def test_optimize_eleven_locations_returns_400(app_client):
    client = app_client
    payload = _payload(11)
    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 400
    # Pydantic validation error is expected for > MAX_LOCATIONS
    assert resp.get_json().get("error") == "VALIDATION_ERROR"
