import importlib
import json
import re
import sys
from pathlib import Path

import pytest
import responses


# `import server` が常に動作するようにプロジェクトルートを sys.path に追加する
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _reload_module(mod_name: str):
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


@pytest.fixture()
def app_client(monkeypatch):
    # テスト結果が安定するように環境変数を設定する
    monkeypatch.setenv("OSRM_BASE_URL", "https://osrm.test")
    monkeypatch.setenv("RATE_LIMIT_RULE", "2/second")
    monkeypatch.setenv("TIMEOUT_CONNECT", "0.2")
    monkeypatch.setenv("TIMEOUT_READ", "0.2")

    # 環境変数を反映させるために設定とアプリを再読み込みする
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

    # アプリと同じように座標を構築する: [depot] + locations
    coords = [
        (payload["depot"]["lat"], payload["depot"]["lng"])
    ] + [
        (loc["lat"], loc["lng"]) for loc in payload["locations"]
    ]

    # OSRM の table API（距離行列）をモックする
    table_path = oc._coords_to_path(coords)
    table_url = f"{base_url}/table/v1/driving/{table_path}?annotations=distance"

    # 決定的な非対称行列
    dm = [
        [0, 100, 300],
        [120, 0, 200],
        [280, 220, 0],
    ]
    responses.add(responses.GET, table_url, json={"distances": dm}, status=200)

    # 任意の経路に対する OSRM の route ジオメトリをモックする
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
    # total_distance は距離行列上で 0 -> (route+1) -> 0 を辿ったコストと一致するはず
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
    # 緯度の範囲が無効
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

    # 1 件のロケーションだけを持つシンプルなペイロード
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

    # 最初の 2 リクエストは成功する
    assert client.post("/api/optimize", json=payload).status_code == 200
    assert client.post("/api/optimize", json=payload).status_code == 200
    # 同じ時間枠内の 3 回目はレート制限されるはず
    r3 = client.post("/api/optimize", json=payload)
    assert r3.status_code == 429
    assert r3.get_json().get("error") == "RATE_LIMITED"


def test_optimize_zero_locations_returns_400(app_client):
    client = app_client
    payload = _payload(0)
    resp = client.post("/api/optimize", json=payload)
    assert resp.status_code == 400
    # ロケーションが 0 件の場合はバリデーションエラーになるべき
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

    # 非対称だが決定的な 2x2 行列
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
    # total は 0->1 + 1->0 = 7 + 3 に等しいはず
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

    # 単純な決定的距離行列を構築する: cost = |i - j| * 10
    n = len(coords)
    dm = [[0 if i == j else abs(i - j) * 10 for j in range(n)] for i in range(n)]
    responses.add(responses.GET, table_url, json={"distances": dm}, status=200)

    # 11 本のレグ（10 ロケーション + デポへの戻り）を返す
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
    # MAX_LOCATIONS を超えると Pydantic のバリデーションエラーになる想定
    assert resp.get_json().get("error") == "VALIDATION_ERROR"
