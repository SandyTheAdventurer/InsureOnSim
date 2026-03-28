from classes.world import World
from classes.models import *
import logging
from fastapi import FastAPI, HTTPException
import json

logging.basicConfig(level=logging.INFO)

config = json.load(open("config.json", "r"))

assert config["MIN_ZONE_CONNECTIONS"] < config["N_ZONES"], "Minimum connections must be less than total zones"
assert config["MAX_ZONE_CONNECTIONS"] < config["N_ZONES"], "Maximum connections must be less than total zones"
assert config["MIN_ZONE_CONNECTIONS"] <= config["MAX_ZONE_CONNECTIONS"], "Minimum connections must be less than or equal to maximum connections"

app = FastAPI()
world = None

@app.get("/", response_model=MessageResponse)
def read_root():
    return {"message": "Welcome to the InsureOnSim API. Use /init to initialize the world and /run_day to simulate a day."}
@app.post("/init")
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
        len_actions=config["LEN_ACTIONS"],
        lockdown_hotspot_fraction=config["LOCKDOWN_HOTSPOT_FRACTION"],
        disaster_hotspot_fraction=config["DISASTER_HOTSPOT_FRACTION"],
        hotspot_event_prob=config["HOTSPOT_EVENT_PROB"]
    )
    world.setup_zones()
    world.setup_workers()
    return {"message": "World initialized with zones and workers"}

@app.post("/run_day", response_model=DaySummaryResponse)
def run_day():
    global world
    if world is None:
        raise HTTPException(status_code=400, detail="World not initialized. Use /init to initialize the world first.")
    world.run_day()
    return {"message": f"Day {world.day} completed", "day_summary": world.get_day_summary()}

@app.get("/weather_alerts", response_model=WeatherAlertsResponse)
def weather_alerts():
    global world
    if world is None:
        raise HTTPException(status_code=400, detail="World not initialized. Use /init to initialize the world first.")
    return {"weather_alerts": world.get_weather_alerts()}

@app.get("/government_alerts", response_model=GovernmentAlertsResponse)
def government_alerts():
    global world
    if world is None:
        raise HTTPException(status_code=400, detail="World not initialized. Use /init to initialize the world first.")
    return {"government_alerts": world.get_government_alerts()}

@app.post("/reset")
def reset_world():
    global world
    world = None
    return {"message": "World reset. Use /init to initialize the world again."}

@app.get("/zone/{zone_id}", response_model=ZoneState)
def get_zone_state(zone_id: int):
    global world
    if world is None:
        raise HTTPException(status_code=400, detail="World not initialized. Use /init to initialize the world first.")
    zone = world.zones.get(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return ZoneState(
        id=zone.id,
        type=zone.type,
        nearby_zones=zone.nearby_zones,
        civil_state=zone.civil_state,
        weather_state=zone.weather,
        event_info=zone.event_info
    )

@app.get("/worker/{worker_id}", response_model=WorkerState)
def get_worker_state(worker_id: int):
    global world
    if world is None:
        raise HTTPException(status_code=400, detail="World not initialized. Use /init to initialize the world first.")
    worker = world.workers.get(worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    return WorkerState(
        id=worker.id,
        zone_id=worker.zone.id,
        type=worker.type,
        income=worker.income,
        actions=worker.actions
    )
    
@app.get("/world_state", response_model=WorldState)
def get_world_state():
    global world
    if world is None:
        raise HTTPException(status_code=400, detail="World not initialized. Use /init to initialize the world first.")
    return WorldState(
        day=world.days_passed,
        zones=[ZoneState(
            id=zone.id,
            type=zone.type,
            nearby_zones=zone.nearby_zones,
            civil_state=zone.civil_state,
            weather_state=zone.weather,
            event_info=zone.event_info
        ) for zone in world.zones.values()],
        workers=[WorkerState(
            id=worker.id,
            zone_id=worker.zone.id,
            type=worker.type,
            income=worker.income
        ) for worker in world.workers.values()]
    )