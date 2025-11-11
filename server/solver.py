from typing import List, Tuple

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def solve_tsp_distance_matrix(
    distance_matrix: List[List[int]], time_limit_ms: int = 3000
) -> tuple[List[int], int]:
    """
    Solve a single-vehicle TSP with a fixed depot at node 0.

    Returns a tuple of:
    - route: visit order as indices into the `locations` array (0-based),
             i.e., OR-Tools nodes 1..N mapped to 0..N-1
    - total_distance: total travel cost along 0 -> route -> 0
    """
    n = len(distance_matrix)
    if n == 0:
        return [], 0

    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.FromMilliseconds(int(time_limit_ms))

    solution = routing.SolveWithParameters(search_params)
    if not solution:
        return [], 0

    # Extract route excluding depot. Map nodes 1..N -> locations indices 0..N-1
    index = routing.Start(0)
    order: List[int] = []
    route_distance = 0
    while not routing.IsEnd(index):
        next_index = solution.Value(routing.NextVar(index))
        from_node = manager.IndexToNode(index)
        to_node = manager.IndexToNode(next_index)
        route_distance += routing.GetArcCostForVehicle(index, next_index, 0)
        if to_node != 0:
            order.append(to_node - 1)
        index = next_index

    return order, int(route_distance)

