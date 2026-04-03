# API Reference

InsureOnSim exposes a REST API built with FastAPI. All endpoints are available once the server is running with `uvicorn main:app`.

---

## Lifecycle Endpoints

### `GET /`

Returns a welcome message describing available actions.

**Response** `200 OK` — `MessageResponse`

```json
{ "message": "Welcome to the InsureOnSim API. Use /init to initialize the world and /run_day to simulate a day." }
```

---

### `POST /init`

Initialises the simulation world. Reads all parameters from `config.json`, creates zones, establishes inter-zone connections, and spawns workers.

Must be called before any other simulation endpoint.

**Response** `200 OK`

```json
{ "message": "World initialized with zones and workers" }
```

**Error** `400 Bad Request` — if the world has already been initialised.

```json
{ "detail": "World already initialized. Use /reset to reinitialize." }
```

---

### `POST /run_day`

Advances the simulation by one calendar day.

- Increments `days_passed` and advances the day-of-week index (Monday → Sunday → Monday …).
- Calls `trigger_event` on every zone, potentially setting `civil_state` to `"lockdown"` and/or `weather` to `"disaster"`.
- Recalculates daily actions for every worker.

**Response** `200 OK` — `DaySummaryResponse`

```json
{
  "message": "Day 3 completed",
  "day_summary": {
    "lockdown": 2,
    "stable": 7,
    "other_civil": 1,
    "weather_disaster": 1,
    "weather_clear": 8,
    "other_weather": 1
  }
}
```

**Error** `400 Bad Request` — if the world has not been initialised.

---

### `POST /reset`

Destroys the current world instance. After calling this endpoint, `/init` must be called again before running any simulation.

**Response** `200 OK`

```json
{ "message": "World reset. Use /init to initialize the world again." }
```

---

## Alert Endpoints

### `GET /weather_alerts`

Returns a list of zones that are currently experiencing a weather disaster.

**Response** `200 OK` — `WeatherAlertsResponse`

```json
{
  "weather_alerts": [
    { "zone_id": 4, "zone_type": "B", "alert": "flood" }
  ]
}
```

Each alert contains the zone ID, zone type, and the disaster type (e.g. `"storm"`, `"flood"`, `"heatwave"`).

---

### `GET /government_alerts`

Returns a list of zones that are currently under civil lockdown.

**Response** `200 OK` — `GovernmentAlertsResponse`

```json
{
  "government_alerts": [
    { "zone_id": 2, "zone_type": "A", "alert": "lockdown" }
  ]
}
```

---

## State Inspection Endpoints

### `GET /zone/{zone_id}`

Returns the full current state of a single zone.

**Path parameter:** `zone_id` — integer ID of the zone.

**Response** `200 OK` — `ZoneState`

```json
{
  "id": 3,
  "type": "C",
  "nearby_zones": { "1": 420, "5": 730, "7": 150 },
  "civil_state": "stable",
  "weather_state": "clear",
  "event_info": "storm"
}
```

`nearby_zones` is a dictionary mapping neighbouring zone IDs to their distances (in km).

**Error** `404 Not Found` — if the zone ID does not exist.

---

### `GET /worker/{worker_id}`

Returns the current state of a single worker.

**Path parameter:** `worker_id` — integer ID of the worker.

**Response** `200 OK` — `WorkerState`

```json
{
  "id": 12,
  "zone_id": 5,
  "type": 1,
  "income": 67400,
  "actions": [
    "short commute multiple deliveries",
    "leisure",
    "long commute single delivery",
    "leisure",
    "short commute single delivery"
  ]
}
```

`type` is `0` for a standard worker and `1` for a high-activity worker.

**Error** `404 Not Found` — if the worker ID does not exist.

---

### `GET /world_state`

Returns a complete snapshot of the current simulation state — all zones and all workers.

**Response** `200 OK` — `WorldState`

```json
{
  "day": 5,
  "zones": [ /* array of ZoneState objects */ ],
  "workers": [ /* array of WorkerState objects */ ]
}
```

---

### `GET /fraud_rings`

Returns the currently generated fraud rings and their member worker IDs.

**Response** `200 OK` — `FraudRingsResponse`

```json
{
  "total_rings": 3,
  "rings": {
    "0": [1, 4, 9],
    "1": [7, 12],
    "2": [18, 20, 22, 25]
  }
}
```

---

## Configuration Reference (`config.json`)

| Key                         | Type          | Default                          | Description                                                                 |
|-----------------------------|---------------|----------------------------------|-----------------------------------------------------------------------------|
| `SEED`                      | int           | `42`                             | Random seed for reproducible simulations.                                   |
| `N_ZONES`                   | int           | `10`                             | Number of geographic zones to create.                                       |
| `N_USERS`                   | int           | `30`                             | Number of worker agents to spawn.                                           |
| `ZONE_TYPES`                | list[str]     | `["A","B","C"]`                  | Zone category labels assigned randomly to each zone.                        |
| `WEATHER_DISASTER_TYPES`    | list[str]     | `["storm","flood","heatwave"]`   | Possible weather disaster event names.                                      |
| `MIN_ZONE_CONNECTIONS`      | int           | `3`                              | Minimum number of neighbouring zones each zone must connect to.             |
| `MAX_ZONE_CONNECTIONS`      | int           | `6`                              | Maximum number of neighbouring zones each zone can connect to.              |
| `MIN_ZONE_DISTANCE`         | int           | `100`                            | Minimum distance (km) between two connected zones.                          |
| `MAX_ZONE_DISTANCE`         | int           | `1000`                           | Maximum distance (km) between two connected zones.                          |
| `INCOME_RANGE`              | [int, int]    | `[30000, 100000]`                | Uniform range from which each worker's annual income is sampled.            |
| `FRAUD_FRACTION`            | float         | `0.3`                            | Fraction of workers initialised with a higher fraud probability (0.5–1.0).  |
| `FRAUD_RING_FRACTION`       | float         | `0.35`                           | Fraction of fraud-prone workers assigned to fraud rings.                     |
| `MIN_FRAUD_RING_SIZE`       | int           | `2`                              | Minimum number of workers in a fraud ring.                                   |
| `MAX_FRAUD_RING_SIZE`       | int           | `5`                              | Maximum number of workers in a fraud ring.                                   |
| `FRAUD_RING_ACTIVATION_PROB`| float         | `0.6`                            | Daily chance that a ring coordinates fraudulent claim submissions.            |
| `FRAUD_RING_BOOST`          | float         | `0.25`                           | Fraud probability boost applied during an active ring day.                    |
| `WORKER_TYPE_FRACTION`      | float         | `0.4`                            | Fraction of workers assigned as type 1 (high-activity).                    |
| `LOCKDOWN_HOTSPOT_FRACTION` | float         | `0.2`                            | Fraction of zones that are lockdown hotspots.                               |
| `DISASTER_HOTSPOT_FRACTION` | float         | `0.2`                            | Fraction of zones that are weather disaster hotspots.                       |
| `HOTSPOT_EVENT_PROB`        | float         | `0.6`                            | Total daily event probability assigned to hotspot zones.                    |
| `LEN_ACTIONS`               | int           | `5`                              | Number of daily action slots generated per worker per day.                  |
| `N_DAYS`                    | int           | `7`                              | Used by `World.simulate()` when running in batch (non-API) mode.            |

### Validation Constraints

The following assertions are checked at startup:

- `MIN_ZONE_CONNECTIONS < N_ZONES`
- `MAX_ZONE_CONNECTIONS < N_ZONES`
- `MIN_ZONE_CONNECTIONS <= MAX_ZONE_CONNECTIONS`