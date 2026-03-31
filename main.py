from classes.world import World
from classes.models import *
import logging
from fastapi import FastAPI, HTTPException
from typing import List
import json

logging.basicConfig(level=logging.INFO)

config = json.load(open("config.json", "r"))

assert config["MIN_ZONE_CONNECTIONS"] < config["N_ZONES"], "Minimum connections must be less than total zones"
assert config["MAX_ZONE_CONNECTIONS"] < config["N_ZONES"], "Maximum connections must be less than total zones"
assert config["MIN_ZONE_CONNECTIONS"] <= config["MAX_ZONE_CONNECTIONS"], "Minimum connections must be less than or equal to maximum connections"

app = FastAPI(
    title="InsureOnSim API",
    description="Parametric insurance simulation engine for InsureOn — Guidewire DevTrails.",
    version="1.0.0",
)

world: World | None = None



def _zone_state(zone) -> ZoneState:
    return ZoneState(
        id=zone.id,
        type=zone.type,
        nearby_zones=zone.nearby_zones,
        civil_state=zone.civil_state,
        weather_state=zone.weather,
        event_info=zone.event_info,
    )


def _worker_state(worker) -> WorkerState:
    return WorkerState(
        id=worker.id,
        zone_id=worker.zone.id,
        type=worker.type,
        income=worker.income,
        actions=worker.actions,
    )


def _require_world():
    if world is None:
        raise HTTPException(
            status_code=400,
            detail="World not initialized. Use /init to initialize the world first.",
        )



@app.get("/", response_model=MessageResponse)
def read_root():
    return {"message": "Welcome to the InsureOnSim API. Use /init to initialize the world and /run_day to simulate a day."}


@app.post("/init", response_model=MessageResponse)
def init_world():
    global world
    if world is not None:
        raise HTTPException(status_code=400, detail="World already initialized. Use /reset to reinitialize.")
    world = World(
        seed=config["SEED"],
        n_zones=config["N_ZONES"],
        n_users=config["N_USERS"],
        zone_types=config["ZONE_TYPES"],
        weather_disaster_types=config["WEATHER_DISASTER_TYPES"],
        min_zone_connections=config["MIN_ZONE_CONNECTIONS"],
        max_zone_connections=config["MAX_ZONE_CONNECTIONS"],
        min_zone_distance=config["MIN_ZONE_DISTANCE"],
        max_zone_distance=config["MAX_ZONE_DISTANCE"],
        fraud_fraction=config["FRAUD_FRACTION"],
        worker_type_fraction=config["WORKER_TYPE_FRACTION"],
        income_range=config["INCOME_RANGE"],
        lockdown_hotspot_fraction=config["LOCKDOWN_HOTSPOT_FRACTION"],
        disaster_hotspot_fraction=config["DISASTER_HOTSPOT_FRACTION"],
        hotspot_event_prob=config["HOTSPOT_EVENT_PROB"],
        len_actions=config["LEN_ACTIONS"],
    )
    world.setup_zones()
    world.setup_workers()
    return {"message": "World initialized with zones and workers"}


@app.post("/run_day", response_model=DaySummaryResponse)
def run_day():
    _require_world()
    world.run_day()
    return {"message": f"Day {world.day} completed", "day_summary": world.get_day_summary()}


@app.post("/reset", response_model=MessageResponse)
def reset_world():
    global world
    world = None
    return {"message": "World reset. Use /init to initialize the world again."}



@app.get("/weather_alerts", response_model=WeatherAlertsResponse)
def weather_alerts():
    _require_world()
    return {"weather_alerts": world.get_weather_alerts()}


@app.get("/government_alerts", response_model=GovernmentAlertsResponse)
def government_alerts():
    _require_world()
    return {"government_alerts": world.get_government_alerts()}



@app.post("/claims", response_model=ClaimsResponse)
def process_claims():
    _require_world()
    if world.days_passed == 0:
        raise HTTPException(status_code=400, detail="No days have been simulated yet. Call /run_day first.")

    claims_today = world.process_claims()
    fraud_count = sum(1 for c in claims_today if c["is_fraud"])
    legitimate_count = len(claims_today) - fraud_count

    return ClaimsResponse(
        day=world.days_passed,
        day_name=world.day,
        total_claims=len(claims_today),
        legitimate_claims=legitimate_count,
        fraud_claims=fraud_count,
        claims=[ClaimRecord(**c) for c in claims_today],
    )


