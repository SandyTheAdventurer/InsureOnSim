# utils.py

#### ` distribute_prob(n, total_prob=1.0, sigma=1.0) -> np.ndarray`
    
    parameters:
        n => No of parts to distribute into
        total_prob => Sum of n probabilities
        sigma => Variance of probabilities

    returns:
        np.ndarray[n] => n number of probabilities with a random peak