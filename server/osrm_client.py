from typing import List, Tuple

import requests


class OsrmError(Exception):
    pass


def _coords_to_path(coords: List[Tuple[float, float]]) -> str:
    # OSRM expects: lon,lat;lon,lat;...
    return ";".join([f"{lng},{lat}" for lat, lng in coords])


def get_distance_matrix(
    base_url: str, coords: List[Tuple[float, float]], timeout: tuple[float, float]
) -> List[List[int]]:
    path = _coords_to_path(coords)
    url = f"{base_url}/table/v1/driving/{path}?annotations=distance"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise OsrmError(f"OSRM table request failed: {e}")
    data = resp.json()
    if "distances" not in data:
        raise OsrmError("OSRM table response missing 'distances'")
    return data["distances"]


def get_route_geometries(
    base_url: str, coords: List[Tuple[float, float]], timeout: tuple[float, float]
) -> List[str]:
    path = _coords_to_path(coords)
    url = f"{base_url}/route/v1/driving/{path}?overview=full&geometries=polyline6"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise OsrmError(f"OSRM route request failed: {e}")
    data = resp.json()
    if "routes" not in data or not data["routes"]:
        raise OsrmError("OSRM route response missing 'routes'")
    legs = data["routes"][0].get("legs", [])
    return [leg.get("geometry", "") for leg in legs]

