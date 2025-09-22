"""
Exercise the new alert ingestion endpoints with realistic payloads.

Reads URL and TOKEN from environment or a .env file in the repo root.

Endpoints tested:
- POST /api/plugins/business-application/alerts/generic/
- POST /api/plugins/business-application/alerts/capacitor/
- POST /api/plugins/business-application/alerts/signalfx/
- POST /api/plugins/business-application/alerts/email/

The script prints concise results and HTTP statuses. Re-running will send
duplicate dedup_ids for some cases to verify update behavior.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict
import importlib


def _import_requests():
    try:
        return importlib.import_module("requests")  # type: ignore
    except Exception:  # pragma: no cover
        print("This script requires the 'requests' package. Please install it (e.g. pip install requests).", file=sys.stderr)
        raise


def load_env() -> Dict[str, str]:
    base_url = os.getenv("URL")
    token = os.getenv("TOKEN")
    if not base_url or not token:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(repo_root, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "URL" and not base_url:
                        base_url = v
                    if k == "TOKEN" and not token:
                        token = v
    if not base_url or not token:
        print("Missing URL or TOKEN. Set environment variables or create a .env with URL=... and TOKEN=...", file=sys.stderr)
        sys.exit(1)
    return {"URL": base_url.rstrip("/"), "TOKEN": token}


def client(env: Dict[str, str]):
    requests = _import_requests()
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Token {env['TOKEN']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    return s


def api_url(env: Dict[str, str], path: str) -> str:
    return f"{env['URL'].rstrip('/')}{'/' if not path.startswith('/') else ''}{path}"


def post_and_print(session, url: str, payload: Dict[str, object]):
    req = _import_requests()
    try:
        resp = session.post(url, json=payload)
    except req.exceptions.RequestException as exc:  # type: ignore[attr-defined]
        print(f"Request error for {url}: {exc}", file=sys.stderr)
        return

    status = resp.status_code
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    print(f"POST {url} -> {status}\n{json.dumps(body, indent=2) if isinstance(body, dict) else body}\n")


def test_generic(env: Dict[str, str], session):
    url = api_url(env, "/api/plugins/business-application/alerts/generic/")
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "source": "test-source",
        "timestamp": now,
        "severity": "high",
        "status": "triggered",
        "message": "CPU usage exceeded threshold",
        "dedup_id": "demo-generic-001",
        "target": {"type": "device", "identifier": "test-device-01"},
        "raw_data": {"metric": "cpu", "value": 95.2},
    }
    post_and_print(session, url, payload)


def test_capacitor(env: Dict[str, str], session):
    url = api_url(env, "/api/plugins/business-application/alerts/capacitor/")
    payload = {
        "alert_id": "CAP-2025-001",
        "device_name": "router-core-01",
        "description": "Interface eth0 down",
        "priority": 1,
        "state": "ALARM",
        "alert_time": "2025-01-10T10:00:00Z",
        "metric_name": "interface_status",
        "metric_value": 0,
        "threshold": 1
        }
    post_and_print(session, url, payload)


def test_signalfx(env: Dict[str, str], session):
    url = api_url(env, "/api/plugins/business-application/alerts/signalfx/")
    payload = {
        "incidentId": "sfx-001",
        "alertState": "TRIGGERED",
        "alertMessage": "API latency above SLO",
        "severity": "high",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "dimensions": {"host": "test-device-01"},
        "detectorName": "Latency SLO",
        "detectorUrl": "https://signalfx.example/detectors/123",
        "rule": "p95 > 300ms",
    }
    post_and_print(session, url, payload)


def test_email(env: Dict[str, str], session):
    url = api_url(env, "/api/plugins/business-application/alerts/email/")
    payload = {
        "message_id": "<demo-1@example.com>",
        "subject": "Server test-device-01 alert: memory high",
        "body": "Memory usage is over 90%",
        "sender": "monitor@example.com",
        "severity": "medium",
        "target_type": "device",
        "target_identifier": "test-device-01",
        "headers": {"X-Env": "demo"},
        "attachments": [],
    }
    post_and_print(session, url, payload)


def main():
    env = load_env()
    s = client(env)

    print(f"Testing alert ingestion endpoints against: {env['URL']}")
    test_generic(env, s)
    test_capacitor(env, s)
    test_signalfx(env, s)
    test_email(env, s)


if __name__ == "__main__":
    main()
