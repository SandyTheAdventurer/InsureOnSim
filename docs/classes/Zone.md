# Zone

The `Zone` class is defined in `classes/world.py` alongside `World`. It represents a single geographic region within the simulation.

---

> For the full class reference including constructor parameters, attributes, and methods, see the [World & Zone documentation](World.md#zone).

---

## Zone States

### Civil State

| Value      | Meaning                                                                 |
|------------|-------------------------------------------------------------------------|
| `"stable"` | Default state. No government event is active.                           |
| `"lockdown"` | A civil lockdown has been triggered. Workers in this zone will always file a claim. |

### Weather State

| Value       | Meaning                                                                 |
|-------------|-------------------------------------------------------------------------|
| `"clear"`   | Default state. No weather event is active.                              |
| `"disaster"`| A weather disaster is active. Workers in this zone will always file a claim. |

---

## Hotspot Types

Zones are assigned a hotspot type at world initialisation, determined by sampling against `LOCKDOWN_HOTSPOT_FRACTION` and `DISASTER_HOTSPOT_FRACTION`.

| Type | Civil Event   | Weather Event | Probability Source                              |
|------|---------------|---------------|-------------------------------------------------|
| `0`  | None          | None          | `event_prob = 0` — zone will never trigger events. |
| `1`  | Lockdown      | None          | `HOTSPOT_EVENT_PROB` distributed across week.   |
| `2`  | None          | Disaster      | `HOTSPOT_EVENT_PROB` distributed across week.   |
| `3`  | Lockdown      | Disaster      | `HOTSPOT_EVENT_PROB` distributed across week.   |

---

## Event Probability Propagation

When a zone adds a connection to another zone, it increases the neighbour's event probability distribution. The amount added is proportional to the ratio of the connection distance to the total distance range (`MAX_ZONE_DISTANCE - MIN_ZONE_DISTANCE`).

This means that zones connected to many high-probability hotspot zones will gradually accumulate higher event probabilities, even if they were not originally designated as hotspots.

---

## Alerts

Each zone maintains an `alerts` list of string labels accumulated over time. Alerts are appended — not replaced — each time an event fires. The list is used by `World.get_weather_alerts()` and `World.get_government_alerts()` to detect active conditions.