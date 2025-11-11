import importlib
import sys
from pathlib import Path

# Ensure project root is on sys.path so that `import server` works
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import math


def _import_solver():
    # Local import to avoid import-time errors before implementation
    return importlib.import_module("server.solver")


def _tour_cost(dm, order):
    # order is node indices in the graph (including depot at start/end)
    total = 0
    for i in range(len(order) - 1):
        total += int(dm[order[i]][order[i + 1]])
    return total


def test_solve_simple_triangle():
    solver = _import_solver()
    # Nodes: 0=depot, 1,2=locations
    dm = [
        [0, 1, 1],
        [1, 0, 2],
        [1, 2, 0],
    ]
    route, total = solver.solve_tsp_distance_matrix(dm, time_limit_ms=500)

    # Returns indices into locations (0-based for locations array)
    assert set(route) == {0, 1}

    # Validate the reported total equals the tour cost 0 -> (route+1) -> 0
    tour_nodes = [0] + [r + 1 for r in route] + [0]
    assert total == _tour_cost(dm, tour_nodes)


def test_solve_single_location():
    solver = _import_solver()
    # Nodes: 0=depot, 1=location
    dm = [
        [0, 7],
        [3, 0],  # asymmetric allowed
    ]
    route, total = solver.solve_tsp_distance_matrix(dm, time_limit_ms=200)

    assert route in ([0],)  # only one location
    tour_nodes = [0, 1, 0]
    assert total == _tour_cost(dm, tour_nodes)


def test_solve_degenerate_only_depot():
    solver = _import_solver()
    # Only depot exists
    dm = [[0]]
    route, total = solver.solve_tsp_distance_matrix(dm, time_limit_ms=100)
    assert route == []
    assert total == 0
