from typing import List, Tuple
try:
    from .utils import distribute_prob
    from .worker import Worker
    from .models import DaySummary
except ImportError:
    from classes.utils import distribute_prob
    from classes.worker import Worker
    from classes.models import DaySummary
import numpy.random as random

class Zone:
    def __init__(self, id: int, type: str, n_connections: int, hostpot_type: int, event_prob: float, event_info: str) -> None:
        self.id = id
        self.type = type
        self.n_connections = n_connections
        self.nearby_zones = dict()
        self.civil_state = "stable"
        self.weather = "clear"
        self.alerts = []
        self.hostpot_type = hostpot_type
        self.event_prob_dist = distribute_prob(n=7, total_prob=event_prob, sigma=1.0)
        self.event_info = event_info

    def add_connection(self, other_zone: 'Zone', max_zone_distance: int, min_zone_distance: int, update_probs = True) -> None:
        if other_zone not in self.nearby_zones:
            distance = random.randint(min_zone_distance, max_zone_distance)
            if update_probs:
                other_zone.event_prob_dist = distribute_prob(n=7, total_prob=other_zone.event_prob_dist.sum() + self.event_prob_dist.sum() * distance / (max_zone_distance - min_zone_distance) if max_zone_distance != min_zone_distance else 0, sigma=1.0)
            self.nearby_zones[other_zone.id] = distance
            if self.id not in other_zone.nearby_zones:
                other_zone.add_connection(self, max_zone_distance, min_zone_distance, update_probs=False)

    def trigger_event(self, day_idx: int) -> Tuple[bool, bool, str]:
        if self.hostpot_type > 0 and random.random() < self.event_prob_dist[day_idx]:
            if self.hostpot_type == 1:
                self.civil_state = "lockdown"
                self.alerts.append("lockdown")
                return True, False, "lockdown"
            elif self.hostpot_type == 2:
                self.weather = "disaster"
                self.alerts.append(self.event_info)
                return False, True, self.event_info
            elif self.hostpot_type == 3:
                self.civil_state = "lockdown"
                self.weather = "disaster"
                self.alerts.append("lockdown")
                self.alerts.append(self.event_info)
                return True, True, f"lockdown + {self.event_info}"
        return False, False, ""

