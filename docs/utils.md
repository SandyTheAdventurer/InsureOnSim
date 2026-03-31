# Utils

`classes/utils.py` contains a single utility function used throughout the simulation for probability distribution.

---

## `distribute_prob`

```python
distribute_prob(n, total_prob=1.0, sigma=1.0, peak=None) -> np.ndarray
```

Generates an array of `n` probabilities shaped like a Gaussian (bell curve), with a controllable peak position and total sum.

This is used in two places:

- **Zone event probability**: distributes a zone's total daily event probability across the 7 days of the week.
- **Worker fraud probability**: distributes a worker's total fraud probability across the 7 days of the week.

### Parameters

| Parameter    | Type   | Default        | Description                                                                                             |
|--------------|--------|----------------|---------------------------------------------------------------------------------------------------------|
| `n`          | int    | —              | Number of elements in the output array (e.g. `7` for days of the week).                                |
| `total_prob` | float  | `1.0`          | The desired sum of all probabilities in the output. The raw Gaussian is rescaled to match this value.   |
| `sigma`      | float  | `1.0`          | Controls the spread (standard deviation) of the Gaussian. Higher values = flatter distribution.         |
| `peak`       | int or None | `None`   | Index of the peak (most likely day). If `None`, a random index in `[0, n)` is chosen each call.        |

### Returns

`np.ndarray` of shape `(n,)` — a probability array where values sum to `total_prob`.

### Algorithm

```
x = [0, 1, 2, ..., n-1]
raw = exp(-0.5 * ((x - peak) / sigma)^2)   # Gaussian curve
probs = raw / sum(raw) * total_prob          # rescale to total_prob
```

### Examples

**Distribute probability uniformly (high sigma):**

```python
distribute_prob(n=7, total_prob=0.6, sigma=10.0)
# Output: roughly [0.086, 0.086, 0.086, 0.086, 0.086, 0.086, 0.086]
```

**Concentrate probability on a specific day:**

```python
distribute_prob(n=7, total_prob=0.6, sigma=1.0, peak=2)
# Output: most probability concentrated around index 2 (Wednesday)
```

**Random peak (default behaviour):**

```python
distribute_prob(n=7, total_prob=0.6, sigma=1.0)
# Output: bell curve centred on a randomly chosen day
```

### Notes

- With `sigma=1.0` (the default), the distribution is narrow — most probability is concentrated on the peak day and its immediate neighbours.
- When `total_prob=0` (e.g. for non-hotspot zones), the function returns an all-zero array, ensuring those zones never trigger events.
- Because `peak` defaults to a fresh random draw each call, two calls with the same parameters but no explicit `peak` will produce different results.