import re

import pytest
import responses
import requests


def _import_client():
    # 実装前のインポート時エラーを避けるためローカルにインポートする
    import importlib
    return importlib.import_module("server.osrm_client")


def test_coords_to_path_formatting():
    client = _import_client()
    coords = [
        (35.0, 135.0),  # 緯度・経度
        (35.1, 135.2),
        (-10.5, 0.25),
    ]
    path = client._coords_to_path(coords)
    assert path == "135.0,35.0;135.2,35.1;0.25,-10.5"


@responses.activate
def test_get_distance_matrix_success():
    client = _import_client()
    base_url = "https://osrm.test"
    coords = [(35.0, 135.0), (35.1, 135.1)]
    path = "135.0,35.0;135.1,35.1"
    url = f"{base_url}/table/v1/driving/{path}?annotations=distance"

    responses.add(
        responses.GET,
        url,
        json={"distances": [[0, 1000], [1000, 0]]},
        status=200,
    )

    dm = client.get_distance_matrix(base_url, coords, (1.0, 2.0))
    assert dm == [[0, 1000], [1000, 0]]


@responses.activate
def test_get_distance_matrix_missing_key_raises():
    client = _import_client()
    base_url = "https://osrm.test"
    coords = [(35.0, 135.0), (35.1, 135.1)]
    path = "135.0,35.0;135.1,35.1"
    url = f"{base_url}/table/v1/driving/{path}?annotations=distance"

    responses.add(
        responses.GET,
        url,
        json={},
        status=200,
    )

    with pytest.raises(Exception) as ei:
        client.get_distance_matrix(base_url, coords, (1.0, 2.0))
    assert "distances" in str(ei.value)


@responses.activate
def test_get_distance_matrix_http_error_raises():
    client = _import_client()
    base_url = "https://osrm.test"
    coords = [(35.0, 135.0), (35.1, 135.1)]
    path = "135.0,35.0;135.1,35.1"
    url = f"{base_url}/table/v1/driving/{path}?annotations=distance"

    responses.add(
        responses.GET,
        url,
        status=503,
        json={"message": "service unavailable"},
    )

    with pytest.raises(Exception) as ei:
        client.get_distance_matrix(base_url, coords, (1.0, 2.0))
    assert "OSRM table request failed" in str(ei.value)


@responses.activate
def test_get_distance_matrix_timeout_raises():
    client = _import_client()
    base_url = "https://osrm.test"
    coords = [(35.0, 135.0), (35.1, 135.1)]
    path = "135.0,35.0;135.1,35.1"
    url = f"{base_url}/table/v1/driving/{path}?annotations=distance"

    responses.add(
        responses.GET,
        url,
        body=requests.exceptions.Timeout("timed out"),
    )

    with pytest.raises(Exception) as ei:
        client.get_distance_matrix(base_url, coords, (0.1, 0.2))
    assert "OSRM table request failed" in str(ei.value)


@responses.activate
def test_get_route_geometries_success():
    client = _import_client()
    base_url = "https://osrm.test"
    coords = [(35.0, 135.0), (35.1, 135.1), (35.2, 135.2)]
    path = "135.0,35.0;135.1,35.1;135.2,35.2"
    url = f"{base_url}/route/v1/driving/{path}?overview=full&geometries=polyline6"

    responses.add(
        responses.GET,
        url,
        json={
            "routes": [
                {
                    "legs": [
                        {"geometry": "polyA"},
                        {"geometry": "polyB"},
                    ]
                }
            ]
        },
        status=200,
    )

    legs = client.get_route_geometries(base_url, coords, (1.0, 2.0))
    assert legs == ["polyA", "polyB"]


@responses.activate
def test_get_route_geometries_missing_routes_raises():
    client = _import_client()
    base_url = "https://osrm.test"
    coords = [(35.0, 135.0), (35.1, 135.1)]
    path = "135.0,35.0;135.1,35.1"
    url = f"{base_url}/route/v1/driving/{path}?overview=full&geometries=polyline6"

    responses.add(
        responses.GET,
        url,
        json={},
        status=200,
    )

    with pytest.raises(Exception) as ei:
        client.get_route_geometries(base_url, coords, (1.0, 2.0))
    assert "OSRM route response missing 'routes'" in str(ei.value)


@responses.activate
def test_get_route_geometries_http_error_raises():
    client = _import_client()
    base_url = "https://osrm.test"
    coords = [(35.0, 135.0), (35.1, 135.1)]
    path = "135.0,35.0;135.1,35.1"
    url = f"{base_url}/route/v1/driving/{path}?overview=full&geometries=polyline6"

    responses.add(
        responses.GET,
        url,
        status=500,
    )

    with pytest.raises(Exception) as ei:
        client.get_route_geometries(base_url, coords, (1.0, 2.0))
    assert "OSRM route request failed" in str(ei.value)
