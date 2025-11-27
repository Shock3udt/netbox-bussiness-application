"""
Exercise the PagerDuty integration endpoints.

Reads URL and TOKEN from environment or a .env file in the repo root.

Endpoints tested:
- GET  /api/plugins/business-application/pagerduty/status/
- POST /api/plugins/business-application/pagerduty/test/
- POST /api/plugins/business-application/pagerduty/trigger-custom/
- POST /api/plugins/business-application/pagerduty/send-event/
- POST /api/plugins/business-application/pagerduty/send-incident/
- POST /api/plugins/business-application/pagerduty/resolve-event/
- POST /api/plugins/business-application/pagerduty/bulk-send-events/

The script prints concise results and HTTP statuses.
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict
import importlib


def _import_requests():
    try:
        return importlib.import_module("requests")
    except Exception:
        print("This script requires the 'requests' package. Please install it (e.g. pip install requests).",
              file=sys.stderr)
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
        print("Missing URL or TOKEN. Set environment variables or create a .env with URL=... and TOKEN=...",
              file=sys.stderr)
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


def get_and_print(session, url: str):
    req = _import_requests()
    try:
        resp = session.get(url)
    except req.exceptions.RequestException as exc:
        print(f"Request error for {url}: {exc}", file=sys.stderr)
        return None

    status = resp.status_code
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    print(f"GET {url} -> {status}\n{json.dumps(body, indent=2) if isinstance(body, dict) else body}\n")
    return body


def post_and_print(session, url: str, payload: Dict[str, object] = None):
    req = _import_requests()
    try:
        resp = session.post(url, json=payload or {})
    except req.exceptions.RequestException as exc:
        print(f"Request error for {url}: {exc}", file=sys.stderr)
        return None

    status = resp.status_code
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    print(f"POST {url} -> {status}\n{json.dumps(body, indent=2) if isinstance(body, dict) else body}\n")
    return body


def test_status(env: Dict[str, str], session):
    """Test GET /pagerduty/status/ endpoint."""
    print("=" * 60)
    print("Testing: PagerDuty Status")
    print("=" * 60)
    url = api_url(env, "/api/plugins/business-application/pagerduty/status/")
    return get_and_print(session, url)


def test_connection(env: Dict[str, str], session):
    """Test POST /pagerduty/test/ endpoint."""
    print("=" * 60)
    print("Testing: PagerDuty Connection Test")
    print("=" * 60)
    url = api_url(env, "/api/plugins/business-application/pagerduty/test/")
    return post_and_print(session, url)


def test_trigger_custom(env: Dict[str, str], session):
    """Test POST /pagerduty/trigger-custom/ endpoint."""
    print("=" * 60)
    print("Testing: Trigger Custom PagerDuty Event")
    print("=" * 60)
    url = api_url(env, "/api/plugins/business-application/pagerduty/trigger-custom/")
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "summary": f"Test alert from NetBox at {now}",
        "severity": "warning",
        "source": "netbox-test-script",
        "dedup_key": "test-custom-event-001",
        "component": "test-component",
        "group": "test-group",
        "event_class": "test",
        "custom_details": {
            "test_run": True,
            "timestamp": now,
            "script": "test_pagerduty_endpoints.py"
        }
    }
    return post_and_print(session, url, payload)


def test_resolve_custom(env: Dict[str, str], session):
    """Test POST /pagerduty/resolve-event/ endpoint with dedup_key."""
    print("=" * 60)
    print("Testing: Resolve Custom PagerDuty Event")
    print("=" * 60)
    url = api_url(env, "/api/plugins/business-application/pagerduty/resolve-event/")
    payload = {
        "dedup_key": "test-custom-event-001"
    }
    return post_and_print(session, url, payload)


def test_send_event(env: Dict[str, str], session, event_id: int = None):
    """Test POST /pagerduty/send-event/ endpoint."""
    print("=" * 60)
    print("Testing: Send NetBox Event to PagerDuty")
    print("=" * 60)

    if not event_id:
        # Try to get first available event
        events_url = api_url(env, "/api/plugins/business-application/events/")
        req = _import_requests()
        try:
            resp = session.get(events_url, params={"limit": 1})
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    event_id = results[0].get("id")
        except Exception as e:
            print(f"Could not fetch events: {e}")

    if not event_id:
        print("No event_id provided and no events found. Skipping test.\n")
        return None

    url = api_url(env, "/api/plugins/business-application/pagerduty/send-event/")
    payload = {"event_id": event_id}
    return post_and_print(session, url, payload)


def test_send_incident(env: Dict[str, str], session, incident_id: int = None):
    """Test POST /pagerduty/send-incident/ endpoint."""
    print("=" * 60)
    print("Testing: Send NetBox Incident to PagerDuty")
    print("=" * 60)

    if not incident_id:
        # Try to get first available incident
        incidents_url = api_url(env, "/api/plugins/business-application/incidents/")
        req = _import_requests()
        try:
            resp = session.get(incidents_url, params={"limit": 1})
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    incident_id = results[0].get("id")
        except Exception as e:
            print(f"Could not fetch incidents: {e}")

    if not incident_id:
        print("No incident_id provided and no incidents found. Skipping test.\n")
        return None

    url = api_url(env, "/api/plugins/business-application/pagerduty/send-incident/")
    payload = {
        "incident_id": incident_id,
        "action": "trigger"
    }
    return post_and_print(session, url, payload)


def test_resolve_event_by_id(env: Dict[str, str], session, event_id: int = None):
    """Test POST /pagerduty/resolve-event/ endpoint with event_id."""
    print("=" * 60)
    print("Testing: Resolve PagerDuty Event by NetBox Event ID")
    print("=" * 60)

    if not event_id:
        # Try to get first available event
        events_url = api_url(env, "/api/plugins/business-application/events/")
        req = _import_requests()
        try:
            resp = session.get(events_url, params={"limit": 1})
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    event_id = results[0].get("id")
        except Exception as e:
            print(f"Could not fetch events: {e}")

    if not event_id:
        print("No event_id provided and no events found. Skipping test.\n")
        return None

    url = api_url(env, "/api/plugins/business-application/pagerduty/resolve-event/")
    payload = {"event_id": event_id}
    return post_and_print(session, url, payload)


def test_bulk_send_events(env: Dict[str, str], session, event_ids: list = None):
    """Test POST /pagerduty/bulk-send-events/ endpoint."""
    print("=" * 60)
    print("Testing: Bulk Send Events to PagerDuty")
    print("=" * 60)

    if not event_ids:
        # Try to get first 3 available events
        events_url = api_url(env, "/api/plugins/business-application/events/")
        req = _import_requests()
        try:
            resp = session.get(events_url, params={"limit": 3})
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                event_ids = [e.get("id") for e in results if e.get("id")]
        except Exception as e:
            print(f"Could not fetch events: {e}")

    if not event_ids:
        print("No event_ids provided and no events found. Skipping test.\n")
        return None

    url = api_url(env, "/api/plugins/business-application/pagerduty/bulk-send-events/")
    payload = {"event_ids": event_ids}
    return post_and_print(session, url, payload)


def test_invalid_requests(env: Dict[str, str], session):
    """Test error handling with invalid requests."""
    print("=" * 60)
    print("Testing: Error Handling")
    print("=" * 60)

    # Test missing event_id
    print("--- Missing event_id ---")
    url = api_url(env, "/api/plugins/business-application/pagerduty/send-event/")
    post_and_print(session, url, {})

    # Test invalid event_id
    print("--- Invalid event_id ---")
    post_and_print(session, url, {"event_id": 999999999})

    # Test missing summary for custom trigger
    print("--- Missing summary ---")
    url = api_url(env, "/api/plugins/business-application/pagerduty/trigger-custom/")
    post_and_print(session, url, {"severity": "warning"})

    # Test invalid severity
    print("--- Invalid severity ---")
    post_and_print(session, url, {"summary": "Test", "severity": "invalid"})


def main():
    env = load_env()
    s = client(env)

    print(f"\nTesting PagerDuty integration endpoints against: {env['URL']}\n")

    # 1. Check status first
    status = test_status(env, s)

    if status and not status.get("enabled"):
        print("\n" + "!" * 60)
        print("WARNING: PagerDuty is not enabled in NetBox configuration!")
        print("Some tests will fail or return errors.")
        print("!" * 60 + "\n")

    if status and not status.get("configured"):
        print("\n" + "!" * 60)
        print("WARNING: PagerDuty routing key is not configured!")
        print("Tests that send to PagerDuty will fail.")
        print("!" * 60 + "\n")

    # 2. Test connection
    test_connection(env, s)

    # 3. Test custom event trigger and resolve
    test_trigger_custom(env, s)
    test_resolve_custom(env, s)

    # 4. Test sending NetBox objects
    test_send_event(env, s)
    test_send_incident(env, s)

    # 5. Test bulk operations
    test_bulk_send_events(env, s)

    # 6. Test resolve by event ID
    test_resolve_event_by_id(env, s)

    # 7. Test error handling
    test_invalid_requests(env, s)

    print("=" * 60)
    print("PagerDuty endpoint tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()