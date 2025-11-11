from typing import List

from pydantic import BaseModel, Field

try:
    # Pydantic v2
    from pydantic import field_validator as validator  # type: ignore
except Exception:  # pragma: no cover - fallback for v1
    # Pydantic v1
    from pydantic import validator  # type: ignore

from .config import Config


class LatLng(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class OptimizeRequest(BaseModel):
    depot: LatLng
    locations: List[LatLng]

    @validator("locations")
    def check_locations(cls, v: List[LatLng]):
        if not (1 <= len(v) <= Config.MAX_LOCATIONS):
            raise ValueError(
                f"訪問地点は1から{Config.MAX_LOCATIONS}の間で設定してください"
            )
        return v


class OptimizeResponse(BaseModel):
    route: List[int]
    total_distance: int
    route_geometries: List[str]

