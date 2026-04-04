from pathlib import Path
import logging
from fastapi import FastAPI, HTTPException
from typing import List
import json
import os
from dotenv import load_dotenv

try:
    from .classes.world import World
    from .classes.models import *
    from .backend_bridge import BackendBridge
except ImportError:
    try:
        from InsureOnSim.classes.world import World
        from InsureOnSim.classes.models import *
        from InsureOnSim.backend_bridge import BackendBridge
    except ImportError:
        from classes.world import World
        from classes.models import *
        from backend_bridge import BackendBridge

load_dotenv()

logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
config = json.loads((BASE_DIR / "config.json").read_text())

assert config["MIN_ZONE_CONNECTIONS"] < config["N_ZONES"], "Minimum connections must be less than total zones"
assert config["MAX_ZONE_CONNECTIONS"] < config["N_ZONES"], "Maximum connections must be less than total zones"
assert config["MIN_ZONE_CONNECTIONS"] <= config["MAX_ZONE_CONNECTIONS"], "Minimum connections must be less than or equal to maximum connections"

app = FastAPI(
    title="InsureOnSim API",
    description="Parametric insurance simulation engine for InsureOn — Guidewire DevTrails.",
    version="1.0.0",
)

world: World | None = None
backend_bridge: BackendBridge | None = None



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
        email=worker.email,
        ring_id=worker.ring_id,
        actions=worker.actions,
    )


def _require_world():
    if world is None:
        raise HTTPException(
            status_code=400,
            detail="World not initialized. Use /init to initialize the world first.",
        )


def _get_backend_bridge() -> BackendBridge:
    global backend_bridge
    if backend_bridge is not None:
        return backend_bridge

    backend_url = os.getenv("INSUREON_BACKEND_URL", "").strip()
    sim_test_key = os.getenv("SIM_TEST_API_KEY", "").strip()

    if not backend_url:
        raise HTTPException(
            status_code=400,
            detail="INSUREON_BACKEND_URL is not configured",
        )
    if not sim_test_key:
        raise HTTPException(
            status_code=400,
            detail="SIM_TEST_API_KEY is not configured",
        )

    backend_bridge = BackendBridge(
        base_url=backend_url,
        sim_test_key=sim_test_key,
    )
    return backend_bridge



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
        fraud_ring_fraction=config.get("FRAUD_RING_FRACTION", 0.35),
        min_fraud_ring_size=config.get("MIN_FRAUD_RING_SIZE", 2),
        max_fraud_ring_size=config.get("MAX_FRAUD_RING_SIZE", 5),
        fraud_ring_activation_prob=config.get("FRAUD_RING_ACTIVATION_PROB", 0.6),
        fraud_ring_boost=config.get("FRAUD_RING_BOOST", 0.25),
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
                email=worker.email,
                zone_id=entry["zone_id"],
                zone_type=world.zones[entry["zone_id"]].type,
                income=worker.income,
                worker_type=worker.type,
                reason=entry["reason"],
                is_fraud=entry["is_fraud"],
                ring_id=entry.get("ring_id"),
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