class World:
    def __init__(self, seed: int, n_zones: int, n_users: int, zone_types: list, weather_disaster_types: list,
                 min_zone_connections: int, max_zone_connections: int, min_zone_distance: int, max_zone_distance: int,
                 fraud_fraction: float, worker_type_fraction: float, income_range: tuple, lockdown_hotspot_fraction: float, disaster_hotspot_fraction: float,
                 hotspot_event_prob: float, len_actions: int, fraud_ring_fraction: float = 0.35,
                 min_fraud_ring_size: int = 2, max_fraud_ring_size: int = 5,
                 fraud_ring_activation_prob: float = 0.6, fraud_ring_boost: float = 0.25) -> None:
        self.seed = seed
        self.n_zones = n_zones
        self.n_users = n_users
        self.zone_types = zone_types
        self.weather_disaster_types = weather_disaster_types
        self.min_zone_connections = min_zone_connections
        self.max_zone_connections = max_zone_connections
        self.min_zone_distance = min_zone_distance
        self.max_zone_distance = max_zone_distance
        self.fraud_fraction = fraud_fraction
        self.worker_type_fraction = worker_type_fraction
        self.income_range = income_range
        self.lockdown_hotspot_fraction = lockdown_hotspot_fraction
        self.disaster_hotspot_fraction = disaster_hotspot_fraction
        self.hotspot_event_prob = hotspot_event_prob
        self.len_actions = len_actions
        self.fraud_ring_fraction = min(max(fraud_ring_fraction, 0.0), 1.0)
        self.min_fraud_ring_size = max(2, min_fraud_ring_size)
        self.max_fraud_ring_size = max(self.min_fraud_ring_size, max_fraud_ring_size)
        self.fraud_ring_activation_prob = min(max(fraud_ring_activation_prob, 0.0), 1.0)
        self.fraud_ring_boost = max(0.0, fraud_ring_boost)

        self.days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.day_idx = 0
        self.day = self.days_of_week[self.day_idx]
        self.days_passed = 0
        self.zones = {}
        self.workers = {}
        self.fraud_rings = {}

        random.seed(seed)

    def setup_zones(self):
        for i in range(self.n_zones):
            rnd = random.random(2)
            hotspot_type = 3 if rnd[0] < self.lockdown_hotspot_fraction and rnd[1] < self.disaster_hotspot_fraction else (
                2 if rnd[0] < self.lockdown_hotspot_fraction else (
                1 if rnd[1] < self.disaster_hotspot_fraction else 0))
            zone = Zone(
                id=i,
                type=random.choice(self.zone_types),
                n_connections=random.randint(self.min_zone_connections, self.max_zone_connections),
                hostpot_type=hotspot_type,
                event_prob=self.hotspot_event_prob if hotspot_type > 0 else 0,
                event_info=random.choice(self.weather_disaster_types) if hotspot_type >= 2 else ("lockdown" if hotspot_type == 1 else "")
            )
            self.zones[zone.id] = zone

        for zone in self.zones.values():
            candidates = [z for z in self.zones.values() if z != zone]
            random.shuffle(candidates)
            needed = zone.n_connections - len(zone.nearby_zones)
            for other_zone in candidates[:needed]:
                if other_zone not in zone.nearby_zones:
                    zone.add_connection(other_zone, self.max_zone_distance, self.min_zone_distance)

    def setup_workers(self):
        workers_created = []
        for i in range(self.n_users):
            zone = random.choice(list(self.zones.values()))
            worker_type = 1 if random.random() < self.worker_type_fraction else 0
            if random.random() < self.fraud_fraction:
                fraud_prob = random.uniform(0.5, 1.0)
            else:
                fraud_prob = random.uniform(0.0, 0.5)
            income = int(random.uniform(*self.income_range))
            actions=[]
            email = f"worker{i}@insureonsim.local"
            worker = Worker(id=i,
                            world=self,
                            zone=zone,
                            type=worker_type,
                            fraud_prob=fraud_prob,
                            income=income,
                            email=email,
                            ring_boost=self.fraud_ring_boost,
                            )
            actions=self.worker_daily_action(worker)
            worker.actions=actions
            self.workers[worker.id] = worker
            workers_created.append(worker)

        self._assign_fraud_rings(workers_created)

    def _assign_fraud_rings(self, workers: List[Worker]) -> None:
        self.fraud_rings = {}
        fraud_candidates = [w for w in workers if float(w.fraud_dist.sum()) >= 0.5]
        if len(fraud_candidates) < self.min_fraud_ring_size:
            return

        random.shuffle(fraud_candidates)
        target_members = max(
            self.min_fraud_ring_size,
            int(len(fraud_candidates) * self.fraud_ring_fraction),
        )
        target_members = min(target_members, len(fraud_candidates))
        selected = fraud_candidates[:target_members]

        ring_id = 0
        idx = 0
        while idx < len(selected):
            remaining = len(selected) - idx
            ring_size = random.randint(self.min_fraud_ring_size, self.max_fraud_ring_size)
            if remaining < self.min_fraud_ring_size:
                break
            ring_size = min(ring_size, remaining)
            if remaining - ring_size == 1:
                ring_size += 1

            members = selected[idx: idx + ring_size]
            for member in members:
                member.ring_id = ring_id
            self.fraud_rings[ring_id] = [member.id for member in members]

            ring_id += 1
            idx += ring_size

    def run_day(self):
        self.days_passed += 1
        self.day_idx = (self.day_idx + 1) % 7
        self.day = self.days_of_week[self.day_idx]

        for zone in self.zones.values():
            zone.civil_state = "stable"
            zone.weather = "clear"
            zone.alerts = []

        for zone in self.zones.values():
            zone.trigger_event(self.day_idx)

        for worker in self.workers.values():
            worker.is_fraud = False
            worker.actions = self.worker_daily_action(worker)

    def get_weather_alerts(self):
        alerts = []
        for zone in self.zones.values():
            if zone.weather == "disaster" or any(a in self.weather_disaster_types for a in zone.alerts):
                alerts.append({
                    "zone_id": zone.id,
                    "zone_type": zone.type,
                    "alert": zone.event_info if zone.weather == "disaster" else zone.alerts,
                })
        return alerts

    def get_government_alerts(self):
        alerts = []
        for zone in self.zones.values():
            if zone.civil_state == "lockdown" or "lockdown" in zone.alerts:
                alerts.append({
                    "zone_id": zone.id,
                    "zone_type": zone.type,
                    "alert": "lockdown",
                })
        return alerts

    def get_day_summary(self):
        summary = {
            'lockdown': 0,
            'stable': 0,
            'other_civil': 0,
            'weather_disaster': 0,
            'weather_clear': 0,
            'other_weather': 0
        }
        for zone in self.zones.values():
            if zone.civil_state == 'lockdown':
                summary['lockdown'] += 1
            elif zone.civil_state == 'stable':
                summary['stable'] += 1
            else:
                summary['other_civil'] += 1
            if zone.weather == 'disaster':
                summary['weather_disaster'] += 1
            elif zone.weather == 'clear':
                summary['weather_clear'] += 1
            else:
                summary['other_weather'] += 1
        return DaySummary(**summary)

    def worker_daily_action(self, worker: Worker):
        total_actions = [
            "long commute single delivery",
            "long commute multiple deliveries",
            "short commute multiple deliveries",
            "short commute single delivery",
            "leisure",
        ]
        actions = []
        n_prob = self.len_actions
        peak = None
        if worker.type == 0:
            peak = 2

        for _ in range(n_prob):
            prob = distribute_prob(n=5, peak=peak)
            rand = random.random()
            cumulative_prob = 0
            action = 0
            for j, p in enumerate(prob):
                cumulative_prob += p
                if rand < cumulative_prob:
                    action = j
                    break
            actions.append(total_actions[action])

        if worker.type == 0:
            actions.extend(["leisure"] * n_prob)

        return actions
    def process_claims(self):
        """
        Calls decide() on every worker for the current day.
        Returns a list of claim dicts for workers who filed a claim today.
        """
        claims = []
        active_rings = {
            ring_id for ring_id in self.fraud_rings
            if random.random() < self.fraud_ring_activation_prob
        }
        for worker in self.workers.values():
            ring_pressure = worker.ring_id in active_rings if worker.ring_id is not None else False
            filed = worker.decide(self.day_idx, ring_pressure=ring_pressure)
            if filed:
                latest = worker.claim_history[-1]
                claims.append({
                    "worker_id": worker.id,
                    "email": worker.email,
                    "zone_id": worker.zone.id,
                    "zone_type": worker.zone.type,
                    "income": worker.income,
                    "worker_type": worker.type,
                    "reason": latest["reason"],
                    "is_fraud": latest["is_fraud"],
                    "ring_id": latest["ring_id"],
                    "day": latest["day"],
                    "day_name": latest["day_name"],
                })
        return claims

    def get_worker_platform_metrics(self, worker_id: int) -> dict:
        worker = self.workers.get(worker_id)
        if worker is None:
            raise KeyError(f"Worker {worker_id} not found")

        # If a major disruption is active in the worker's zone, assume zero work today.
        if worker.zone.civil_state == "lockdown" or worker.zone.weather == "disaster":
            return {
                "worker_id": worker.id,
                "day": self.days_passed,
                "day_name": self.day,
                "platform_logged_in": False,
                "income_earned": 0.0,
            }

        action_weight = {
            "long commute single delivery": 0.18,
            "long commute multiple deliveries": 0.30,
            "short commute multiple deliveries": 0.34,
            "short commute single delivery": 0.22,
            "leisure": 0.0,
        }
        action_score = sum(action_weight.get(action, 0.0) for action in worker.actions)
        max_score = max(len(worker.actions) * 0.34, 1.0)
        normalized = min(action_score / max_score, 1.0)

        base_daily_income = float(worker.income) / 6.0
        platform_logged_in = any(action != "leisure" for action in worker.actions)
        income_earned = round(base_daily_income * normalized, 2) if platform_logged_in else 0.0

        return {
            "worker_id": worker.id,
            "day": self.days_passed,
            "day_name": self.day,
            "platform_logged_in": platform_logged_in,
            "income_earned": income_earned,
        }

    def simulate(self, n_days: int, logger=None):
        for day in range(n_days):
            if logger:
                logger.info(f"\n--- Day {day+1}: {self.day} ---")
            self.run_day()
            summary = self.get_day_summary()
            if logger:
                logger.info(f"Day summary: Lockdown: {summary.lockdown}, Stable: {summary.stable}, Weather Disaster: {summary.weather_disaster}, Weather Clear: {summary.weather_clear}")