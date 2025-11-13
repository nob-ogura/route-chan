import importlib
import sys
from pathlib import Path

# `import server` が動作するようにプロジェクトルートを sys.path に追加する
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import math


def _import_solver():
    # 実装前のインポート時エラーを避けるためローカルにインポートする
    return importlib.import_module("server.solver")


def _tour_cost(dm, order):
    # order はグラフのノード番号（デポを開始/終了に含む）
    total = 0
    for i in range(len(order) - 1):
        total += int(dm[order[i]][order[i + 1]])
    return total


def test_solve_simple_triangle():
    solver = _import_solver()
    # ノード: 0=デポ、1,2=ロケーション
    dm = [
        [0, 1, 1],
        [1, 0, 2],
        [1, 2, 0],
    ]
    route, total = solver.solve_tsp_distance_matrix(dm, time_limit_ms=500)

    # 戻り値はロケーション配列に対するインデックス（0 始まり）
    assert set(route) == {0, 1}

    # total が 0 -> (route+1) -> 0 の巡回コストと等しいことを検証する
    tour_nodes = [0] + [r + 1 for r in route] + [0]
    assert total == _tour_cost(dm, tour_nodes)


def test_solve_single_location():
    solver = _import_solver()
    # ノード: 0=デポ、1=ロケーション
    dm = [
        [0, 7],
        [3, 0],  # 非対称でも許容
    ]
    route, total = solver.solve_tsp_distance_matrix(dm, time_limit_ms=200)

    assert route in ([0],)  # ロケーションは 1 件だけ
    tour_nodes = [0, 1, 0]
    assert total == _tour_cost(dm, tour_nodes)


def test_solve_degenerate_only_depot():
    solver = _import_solver()
    # デポのみが存在する
    dm = [[0]]
    route, total = solver.solve_tsp_distance_matrix(dm, time_limit_ms=100)
    assert route == []
    assert total == 0
