# Data Models

`classes/models.py` defines all Pydantic models used for FastAPI request/response validation and serialisation.

---

## Response Models

### `MessageResponse`

A simple message envelope returned by lifecycle endpoints.

| Field     | Type | Description          |
|-----------|------|----------------------|
| `message` | str  | Human-readable status message. |

---

### `DaySummary`

A count of zone states at the end of a simulated day. Returned inside `DaySummaryResponse`.

| Field             | Type | Description                                      |
|-------------------|------|--------------------------------------------------|
| `lockdown`        | int  | Number of zones with `civil_state == "lockdown"`. |
| `stable`          | int  | Number of zones with `civil_state == "stable"`.   |
| `other_civil`     | int  | Number of zones with any other civil state.        |
| `weather_disaster`| int  | Number of zones with `weather == "disaster"`.      |
| `weather_clear`   | int  | Number of zones with `weather == "clear"`.         |
| `other_weather`   | int  | Number of zones with any other weather state.      |

---

### `DaySummaryResponse`

Returned by `POST /run_day`.

| Field         | Type        | Description                          |
|---------------|-------------|--------------------------------------|
| `message`     | str         | Day completion message (e.g. `"Day 3 completed"`). |
| `day_summary` | DaySummary  | Aggregated zone state counts for the day. |

---

### `WeatherAlertsResponse`

Returned by `GET /weather_alerts`.

| Field            | Type | Description                                          |
|------------------|------|------------------------------------------------------|
| `weather_alerts` | list | List of alert dicts with `zone_id`, `zone_type`, and `alert`. |

---

### `GovernmentAlertsResponse`

Returned by `GET /government_alerts`.

| Field               | Type | Description                                             |
|---------------------|------|---------------------------------------------------------|
| `government_alerts` | list | List of alert dicts with `zone_id`, `zone_type`, and `alert`. |

---

## State Models

### `ZoneState`

Returned by `GET /zone/{zone_id}` and included in `WorldState`.

| Field          | Type        | Description                                                        |
|----------------|-------------|--------------------------------------------------------------------|
| `id`           | int         | Zone integer ID.                                                   |
| `type`         | str         | Zone category label (e.g. `"A"`, `"B"`, `"C"`).                  |
| `nearby_zones` | dict        | Maps neighbouring zone IDs (as strings) to distances in km.       |
| `civil_state`  | str         | Current civil state: `"stable"` or `"lockdown"`.                  |
| `weather_state`| str         | Current weather state: `"clear"` or `"disaster"`.                 |
| `event_info`   | str         | Label of the event type assigned to this zone (e.g. `"flood"`).   |

---

### `WorkerState`

Returned by `GET /worker/{worker_id}` and included in `WorldState`.

| Field      | Type       | Description                                                          |
|------------|------------|----------------------------------------------------------------------|
| `id`       | int        | Worker integer ID.                                                   |
| `zone_id`  | int        | ID of the zone the worker currently occupies.                        |
| `type`     | int        | Worker activity type: `0` = standard, `1` = high-activity.          |
| `income`   | int        | Annual income of the worker.                                         |
| `actions`  | list       | List of daily action strings generated for the current day.          |

---

### `WorldState`

Returned by `GET /world_state`.

| Field     | Type             | Description                            |
|-----------|------------------|----------------------------------------|
| `day`     | int              | Number of days simulated so far.       |
| `zones`   | list[ZoneState]  | State of every zone in the world.      |
| `workers` | list[WorkerState]| State of every worker in the world.    |

---