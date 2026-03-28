from pydantic import BaseModel

class MessageResponse(BaseModel):
    message: str

class DaySummary(BaseModel):
    lockdown: int
    stable: int
    other_civil: int
    weather_disaster: int
    weather_clear: int
    other_weather: int

class DaySummaryResponse(BaseModel):
    message: str
    day_summary: DaySummary

class WeatherAlertsResponse(BaseModel):
    weather_alerts: list

class GovernmentAlertsResponse(BaseModel):
    government_alerts: list

class ZoneState(BaseModel):
    id: int
    type: str
    nearby_zones: dict
    civil_state: str
    weather_state: str
    event_info: str

class WorkerState(BaseModel):
    id: int
    zone_id: int
    type: int
    income: int

class WorldState(BaseModel):
    day: int
    zones: list
    workers: list