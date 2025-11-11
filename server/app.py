import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .config import Config
from .schemas import OptimizeRequest
from .osrm_client import (
    get_distance_matrix,
    get_route_geometries,
    OsrmError,
)
from .solver import solve_tsp_distance_matrix


app = Flask(__name__)
origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in origins_env.split(",")] if origins_env else "*"
CORS(app, resources={r"/api/*": {"origins": origins}})
limiter = Limiter(get_remote_address, app=app, default_limits=[Config.RATE_LIMIT_RULE])


@app.get("/api/health")
def health():
    return jsonify(status="ok"), 200


@app.post("/api/optimize")
def optimize():
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return (
            jsonify(error="BAD_REQUEST", message="JSON ボディを解析できませんでした"),
            400,
        )

    try:
        req = OptimizeRequest(**payload)
    except Exception as e:
        return jsonify(error="VALIDATION_ERROR", message=str(e)), 400

    # Redundant but explicit guard per spec
    if not (1 <= len(req.locations) <= Config.MAX_LOCATIONS):
        return (
            jsonify(
                error="INVALID_LOCATION_COUNT",
                message=f"訪問地点は1から{Config.MAX_LOCATIONS}の間で設定してください。",
            ),
            400,
        )

    coords = [(req.depot.lat, req.depot.lng)] + [
        (loc.lat, loc.lng) for loc in req.locations
    ]

    try:
        dm = get_distance_matrix(
            Config.OSRM_BASE_URL, coords, (Config.TIMEOUT_CONNECT, Config.TIMEOUT_READ)
        )
    except OsrmError as e:
        return jsonify(error="OSRM_TABLE_FAILED", message=str(e)), 502

    route, total = solve_tsp_distance_matrix(
        dm, time_limit_ms=Config.SOLVER_TIME_LIMIT_MS
    )

    ordered = [coords[0]] + [coords[i + 1] for i in route] + [coords[0]]
    try:
        legs = get_route_geometries(
            Config.OSRM_BASE_URL,
            ordered,
            (Config.TIMEOUT_CONNECT, Config.TIMEOUT_READ),
        )
    except OsrmError as e:
        return jsonify(error="OSRM_ROUTE_FAILED", message=str(e)), 502

    return (
        jsonify(route=route, total_distance=total, route_geometries=legs),
        200,
    )


@app.errorhandler(429)
def ratelimit_handler(e):
    return (
        jsonify(error="RATE_LIMITED", message="しばらく待ってから再試行してください。"),
        429,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
