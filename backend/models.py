from pydantic import BaseModel, Field


class Preferences(BaseModel):
    hilly: int = Field(50, ge=0, le=100, description="0=flat, 100=very hilly")
    offroad: int = Field(50, ge=0, le=100, description="0=paved, 100=offroad/trails")
    repetition: int = Field(0, ge=0, le=100, description="0=no repeats, 100=don't care")
    green: int = Field(50, ge=0, le=100, description="0=don't care, 100=maximize green")


class GenerateRequest(BaseModel):
    start: list[float] = Field(..., min_length=2, max_length=2, description="[lon, lat]")
    distance_m: int = Field(5000, ge=500, le=50000, description="Target distance in meters")
    mode: str = Field("walk", pattern="^(walk|cycle|drive)$")
    preferences: Preferences = Field(default_factory=Preferences)
    algorithm: int = Field(1, ge=1, le=3, description="1=isochrone-polygon, 3=ORS round_trip")
    iterations: int = Field(2, ge=1, le=5)
