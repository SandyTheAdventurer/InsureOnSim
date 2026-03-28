import numpy as np

def distribute_prob(n, total_prob=1.0, sigma=1.0) -> np.ndarray:
    x = np.arange(n)        
    peak = np.random.randint(0, n)
    probs = np.exp(-0.5 * ((x - peak) / sigma) ** 2)
    probs = probs / probs.sum() * total_prob
    return probs