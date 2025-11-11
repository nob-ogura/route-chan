import importlib
import sys
import os

import pytest
from pydantic import ValidationError


ENV_KEYS = [
    "OSRM_BASE_URL",
    "MAX_LOCATIONS",
    "TIMEOUT_CONNECT",
    "TIMEOUT_READ",
    "RATE_LIMIT_RULE",
    "SOLVER_TIME_LIMIT_MS",
]


def _reload_module(mod_name: str):
    if mod_name in sys.modules:
        return importlib.reload(sys.modules[mod_name])
    return importlib.import_module(mod_name)


def _reload_config(monkeypatch, env: dict | None = None):
    for k in ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    if env:
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
    # Reload config (reads environment at import time)
    config = _reload_module("server.config")
    return config


def test_config_defaults(monkeypatch):
    config = _reload_config(monkeypatch)
    assert config.Config.OSRM_BASE_URL == "https://router.project-osrm.org"
    assert config.Config.MAX_LOCATIONS == 10
    assert config.Config.TIMEOUT_CONNECT == 3.0
    assert config.Config.TIMEOUT_READ == 5.0
    assert config.Config.RATE_LIMIT_RULE == "60/minute"
    assert config.Config.SOLVER_TIME_LIMIT_MS == 3000


def test_config_env_override(monkeypatch):
    cfg = _reload_config(
        monkeypatch,
        env={
            "OSRM_BASE_URL": "https://example.com",
            "MAX_LOCATIONS": "7",
            "TIMEOUT_CONNECT": "1.5",
            "TIMEOUT_READ": "2.5",
            "RATE_LIMIT_RULE": "10/second",
            "SOLVER_TIME_LIMIT_MS": "1234",
        },
    )

    assert cfg.Config.OSRM_BASE_URL == "https://example.com"
    assert cfg.Config.MAX_LOCATIONS == 7
    assert cfg.Config.TIMEOUT_CONNECT == 1.5
    assert cfg.Config.TIMEOUT_READ == 2.5
    assert cfg.Config.RATE_LIMIT_RULE == "10/second"
    assert cfg.Config.SOLVER_TIME_LIMIT_MS == 1234


def test_latlng_validation(monkeypatch):
    _reload_config(monkeypatch)
    schemas = _reload_module("server.schemas")

    # Boundary OK
    schemas.LatLng(lat=90, lng=180)
    schemas.LatLng(lat=-90, lng=-180)

    # Out of range raises
    with pytest.raises(ValidationError):
        schemas.LatLng(lat=90.0001, lng=0)
    with pytest.raises(ValidationError):
        schemas.LatLng(lat=0, lng=180.0001)


def test_optimize_request_locations_count_limits(monkeypatch):
    # Set MAX_LOCATIONS=3 and reload both config and schemas
    _reload_config(monkeypatch, env={"MAX_LOCATIONS": "3"})
    schemas = _reload_module("server.schemas")

    depot = schemas.LatLng(lat=35.0, lng=135.0)
    loc = lambda n: [schemas.LatLng(lat=35.0 + i * 0.01, lng=135.0) for i in range(n)]

    # 0 locations -> invalid
    with pytest.raises(ValidationError):
        schemas.OptimizeRequest(depot=depot, locations=loc(0))

    # 1..3 locations -> valid
    for n in (1, 2, 3):
        schemas.OptimizeRequest(depot=depot, locations=loc(n))

    # 4 locations -> invalid over MAX_LOCATIONS
    with pytest.raises(ValidationError):
        schemas.OptimizeRequest(depot=depot, locations=loc(4))

