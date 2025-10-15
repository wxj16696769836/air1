from pydantic import BaseModel, Field
from typing import Optional, List


class FetchConfig(BaseModel):
    city: Optional[str] = Field(None, description="City name for OpenAQ queries")
    country: Optional[str] = Field(None, description="Country code (ISO2)")
    bbox: Optional[List[float]] = Field(None, description="[minLon, minLat, maxLon, maxLat]")
    start: Optional[str] = Field(None, description="ISO8601 start datetime")
    end: Optional[str] = Field(None, description="ISO8601 end datetime")
    parameters: List[str] = Field(default_factory=lambda: ["pm25", "so2", "no2"])
    limit: int = 10000
    api_key: Optional[str] = Field(None, description="OpenAQ v3 API key for authenticated requests")


class Thresholds(BaseModel):
    pm25: float = 150.0
    so2: float = 350.0
    no2: float = 200.0


class Paths(BaseModel):
    data_dir: str = "data"
    outputs_dir: str = "outputs"
    maps_dir: str = "outputs/maps"
    plots_dir: str = "outputs/plots"
    alerts_dir: str = "outputs/alerts"
