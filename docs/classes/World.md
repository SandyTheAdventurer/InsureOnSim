# World & Zone

`classes/world.py` contains two classes: `Zone` and `World`. `Zone` represents a single geographic region; `World` acts as the top-level simulation engine that owns and orchestrates all zones and workers.

---

## Zone

```python
class Zone(id, type, n_connections, hostpot_type, event_prob, event_info)
```

A single geographic region in the simulation. Zones have a civil state (stable or lockdown), a weather state (clear or disaster), and a list of active alerts. They are connected to neighbouring zones with distances.

### Constructor Parameters

| Parameter      | Type   | Description                                                                                      |
|----------------|--------|--------------------------------------------------------------------------------------------------|
| `id`           | int    | Unique integer identifier for this zone.                                                         |
| `type`         | str    | Zone category label (e.g. `"A"`, `"B"`, `"C"`).                                                 |
| `n_connections`| int    | Target number of neighbouring zones to connect to during world setup.                            |
| `hostpot_type` | int    | `0` = no events; `1` = lockdown only; `2` = weather disaster only; `3` = both.                  |
| `event_prob`   | float  | Total daily event probability, distributed across the 7 days of the week by `distribute_prob`.  |
| `event_info`   | str    | Label for the event that fires (e.g. `"flood"`, `"lockdown"`).                                  |

### Attributes

| Attribute           | Type        | Description                                                                      |
|---------------------|-------------|----------------------------------------------------------------------------------|
| `nearby_zones`      | dict[int,int]| Maps neighbour zone IDs to their distances in km.                               |
| `civil_state`       | str         | Current civil status: `"stable"` or `"lockdown"`.                               |
| `weather`           | str         | Current weather status: `"clear"` or `"disaster"`.                              |
| `alerts`            | list[str]   | Accumulated alert messages for this zone.                                        |
| `event_prob_dist`   | np.ndarray  | 7-element array of daily event probabilities (one per day of week).              |

### Methods

#### `add_connection(other_zone, max_zone_distance, min_zone_distance, update_probs=True)`

Establishes a bidirectional connection between this zone and `other_zone` with a randomly sampled distance.

When `update_probs=True`, the connected zone's event probability distribution is increased based on the distance ratio — closer zones propagate more risk.

#### `trigger_event(day_idx) -> Tuple[bool, bool, str]`

Evaluates whether an event fires today using `event_prob_dist[day_idx]`.

Returns a tuple `(civil_event, weather_event, description)`:

- For `hotspot_type == 1`: sets `civil_state = "lockdown"`.
- For `hotspot_type == 2`: sets `weather = "disaster"`.
- For `hotspot_type == 3`: triggers both lockdown and disaster.
- Returns `(False, False, "")` if no event occurs or zone has `hotspot_type == 0`.

---

## World

```python
class World(seed, n_zones, n_users, zone_types, weather_disaster_types,
            min_zone_connections, max_zone_connections, min_zone_distance,
            max_zone_distance, fraud_fraction, worker_type_fraction,
            income_range, lockdown_hotspot_fraction, disaster_hotspot_fraction,
            hotspot_event_prob, len_actions)
```

The simulation container. Manages all zones and workers, advances time, and aggregates simulation state.

### Constructor Parameters

All parameters correspond directly to keys in `config.json`. See the [API reference](../api.md#configuration-reference-configjson) for a full description of each.

### Key Attributes

| Attribute       | Type            | Description                                         |
|-----------------|-----------------|-----------------------------------------------------|
| `zones`         | dict[int, Zone] | All zones keyed by their integer ID.                |
| `workers`       | dict[int, Worker]| All workers keyed by their integer ID.             |
| `days_passed`   | int             | Total number of days simulated so far.              |
| `day`           | str             | Current day-of-week name (e.g. `"Monday"`).         |
| `day_idx`       | int             | Current day-of-week index (0 = Monday, 6 = Sunday). |

### Methods

#### `setup_zones()`

Creates `n_zones` Zone instances. For each zone:

1. Determines `hotspot_type` by sampling against `lockdown_hotspot_fraction` and `disaster_hotspot_fraction`.
2. Randomly assigns a type from `zone_types`.
3. Randomly samples `n_connections` in the allowed range.

After all zones are created, establishes connections between them until each zone reaches its target `n_connections`.

#### `setup_workers()`

Creates `n_users` Worker instances. For each worker:

1. Assigns a random zone.
2. Assigns `type` (0 or 1) based on `worker_type_fraction`.
3. Assigns a `fraud_prob`: uniform in `[0.5, 1.0]` for fraud workers, `[0.0, 0.5]` for honest workers (controlled by `fraud_fraction`).
4. Samples an `income` from `income_range`.
5. Generates an initial set of daily actions via `worker_daily_action`.

#### `run_day()`

Advances the simulation by one day:

1. Increments `days_passed` and `day_idx` (wraps around after Sunday).
2. Calls `trigger_event(day_idx)` on every zone.
3. Calls `worker_daily_action(worker)` on every worker to refresh their action list.

#### `get_weather_alerts() -> list`

Returns a list of alert dictionaries for all zones whose `weather == "disaster"` or whose `alerts` list contains a known disaster type.

#### `get_government_alerts() -> list`

Returns a list of alert dictionaries for all zones whose `civil_state == "lockdown"` or whose `alerts` list contains `"lockdown"`.

#### `get_day_summary() -> DaySummary`

Aggregates zone states across the entire world into counts:

| Field             | Description                              |
|-------------------|------------------------------------------|
| `lockdown`        | Zones with `civil_state == "lockdown"`.  |
| `stable`          | Zones with `civil_state == "stable"`.    |
| `other_civil`     | Zones with any other civil state.        |
| `weather_disaster`| Zones with `weather == "disaster"`.      |
| `weather_clear`   | Zones with `weather == "clear"`.         |
| `other_weather`   | Zones with any other weather state.      |

#### `worker_daily_action(worker) -> list[str]`

Generates a list of daily actions for a worker using a skewed probability distribution over five action categories:

- `"long commute single delivery"`
- `"long commute multiple deliveries"`
- `"short commute multiple deliveries"`
- `"short commute single delivery"`
- `"leisure"`

Type `0` workers generate 5 probabilistic actions with the distribution peaked at index 2 (short commute multiple deliveries), then padded with 5 `"leisure"` entries. Type `1` workers generate 10 fully probabilistic actions with a random peak.

#### `simulate(n_days, logger=None)`

Batch simulation mode. Runs `run_day()` for `n_days` iterations, optionally logging each day's summary. Intended for offline / script use rather than API use.