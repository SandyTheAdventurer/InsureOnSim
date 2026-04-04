import random
from typing import Any

import httpx


ZONE_TO_REGION = {
    "A": "mumbai",
    "B": "bengaluru",
    "C": "delhi",
}

PLATFORMS = ["swiggy", "zomato", "dunzo", "blinkit"]
SHIFTS = ["morning", "afternoon", "night"]


class BackendBridge:
    def __init__(self, base_url: str, sim_test_key: str, timeout_seconds: float = 20.0):
        self.base_url = base_url.rstrip("/").replace("://0.0.0.0", "://127.0.0.1")
        self.sim_test_key = sim_test_key
        self.timeout_seconds = timeout_seconds
        self._tokens_by_worker_id: dict[int, str] = {}
        self._password_by_worker_id: dict[int, str] = {}

    def _backend_email_for_worker(self, worker_id: int) -> str:
        # Keep a standards-compliant email for backend validation.
        return f"worker{worker_id}@sim.insureon.dev"

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            return client.request(method, path, **kwargs)

    def _auth_headers(self, token: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _sim_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "x-sim-test-key": self.sim_test_key,
        }

    def _password_for_worker(self, worker_id: int) -> str:
        if worker_id not in self._password_by_worker_id:
            self._password_by_worker_id[worker_id] = f"sim-worker-{worker_id}-pass"
        return self._password_by_worker_id[worker_id]

    def _login(self, email: str, password: str) -> str:
        resp = self._request(
            "POST",
            "/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        body = resp.json()
        return body["access_token"]

    def _ensure_user_token(self, worker) -> tuple[str, str]:
        if worker.id in self._tokens_by_worker_id:
            return self._tokens_by_worker_id[worker.id], "reused"

        password = self._password_for_worker(worker.id)
        backend_email = self._backend_email_for_worker(worker.id)
        signup_payload = {
            "email": backend_email,
            "password": password,
            "platform": random.choice(PLATFORMS),
            "region": ZONE_TO_REGION.get(worker.zone.type, "delhi"),
            "income": int(worker.income),
            "pincode": f"560{worker.id % 1000:03d}",
            "upi_id": f"worker{worker.id}@oksbi",
        }

        signup_resp = self._request("POST", "/signup", json=signup_payload)
        if signup_resp.status_code == 200:
            token = signup_resp.json()["access_token"]
            self._tokens_by_worker_id[worker.id] = token
            return token, "signed_up"

        if signup_resp.status_code == 422:
            try:
                detail = signup_resp.json().get("detail", signup_resp.text)
            except Exception:
                detail = signup_resp.text
            raise ValueError(f"Signup validation failed for worker {worker.id}: {detail}")

        if signup_resp.status_code != 400:
            signup_resp.raise_for_status()

        token = self._login(backend_email, password)
        self._tokens_by_worker_id[worker.id] = token
        return token, "logged_in"

    def _ensure_profile(self, worker, token: str) -> str:
        params = {
            "pincode": f"560{worker.id % 1000:03d}",
            "avg_weekly_hours": 48 if worker.type == 1 else 28,
            "primary_shift": random.choice(SHIFTS),
            "is_multi_platform": worker.type == 1,
        }
        resp = self._request(
            "POST",
            "/workers/profile",
            params=params,
            headers=self._auth_headers(token),
        )
        if resp.status_code in (200, 201):
            return "created"
        if resp.status_code == 400 and "already exists" in resp.text.lower():
            return "exists"
        resp.raise_for_status()
        return "unknown"

    def _ensure_paid_policy(self, token: str) -> str:
        active_resp = self._request("GET", "/policies/active", headers=self._auth_headers(token))
        if active_resp.status_code == 200:
            return "already_active"

        issue_resp = self._request("POST", "/policies/issue", headers=self._auth_headers(token))
        if issue_resp.status_code == 200:
            policy_id = issue_resp.json()["id"]
            pay_resp = self._request("POST", f"/policies/{policy_id}/pay", headers=self._auth_headers(token))
            pay_resp.raise_for_status()
            return "issued_and_paid"

        if issue_resp.status_code == 400 and "already issued" in issue_resp.text.lower():
            history_resp = self._request("GET", "/policies/history", headers=self._auth_headers(token))
            history_resp.raise_for_status()
            history = history_resp.json()
            if history:
                latest = history[0]
                if not latest.get("is_paid", False):
                    pay_resp = self._request("POST", f"/policies/{latest['id']}/pay", headers=self._auth_headers(token))
                    pay_resp.raise_for_status()
                    return "paid_existing"
                return "existing_paid"
            return "no_policy_history"

        issue_resp.raise_for_status()
        return "unknown"

    def onboard_worker(self, worker) -> dict[str, Any]:
        token, auth_status = self._ensure_user_token(worker)
        profile_status = self._ensure_profile(worker, token)
        policy_status = self._ensure_paid_policy(token)

        return {
            "worker_id": worker.id,
            "email": worker.email,
            "auth_status": auth_status,
            "profile_status": profile_status,
            "policy_status": policy_status,
        }

    def onboard_workers(self, workers: list, limit: int | None = None) -> dict[str, Any]:
        selected = workers[:limit] if limit else workers
        results = []
        failures = []

        for worker in selected:
            try:
                results.append(self.onboard_worker(worker))
            except Exception as exc:
                failures.append({
                    "worker_id": worker.id,
                    "email": worker.email,
                    "error": str(exc),
                })

        return {
            "requested": len(selected),
            "onboarded": len(results),
            "failed": len(failures),
            "results": results,
            "failures": failures,
        }

    def trigger_zone(self, zone_id: int, zone_type: str, day_number: int, reason: str) -> dict[str, Any]:
        district = f"sim-zone-{zone_id}-day-{day_number}-{reason}"
        payload = {
            "district": district,
            "zone": zone_type,
            "alert_color": "RED",
        }
        resp = self._request(
            "POST",
            "/claims/sim/trigger",
            json=payload,
            headers=self._sim_headers(),
        )
        resp.raise_for_status()
        body = resp.json()
        return {
            "zone_id": zone_id,
            "zone_type": zone_type,
            "district": district,
            "claims_opened": body.get("claims_opened", 0),
        }

    def trigger_from_weather_alerts(self, weather_alerts: list[dict[str, Any]], day_number: int) -> dict[str, Any]:
        unique_zone_alert: dict[tuple[int, str], dict[str, Any]] = {}

        for alert_entry in weather_alerts:
            zone_id = int(alert_entry["zone_id"])
            zone_type = alert_entry["zone_type"]
            alert_value = alert_entry.get("alert", "weather")
            if isinstance(alert_value, list):
                alert_name = "+".join(sorted(str(item) for item in alert_value))
            else:
                alert_name = str(alert_value)

            key = (zone_id, alert_name)
            if key not in unique_zone_alert:
                unique_zone_alert[key] = {
                    "zone_id": zone_id,
                    "zone_type": zone_type,
                    "alert_name": alert_name,
                }

        triggers = []
        for (_, alert_name), entry in unique_zone_alert.items():
            triggers.append(
                self.trigger_zone(
                    zone_id=entry["zone_id"],
                    zone_type=entry["zone_type"],
                    day_number=day_number,
                    reason=f"weather-{alert_name}",
                )
            )

        return {
            "trigger_count": len(triggers),
            "claims_opened_total": sum(t["claims_opened"] for t in triggers),
            "triggers": triggers,
        }

    def process_monitoring_day(self) -> dict[str, Any]:
        resp = self._request(
            "POST",
            "/claims/sim/process-monitoring",
            headers=self._sim_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def trigger_from_claims(self, claims_today: list[dict[str, Any]], day_number: int) -> dict[str, Any]:
        legitimate = [c for c in claims_today if not c.get("is_fraud", False)]
        unique_zone_reason: dict[tuple[int, str], dict[str, Any]] = {}
        for claim in legitimate:
            key = (claim["zone_id"], claim["reason"])
            if key not in unique_zone_reason:
                unique_zone_reason[key] = claim

        triggers = []
        for (_, reason), claim in unique_zone_reason.items():
            triggers.append(
                self.trigger_zone(
                    zone_id=claim["zone_id"],
                    zone_type=claim["zone_type"],
                    day_number=day_number,
                    reason=reason,
                )
            )

        return {
            "trigger_count": len(triggers),
            "claims_opened_total": sum(t["claims_opened"] for t in triggers),
            "triggers": triggers,
        }

    def count_active_claims_for_onboarded(self) -> int:
        count = 0
        for token in self._tokens_by_worker_id.values():
            resp = self._request("GET", "/claims/active", headers=self._auth_headers(token))
            if resp.status_code == 200:
                count += 1
        return count

    def collect_fraud_audit(self) -> dict[str, Any]:
        total_claims = 0
        flagged_claims = 0
        rejected_claims = 0
        manual_review_claims = 0
        flagged_and_rejected = 0
        evaluations_run = 0

        for token in self._tokens_by_worker_id.values():
            history_resp = self._request("GET", "/claims/history", headers=self._auth_headers(token))
            history_resp.raise_for_status()
            claims = history_resp.json()

            for claim in claims:
                total_claims += 1
                claim_id = claim["id"]

                eval_resp = self._request(
                    "POST",
                    f"/claims/{claim_id}/evaluate-fraud",
                    headers=self._auth_headers(token),
                )
                eval_resp.raise_for_status()
                evaluations_run += 1

                refreshed_resp = self._request(
                    "GET",
                    f"/claims/{claim_id}",
                    headers=self._auth_headers(token),
                )
                refreshed_resp.raise_for_status()
                refreshed_claim = refreshed_resp.json()

                is_flagged = bool(refreshed_claim.get("is_fraud_flagged", False))
                status = refreshed_claim.get("status")

                if is_flagged:
                    flagged_claims += 1
                if status == "rejected":
                    rejected_claims += 1
                if status == "manual_review":
                    manual_review_claims += 1
                if is_flagged and status == "rejected":
                    flagged_and_rejected += 1

        return {
            "total_claims": total_claims,
            "evaluations_run": evaluations_run,
            "flagged_claims": flagged_claims,
            "rejected_claims": rejected_claims,
            "manual_review_claims": manual_review_claims,
            "flagged_and_rejected": flagged_and_rejected,
            "flagged_rejection_rate": (
                round((flagged_and_rejected / flagged_claims) * 100, 2)
                if flagged_claims > 0
                else 0.0
            ),
        }

    def collect_app_audit(self) -> dict[str, Any]:
        checks = [
            ("/dashboard/summary", "dashboard_ok"),
            ("/workers/profile", "profile_ok"),
            ("/workers/risk-score", "risk_ok"),
            ("/workers/smartwork", "smartwork_ok"),
            ("/policies/active", "policy_active_ok"),
            ("/policies/history", "policy_history_ok"),
            ("/payouts/history", "payouts_history_ok"),
            ("/claims/history", "claim_history_ok"),
        ]

        counters = {key: 0 for (_, key) in checks}
        failures = []

        for worker_id, token in self._tokens_by_worker_id.items():
            for endpoint, key in checks:
                resp = self._request("GET", endpoint, headers=self._auth_headers(token))
                if resp.status_code == 200:
                    counters[key] += 1
                    continue

                try:
                    detail = resp.json()
                except Exception:
                    detail = resp.text

                failures.append({
                    "worker_id": worker_id,
                    "endpoint": endpoint,
                    "status_code": resp.status_code,
                    "detail": str(detail),
                })

        return {
            "workers_checked": len(self._tokens_by_worker_id),
            **counters,
            "failures": failures,
        }

    def collect_worker_flag_summary(self) -> dict[str, Any]:
        flagged_workers = set()
        onboarded_workers = list(self._tokens_by_worker_id.keys())
        claims_checked = 0

        for worker_id, token in self._tokens_by_worker_id.items():
            history_resp = self._request("GET", "/claims/history", headers=self._auth_headers(token))
            history_resp.raise_for_status()
            claims = history_resp.json()

            for claim in claims:
                claims_checked += 1
                claim_id = claim.get("id")
                if claim.get("fraud_probability") is None and claim_id is not None:
                    eval_resp = self._request(
                        "POST",
                        f"/claims/{claim_id}/evaluate-fraud",
                        headers=self._auth_headers(token),
                    )
                    eval_resp.raise_for_status()
                    refreshed_resp = self._request(
                        "GET",
                        f"/claims/{claim_id}",
                        headers=self._auth_headers(token),
                    )
                    refreshed_resp.raise_for_status()
                    claim = refreshed_resp.json()

                if bool(claim.get("is_fraud_flagged", False)):
                    flagged_workers.add(worker_id)

        return {
            "onboarded_worker_ids": onboarded_workers,
            "flagged_workers": sorted(flagged_workers),
            "claims_checked": claims_checked,
        }
