from pydantic import BaseModel
from typing import List, Any

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
    email: str
    ring_id: int | None
    actions: list

class WorldState(BaseModel):
    day: int
    zones: list
    workers: list


class ClaimRecord(BaseModel):
    worker_id: int
    email: str
    zone_id: int
    zone_type: str
    income: int
    worker_type: int
    reason: str
    is_fraud: bool
    ring_id: int | None
    day: int
    day_name: str

class FraudRingsResponse(BaseModel):
    total_rings: int
    rings: dict[int, list[int]]

class ClaimsResponse(BaseModel):
    day: int
    day_name: str
    total_claims: int
    legitimate_claims: int
    fraud_claims: int
    claims: List[ClaimRecord]

class WorkerClaimHistoryResponse(BaseModel):
    worker_id: int
    total_claims: int
    fraud_claims: int
    history: List[Any]

class WorkerDecideResponse(BaseModel):
    worker_id: int
    filed_claim: bool
    reason: str | None
    is_fraud: bool


class IssuedPayout(BaseModel):
    worker_id: int
    reason: str

class CompareEntry(BaseModel):
    worker_id: int
    backend_reason: str
    sim_reason: str | None

class CompareResponse(BaseModel):
    day: int
    day_name: str
    submitted: int
    true_positives: int
    false_negatives: int
    false_positives: int
    correct: List[CompareEntry]
    missed: List[CompareEntry] 
    invalid: List[CompareEntry]