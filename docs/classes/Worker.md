# Worker

`classes/worker.py` defines the `Worker` class, which represents a single insured individual in the simulation.

---

## Worker

```python
class Worker(id, world, zone, type, fraud_prob, income)
```

A worker agent that lives in a zone, has a type, an income, and a probabilistic tendency to commit insurance fraud. Each day, workers generate a list of simulated actions and can decide whether to file a claim.

### Constructor Parameters

| Parameter    | Type    | Description                                                                                               |
|--------------|---------|-----------------------------------------------------------------------------------------------------------|
| `id`         | int     | Unique integer identifier for this worker.                                                                |
| `world`      | World   | Reference to the parent `World` instance.                                                                 |
| `zone`       | Zone    | The `Zone` object in which this worker currently resides.                                                 |
| `type`       | int     | Worker activity type. `0` = standard (fewer commute actions); `1` = high-activity.                       |
| `fraud_prob` | float   | Total fraud probability, distributed across 7 days by `distribute_prob`. Higher values = more fraud risk.|
| `income`     | float   | Annual income of the worker, sampled uniformly from `INCOME_RANGE`.                                       |

### Attributes

| Attribute     | Type       | Description                                                                                  |
|---------------|------------|----------------------------------------------------------------------------------------------|
| `actions`     | list[str]  | Most recently generated list of daily actions (see `World.worker_daily_action`).             |
| `is_fraud`    | bool       | Set to `True` when the worker decides to commit fraud on a given day.                        |
| `fraud_dist`  | np.ndarray | 7-element probability array over days of the week, built from `fraud_prob`.                  |

### Worker Types

| Type | Description                                                                                                 |
|------|-------------------------------------------------------------------------------------------------------------|
| `0`  | Standard worker. Generates 5 probabilistic actions with peak at index 2, padded with 5 leisure entries.    |
| `1`  | High-activity worker. Generates 10 fully probabilistic actions with a random daily peak.                    |

### Fraud Probability Distribution

The `fraud_prob` passed to the constructor represents a total probability budget. The `distribute_prob` utility spreads this budget across the 7 days of the week using a Gaussian-shaped distribution with a random peak day. This means a worker is more likely to attempt fraud on certain days of the week and less likely on others.

Workers initialised with `fraud_prob` in `[0.5, 1.0]` are considered "fraud workers"; those with values in `[0.0, 0.5]` are considered "honest workers". The split is controlled by `FRAUD_FRACTION` in `config.json`.

### Methods

#### `decide(day_idx) -> bool`

Determines whether the worker files a claim (potentially fraudulent) on the given day.

Returns `True` (claim filed) in the following cases:

1. The worker's zone is under `"lockdown"`.
2. The worker's zone has `weather == "disaster"`.
3. A random draw falls below `fraud_dist[day_idx]` — in which case `is_fraud` is also set to `True`.

Returns `False` if none of the above conditions are met.

**Parameters:**

| Parameter | Type | Description                                      |
|-----------|------|--------------------------------------------------|
| `day_idx` | int  | Day-of-week index (0 = Monday, 6 = Sunday).      |

**Returns:** `bool` — whether the worker files a claim today.

---

## Notes

- A claim filed due to lockdown or disaster is considered legitimate (forced by external conditions), even though `decide()` returns `True`.
- Only claims triggered by the probabilistic fraud branch set `is_fraud = True`.
- Workers do not move between zones in the current implementation; zone assignment is fixed at initialisation.