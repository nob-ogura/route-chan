import os


class Config:
    OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
    MAX_LOCATIONS = int(os.getenv("MAX_LOCATIONS", "10"))
    TIMEOUT_CONNECT = float(os.getenv("TIMEOUT_CONNECT", "3.0"))
    TIMEOUT_READ = float(os.getenv("TIMEOUT_READ", "5.0"))
    RATE_LIMIT_RULE = os.getenv("RATE_LIMIT_RULE", "60/minute")
    SOLVER_TIME_LIMIT_MS = int(os.getenv("SOLVER_TIME_LIMIT_MS", "3000"))

