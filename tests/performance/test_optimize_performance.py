import importlib
import re
import sys
import time
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
    # パフォーマンステストのためにリミットとタイムアウトを厳格かつ決定的に保つ
    monkeypatch.setenv("OSRM_BASE_URL", "https://osrm.test")
    monkeypatch.setenv("RATE_LIMIT_RULE", "100/second")  # レートリミッターの干渉を避ける
    monkeypatch.setenv("TIMEOUT_CONNECT", "0.5")
    monkeypatch.setenv("TIMEOUT_READ", "0.5")
    # ソルバーに妥当な上限を設定し、通常ケースではさらに早く終わるようにする
    # 仕様通りエンドツーエンド 3 秒未満を維持し、余裕を持たせる
    monkeypatch.setenv("SOLVER_TIME_LIMIT_MS", "2500")

    # 環境変数を反映させるために設定とアプリを再読み込みする
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
    """エンドツーエンド性能: 10 件のロケーションが約 3 秒以内に完了することを確認する。

    再現性を保つため OSRM への HTTP 呼び出しはモックするが、
    リクエストのパース、距離行列の利用、OR-Tools の解法、
    経路ジオメトリの生成、JSON シリアライズまでアプリの処理全体を測定する。
    """
    import server.osrm_client as oc

    client = app_client
    base_url = "https://osrm.test"
    payload = _payload(10)

    # アプリと同じ手順で座標を組み立てる: [depot] + locations
    coords = [(payload["depot"]["lat"], payload["depot"]["lng"])]
    coords += [(loc["lat"], loc["lng"]) for loc in payload["locations"]]

    # 単純で決定的な行列を使って OSRM の table API をモックする
    table_path = oc._coords_to_path(coords)
    table_url = f"{base_url}/table/v1/driving/{table_path}?annotations=distance"
    n = len(coords)
    dm = [[0 if i == j else abs(i - j) * 10 for j in range(n)] for i in range(n)]
    responses.add(responses.GET, table_url, json={"distances": dm}, status=200)

    # 11 本のレグ（10 ロケーション訪問 + デポ帰還）で OSRM の route API をモックする
    route_re = re.compile(
        r"^https://osrm\.test/route/v1/driving/.+\?overview=full&geometries=polyline6$"
    )
    legs = [{"geometry": f"L{i}"} for i in range(11)]
    responses.add(responses.GET, route_re, json={"routes": [{"legs": legs}]}, status=200)

    # ドキュメント推奨どおり 1 回ウォームアップして初期化コストを避ける
    _ = client.post("/api/optimize", json=payload)

    c_before = len(responses.calls)
    t0 = time.perf_counter()
    resp = client.post("/api/optimize", json=payload)
    elapsed = time.perf_counter() - t0

    # 基本的な正しさを検証する
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data.keys()) >= {"route", "total_distance", "route_geometries"}
    assert len(data["route"]) == 10
    assert len(data["route_geometries"]) == 11

    # 仕様上の性能目標: 約 3 秒以内
    assert elapsed < 3.0, f"optimize took {elapsed:.3f}s, exceeds 3s target"

    # 計測対象リクエスト中に最小限の OSRM 呼び出ししか行われていないことを確認する
    assert len(responses.calls) - c_before == 2
