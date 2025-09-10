import argparse
import requests
import json
import uuid
from datetime import datetime, timezone

# The single, global endpoint for the PagerDuty Events API v2.
PAGERDUTY_EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"


def create_incident(integration_key: str, dedup_key: str):
    """
    Sends a 'trigger' event to the PagerDuty Events API to create a new incident.
    """
    print(f"--- Creating Incident ---")
    print(f"Targeting API Endpoint: {PAGERDUTY_EVENTS_API_URL}")
    print(f"Using dedup_key: {dedup_key}")

    # Generate a timestamp in ISO 8601 format with a Z for UTC.
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    # This payload contains all the details PagerDuty needs to create a rich incident.
    payload = {
        "routing_key": integration_key,
        "event_action": "trigger",
        "dedup_key": dedup_key,
        "client": "NetBox Simulation Script",
        "client_url": "https://github.com/your-repo/netbox-pagerduty-integration",
        "payload": {
            "summary": f"Simulated Alert: High latency on router NYC-CR01",
            "source": "netbox-simulation.local",
            "severity": "critical",
            "timestamp": timestamp,
            "component": "core-network",
            "group": "us-east-1",
            "class": "network-latency",
            # Custom details are where you can stuff any extra info from NetBox.
            "custom_details": {
                "NetBox Incident ID": "SIM-789",
                "Device Name": "NYC-CR01",
                "Device IP": "192.0.2.1",
                "Affected Services": ["VPN Gateway", "Public DNS"]
            }
        }
    }

    try:
        response = requests.post(PAGERDUTY_EVENTS_API_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        print("\n✅ PagerDuty API Call Successful!")
        print(f"   Status Code: {response.status_code}")
        print("   Response Body:")
        print(json.dumps(response.json(), indent=4))

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error calling PagerDuty API: {e}")
        if e.response:
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Response Body: {e.response.text}")


def resolve_incident(integration_key: str, dedup_key: str):
    """
    Sends a 'resolve' event to the PagerDuty Events API to resolve an existing incident.
    """
    if not dedup_key:
        print("\n❌ Error: You must provide a --dedup-key to resolve an incident.")
        return

    print(f"--- Resolving Incident ---")
    print(f"Targeting API Endpoint: {PAGERDUTY_EVENTS_API_URL}")
    print(f"Using dedup_key: {dedup_key}")


    # The payload to resolve an incident is much simpler.
    # The dedup_key is the crucial piece that links this event to the original trigger.
    payload = {
        "routing_key": integration_key,
        "event_action": "resolve",
        "dedup_key": dedup_key,
    }

    try:
        response = requests.post(PAGERDUTY_EVENTS_API_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        response.raise_for_status()

        print("\n✅ PagerDuty API Call Successful!")
        print(f"   Status Code: {response.status_code}")
        print("   Response Body:")
        print(json.dumps(response.json(), indent=4))

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error calling PagerDuty API: {e}")
        if e.response:
            print(f"   Status Code: {e.response.status_code}")
            print(f"   Response Body: {e.response.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate creating and resolving PagerDuty incidents using the official API.")

    parser.add_argument(
        "integration_key",
        help="Your PagerDuty Events API v2 integration key (routing key)."
    )
    parser.add_argument(
        "--action",
        choices=["create", "resolve"],
        required=True,
        help="The action to perform: 'create' a new incident or 'resolve' an existing one."
    )
    parser.add_argument(
        "--dedup-key",
        help="The de-duplication key. For 'create', a new UUID is generated if not provided. For 'resolve', this is required."
    )

    args = parser.parse_args()

    # If creating and no key is provided, generate a unique one. This simulates
    # how NetBox would use its own unique incident ID.
    dedup_key = args.dedup_key or f"simulated-incident-{uuid.uuid4()}"

    if args.action == "create":
        create_incident(args.integration_key, dedup_key)
    elif args.action == "resolve":
        resolve_incident(args.integration_key, args.dedup_key)