@app.get("/claims/history", response_model=ClaimsResponse)
def all_claims_history():
    _require_world()
    all_claims = []
    for worker in world.workers.values():
        for entry in worker.claim_history:
            all_claims.append(ClaimRecord(
                worker_id=worker.id,
                zone_id=entry["zone_id"],
                zone_type=world.zones[entry["zone_id"]].type,
                income=worker.income,
                worker_type=worker.type,
                reason=entry["reason"],
                is_fraud=entry["is_fraud"],
                day=entry["day"],
                day_name=entry["day_name"],
            ))

    fraud_count = sum(1 for c in all_claims if c.is_fraud)
    return ClaimsResponse(
        day=world.days_passed,
        day_name=world.day,
        total_claims=len(all_claims),
        legitimate_claims=len(all_claims) - fraud_count,
        fraud_claims=fraud_count,
        claims=all_claims,
    )


@app.get("/worker/{worker_id}/claims", response_model=WorkerClaimHistoryResponse)
def get_worker_claim_history(worker_id: int):
    _require_world()
    worker = world.workers.get(worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    fraud_count = sum(1 for c in worker.claim_history if c["is_fraud"])
    return WorkerClaimHistoryResponse(
        worker_id=worker.id,
        total_claims=len(worker.claim_history),
        fraud_claims=fraud_count,
        history=worker.claim_history,
    )


@app.post("/worker/{worker_id}/decide", response_model=WorkerDecideResponse)
def worker_decide(worker_id: int):
    _require_world()
    if world.days_passed == 0:
        raise HTTPException(status_code=400, detail="No days have been simulated yet. Call /run_day first.")
    worker = world.workers.get(worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")

    filed = worker.decide(world.day_idx)
    reason = worker.claim_history[-1]["reason"] if filed else None
    return WorkerDecideResponse(
        worker_id=worker.id,
        filed_claim=filed,
        reason=reason,
        is_fraud=worker.is_fraud,
    )



@app.post("/compare", response_model=CompareResponse)
def compare_payouts(issued: List[IssuedPayout]):
    _require_world()
    if world.days_passed == 0:
        raise HTTPException(
            status_code=400,
            detail="No days have been simulated yet. Call /run_day first.",
        )

    all_today = world.process_claims()
    legitimate_today: dict[int, str] = {
        c["worker_id"]: c["reason"]
        for c in all_today
        if not c["is_fraud"]
    }

    backend_issued: dict[int, str] = {p.worker_id: p.reason for p in issued}

    correct: list[CompareEntry] = []
    missed: list[CompareEntry] = []
    invalid: list[CompareEntry] = []

    for worker_id, sim_reason in legitimate_today.items():
        if worker_id in backend_issued:
            correct.append(CompareEntry(
                worker_id=worker_id,
                backend_reason=backend_issued[worker_id],
                sim_reason=sim_reason,
            ))
        else:
            missed.append(CompareEntry(
                worker_id=worker_id,
                backend_reason="not issued",
                sim_reason=sim_reason,
            ))

    for worker_id, backend_reason in backend_issued.items():
        if worker_id not in legitimate_today:
            invalid.append(CompareEntry(
                worker_id=worker_id,
                backend_reason=backend_reason,
                sim_reason=None,
            ))

    return CompareResponse(
        day=world.days_passed,
        day_name=world.day,
        submitted=len(issued),
        true_positives=len(correct),
        false_negatives=len(missed),
        false_positives=len(invalid),
        correct=correct,
        missed=missed,
        invalid=invalid,
    )



@app.get("/zone/{zone_id}", response_model=ZoneState)
def get_zone_state(zone_id: int):
    _require_world()
    zone = world.zones.get(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return _zone_state(zone)


@app.get("/worker/{worker_id}", response_model=WorkerState)
def get_worker_state(worker_id: int):
    _require_world()
    worker = world.workers.get(worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    return _worker_state(worker)


@app.get("/world_state", response_model=WorldState)
def get_world_state():
    _require_world()
    return WorldState(
        day=world.days_passed,
        zones=[_zone_state(z) for z in world.zones.values()],
        workers=[_worker_state(w) for w in world.workers.values()],
    )