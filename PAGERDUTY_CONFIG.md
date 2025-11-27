# PagerDuty Integration

This module provides integration between NetBox Business Application plugin and PagerDuty Events API v2.

## Overview

The integration automatically sends events to PagerDuty when:

- A new **Event** is created in NetBox
- A new **Incident** is created in NetBox
- An **Event** or **Incident** status changes (acknowledge, resolve)

## Requirements

- PagerDuty account with Events API v2 integration
- 32-character Integration Key (routing key) from PagerDuty

## Quick Start

### 1. Get your PagerDuty Integration Key

1. Log in to PagerDuty
2. Go to **Services** → Select your service (or create new)
3. Click **Integrations** tab
4. Add integration: **Events API v2**
5. Copy the **Integration Key** (32 characters)

### 2. Configure NetBox

Add to your `configuration.py`:

```python
PAGERDUTY_ENABLED = True
PAGERDUTY_ROUTING_KEY = 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
```

### 3. Test the Connection

```bash
curl -X POST "https://your-netbox/api/plugins/business-application/pagerduty/test/" \
  -H "Authorization: Token your-api-token" \
  -H "Content-Type: application/json"
```

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `PAGERDUTY_ENABLED` | `False` | Enable/disable PagerDuty integration |
| `PAGERDUTY_ROUTING_KEY` | `None` | **Required.** Your 32-character integration key |
| `PAGERDUTY_EVENTS_API_URL` | `https://events.pagerduty.com/v2/enqueue` | PagerDuty API endpoint |
| `PAGERDUTY_SOURCE` | `netbox` | Source identifier shown in PagerDuty |
| `PAGERDUTY_SEND_ON_EVENT_CREATE` | `True` | Send to PagerDuty when Events are created |
| `PAGERDUTY_SEND_ON_INCIDENT_CREATE` | `True` | Send to PagerDuty when Incidents are created |
| `PAGERDUTY_SEND_ON_INCIDENT_UPDATE` | `True` | Send updates when Incident status changes |
| `PAGERDUTY_AUTO_RESOLVE` | `True` | Auto-resolve PagerDuty when NetBox resolves |
| `PAGERDUTY_TIMEOUT` | `30` | HTTP timeout in seconds |
| `PAGERDUTY_COMPONENT` | `netbox-business-application` | Default component name |
| `PAGERDUTY_GROUP` | `infrastructure` | Default group name |
| `BASE_URL` | `None` | NetBox URL for links (e.g., `https://netbox.example.com`) |

## Example Configuration

```python
# configuration.py

# PagerDuty Integration
PAGERDUTY_ENABLED = True
PAGERDUTY_ROUTING_KEY = 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
PAGERDUTY_SOURCE = 'netbox-prod'
PAGERDUTY_COMPONENT = 'infrastructure-monitoring'
PAGERDUTY_GROUP = 'network-operations'

# For links back to NetBox in PagerDuty alerts
BASE_URL = 'https://netbox.company.com'
```

## API Endpoints

All endpoints require authentication via NetBox API token.

### Get Integration Status

```
GET /api/plugins/business-application/pagerduty/status/
```

Returns current configuration and status.

### Test Connection

```
POST /api/plugins/business-application/pagerduty/test/
```

Sends a test event to PagerDuty and immediately resolves it.

### Send Event to PagerDuty

```
POST /api/plugins/business-application/pagerduty/send-event/
Content-Type: application/json

{
    "event_id": 123
}
```

### Send Incident to PagerDuty

```
POST /api/plugins/business-application/pagerduty/send-incident/
Content-Type: application/json

{
    "incident_id": 123,
    "action": "trigger"  // or "acknowledge", "resolve"
}
```

### Resolve PagerDuty Event

```
POST /api/plugins/business-application/pagerduty/resolve-event/
Content-Type: application/json

{
    "event_id": 123
}
// or
{
    "dedup_key": "netbox-event-abc123"
}
```

### Trigger Custom Event

```
POST /api/plugins/business-application/pagerduty/trigger-custom/
Content-Type: application/json

{
    "summary": "Custom alert from NetBox",
    "severity": "warning",
    "source": "my-source",
    "dedup_key": "custom-key-123",
    "component": "my-component",
    "custom_details": {
        "key": "value"
    }
}
```

### Bulk Send Events

```
POST /api/plugins/business-application/pagerduty/bulk-send-events/
Content-Type: application/json

{
    "event_ids": [1, 2, 3, 4, 5]
}
```

## How It Works

### Event Flow

```
NetBox Event Created
        │
        ▼
   Status = triggered? ──No──► Status = ok/suppressed?
        │                              │
       Yes                            Yes
        │                              │
        ▼                              ▼
  PagerDuty TRIGGER            PagerDuty RESOLVE
```

### Incident Flow

```
NetBox Incident Created
        │
        ▼
  PagerDuty TRIGGER
        │
        ▼
  Status Changes?
        │
        ├── monitoring/resolved/closed ──► PagerDuty RESOLVE
        │
        └── acknowledged ──► PagerDuty ACKNOWLEDGE (if supported)
```

### Severity Mapping

| NetBox | PagerDuty |
|--------|-----------|
| CRITICAL | critical |
| HIGH | error |
| MEDIUM | warning |
| LOW | info |
| INFO | info |

### Deduplication

Events and incidents use unique deduplication keys:

- Events: `netbox-event-{event.dedup_id}`
- Incidents: `netbox-incident-{incident.id}`

This ensures:
- Updates don't create duplicate PagerDuty incidents
- Resolving in NetBox resolves the correct PagerDuty incident

## Programmatic Usage

You can also use the PagerDuty client directly in your code:

```python
from business_application.utils.pagerduty import (
    PagerDutyClient,
    send_event_to_pagerduty,
    send_incident_to_pagerduty,
)

# Using the client directly
client = PagerDutyClient()

# Trigger an event
client.trigger(
    summary="Database connection failed",
    severity="critical",
    source="db-server-01",
    dedup_key="db-conn-001"
)

# Acknowledge
client.acknowledge(dedup_key="db-conn-001")

# Resolve
client.resolve(dedup_key="db-conn-001")

# Using helper functions with NetBox models
from business_application.models import Event, Incident

event = Event.objects.get(pk=123)
send_event_to_pagerduty(event)

incident = Incident.objects.get(pk=456)
send_incident_to_pagerduty(incident)
```

## Troubleshooting

### Events not being sent

1. Check `PAGERDUTY_ENABLED = True`
2. Verify `PAGERDUTY_ROUTING_KEY` is set correctly
3. Check NetBox logs for errors
4. Test connection via API endpoint

### Wrong severity in PagerDuty

Check the severity/criticality field on your NetBox Event or Incident. See severity mapping table above.

### Links not working

Set `BASE_URL` in your configuration to your NetBox URL.

### Duplicate incidents in PagerDuty

This shouldn't happen due to deduplication keys. If it does, check that `dedup_id` is set on your Events.

## Logging

The integration logs to `business_application.pagerduty`. To enable debug logging:

```python
# configuration.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'business_application.pagerduty': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```