from numpy import random
from classes.utils import distribute_prob
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from classes.world import Zone, World

class Worker:
    def __init__(self, id: int, world: 'World', zone: 'Zone', type: int, fraud_prob: float, income: float) -> None:
        self.id = id
        self.world = world
        self.zone = zone
        self.type = type
        self.income = income
        self.is_fraud = False
        self.fraud_dist = distribute_prob(n=7, total_prob=fraud_prob, sigma=1.0)
    
    def decide(self, day_idx: int) -> bool:
        if self.zone.civil_state == "lockdown" or self.zone.weather == "disaster":
            return True
        if random.random() < self.fraud_dist[day_idx]:
            self.is_fraud = True
            return True
        return False