@app.get("/worker/{worker_id}/platform-metrics", response_model=PlatformMetricsResponse)
def get_worker_platform_metrics(worker_id: int):
    _require_world()
    try:
        metrics = world.get_worker_platform_metrics(worker_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Worker not found")
    return PlatformMetricsResponse(**metrics)


@app.get("/world_state", response_model=WorldState)
def get_world_state():
    _require_world()
    return WorldState(
        day=world.days_passed,
        zones=[_zone_state(z) for z in world.zones.values()],
        workers=[_worker_state(w) for w in world.workers.values()],
    )


@app.get("/fraud_rings", response_model=FraudRingsResponse)
def get_fraud_rings():
    _require_world()
    return FraudRingsResponse(
        total_rings=len(world.fraud_rings),
        rings=world.fraud_rings,
    )


@app.get("/backend/status", response_model=BackendBridgeStatus)
def backend_status():
    backend_url = os.getenv("INSUREON_BACKEND_URL", "").strip()
    sim_test_key = os.getenv("SIM_TEST_API_KEY", "").strip()

    if not backend_url:
        return BackendBridgeStatus(
            configured=False,
            backend_url="",
            reason="INSUREON_BACKEND_URL missing",
        )

    if not sim_test_key:
        return BackendBridgeStatus(
            configured=False,
            backend_url=backend_url,
            reason="SIM_TEST_API_KEY missing",
        )

    return BackendBridgeStatus(configured=True, backend_url=backend_url)


@app.post("/backend/onboard", response_model=BackendSyncResponse)
def onboard_workers_to_backend(limit: int | None = None):
    _require_world()
    bridge = _get_backend_bridge()
    workers = sorted(world.workers.values(), key=lambda w: w.id)
    return bridge.onboard_workers(workers, limit=limit)


@app.post("/backend/trigger", response_model=BackendTriggerResult)
def trigger_backend_from_claims():
    _require_world()
    bridge = _get_backend_bridge()
    if world.days_passed == 0:
        raise HTTPException(status_code=400, detail="No days have been simulated yet. Call /run_day first.")

    claims_today = world.process_claims()
    return bridge.trigger_from_claims(claims_today, day_number=world.days_passed)


@app.post("/backend/sync_weather", response_model=BackendTriggerResult)
def sync_weather_alerts_to_backend():
    _require_world()
    bridge = _get_backend_bridge()
    if world.days_passed == 0:
        raise HTTPException(status_code=400, detail="No days have been simulated yet. Call /run_day first.")

    weather_alerts_today = world.get_weather_alerts()
    return bridge.trigger_from_weather_alerts(weather_alerts_today, day_number=world.days_passed)


@app.post("/backend/test_day", response_model=BackendDayTestResponse)
def run_integrated_backend_test_day():
    _require_world()
    bridge = _get_backend_bridge()

    world.run_day()
    weather_alerts_today = world.get_weather_alerts()
    claims_today = world.process_claims()
    trigger_result = bridge.trigger_from_weather_alerts(weather_alerts_today, day_number=world.days_passed)
    monitoring_result = bridge.process_monitoring_day()
    backend_active_claims = bridge.count_active_claims_for_onboarded()

    legitimate_claims = [c for c in claims_today if not c["is_fraud"]]
    fraudulent_claims = [c for c in claims_today if c["is_fraud"]]

    return BackendDayTestResponse(
        day=world.days_passed,
        day_name=world.day,
        total_sim_claims=len(claims_today),
        legitimate_sim_claims=len(legitimate_claims),
        fraudulent_sim_claims=len(fraudulent_claims),
        backend_trigger_count=trigger_result["trigger_count"],
        backend_claims_opened=trigger_result["claims_opened_total"],
        backend_monitor_processed=monitoring_result.get("processed", 0),
        backend_monitor_status_counts=monitoring_result.get("status_counts", {}),
        backend_active_claims=backend_active_claims,
    )


@app.get("/backend/fraud_audit")
def backend_fraud_audit():
    bridge = _get_backend_bridge()
    return bridge.collect_fraud_audit()

@app.get("/backend/fraud_accuracy", response_model=BackendFraudAccuracyResponse)
def backend_fraud_accuracy():
    _require_world()
    bridge = _get_backend_bridge()
    summary = bridge.collect_worker_flag_summary()
    onboarded_ids = set(summary.get("onboarded_worker_ids", []))

    sim_fraud_workers = set()
    for worker_id in onboarded_ids:
        worker = world.workers.get(worker_id)
        if not worker:
            continue
        if any(entry.get("is_fraud", False) for entry in worker.claim_history):
            sim_fraud_workers.add(worker_id)

    sim_legit_workers = onboarded_ids - sim_fraud_workers
    backend_flagged_workers = set(summary.get("flagged_workers", []))

    true_positive = len(sim_fraud_workers & backend_flagged_workers)
    false_positive = len(backend_flagged_workers - sim_fraud_workers)
    false_negative = len(sim_fraud_workers - backend_flagged_workers)
    true_negative = len(sim_legit_workers - backend_flagged_workers)

    precision = round(true_positive / (true_positive + false_positive), 4) if (true_positive + false_positive) else 0.0
    recall = round(true_positive / (true_positive + false_negative), 4) if (true_positive + false_negative) else 0.0

    return BackendFraudAccuracyResponse(
        workers_checked=len(onboarded_ids),
        sim_fraud_workers=len(sim_fraud_workers),
        sim_legit_workers=len(sim_legit_workers),
        backend_flagged_workers=len(backend_flagged_workers),
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        true_negative=true_negative,
        precision=precision,
        recall=recall,
    )