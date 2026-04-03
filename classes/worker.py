from numpy import random
from classes.utils import distribute_prob
from typing import TYPE_CHECKING, List, Dict
if TYPE_CHECKING:
    from classes.world import Zone, World


class Worker:
    def __init__(
        self,
        id: int,
        world: 'World',
        zone: 'Zone',
        type: int,
        fraud_prob: float,
        income: float,
        email: str,
        ring_id: int | None = None,
        ring_boost: float = 0.0,
    ) -> None:
        self.id = id
        self.world = world
        self.zone = zone
        self.type = type
        self.income = income
        self.email = email
        self.ring_id = ring_id
        self.ring_boost = ring_boost
        self.actions: List[str] = []
        self.is_fraud = False
        self.fraud_dist = distribute_prob(n=7, total_prob=fraud_prob, sigma=1.0)

        self.claim_history: List[Dict] = []

    def decide(self, day_idx: int, ring_pressure: bool = False) -> bool:
        filed = False
        reason = None

        if self.zone.civil_state == "lockdown" and self.zone.weather == "disaster":
            filed = True
            reason = "lockdown+disaster"
            self.is_fraud = False
        elif self.zone.civil_state == "lockdown":
            filed = True
            reason = "lockdown"
            self.is_fraud = False
        elif self.zone.weather == "disaster":
            filed = True
            reason = "disaster"
            self.is_fraud = False
        else:
            fraud_threshold = self.fraud_dist[day_idx]
            if ring_pressure and self.ring_id is not None:
                fraud_threshold = min(1.0, fraud_threshold + self.ring_boost)
            if random.random() < fraud_threshold:
                filed = True
                reason = "fraud_ring" if ring_pressure and self.ring_id is not None else "fraud"
                self.is_fraud = True

        if filed:
            self.claim_history.append({
                "day": self.world.days_passed,
                "day_name": self.world.day,
                "zone_id": self.zone.id,
                "reason": reason,
                "is_fraud": self.is_fraud,
                "ring_id": self.ring_id,
                "email": self.email,
            })

        return filed