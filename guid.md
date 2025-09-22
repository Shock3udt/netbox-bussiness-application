# NetBox Business Application Plugin - Incident Auto-Creation Integration Guide

This guide shows how to integrate the automatic incident creation system into your NetBox business application plugin.

## Overview

The incident auto-creation system automatically groups related alerts into incidents by analyzing the NetBox dependency map. When events/alerts come in, the system:

1. **Identifies affected components** (devices, VMs, services)
2. **Finds dependency relationships** between components  
3. **Correlates events** based on common parent services
4. **Groups related alerts** into single incidents
5. **Reduces noise** and defines blast radius

## Installation Steps

### 1. Add Files to Your Plugin Structure

```
business_application/
├── services/
│   ├── __init__.py
│   └── incident_service.py          # Main incident creation logic
├── management/
│   └── commands/
│       ├── __init__.py
│       └── process_incidents.py     # Management command for batch processing
├── api/
│   ├── incident_automation_views.py # API endpoints for automation control
│   └── urls.py                      # Updated with new endpoints
├── signals.py                       # Auto-processing when events are created
├── apps.py                          # Updated to register signals
├── config.py                        # Configuration settings
└── notifications.py                 # Webhook notification system
```

### 2. Update Your Django Settings

Add these settings to your `settings.py`:

```python
# Business Application Plugin - Incident Automation Settings
BUSINESS_APP_AUTO_INCIDENTS_ENABLED = True
BUSINESS_APP_AUTO_RESOLVE_INCIDENTS = True
BUSINESS_APP_CORRELATION_WINDOW_MINUTES = 15
BUSINESS_APP_MAX_DEPENDENCY_DEPTH = 5
BUSINESS_APP_CORRELATION_THRESHOLD = 0.3
BUSINESS_APP_INCIDENT_NOTIFICATIONS_ENABLED = True
BUSINESS_APP_NOTIFICATION_WEBHOOKS = [
    'https://your-slack-webhook.com/hook'
]
BUSINESS_APP_REQUIRE_MINIMUM_SEVERITY = 'warning'
BUSINESS_APP_DEFAULT_INCIDENT_COMMANDER = 'NOC Team'

# Logging for incident automation
LOGGING = {
    # ... existing logging config ...
    'loggers': {
        'business_application.services.incident_service': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### 3. Run Database Migrations

If you've made any model changes:

```bash
python manage.py makemigrations business_application
python manage.py migrate
```

## How the System Works

### Automatic Processing (Real-time)

When a new `Event` is created or updated, Django signals automatically trigger incident processing:

```python
# This happens automatically when events are saved
event = Event.objects.create(
    message="Database connection failed",
    status=EventStatus.TRIGGERED,
    criticallity=EventCrit.CRITICAL,
    content_type=ContentType.objects.get_for_model(Device),
    object_id=device.id,
    # ... other fields
)
# System automatically processes this event for incident creation
```

### Correlation Algorithm

The system uses multiple factors to determine if events should be grouped:

1. **Direct Service Overlap** (80% weight) - Events affecting the same services
2. **Dependency Relationships** (60% weight) - Events in the same dependency chain  
3. **Infrastructure Overlap** (40% weight) - Events affecting related devices/VMs
4. **Time Decay** - Newer events more likely to correlate
5. **Severity Matching** - Similar severity events group better

### Example Scenarios

**Scenario 1: Database Outage**
```
Event 1: "DB-PROD-01 connection timeout" (affects DB service)
Event 2: "Web-APP-01 database errors" (affects Web service that depends on DB)
→ System creates 1 incident: "Service disruption affecting Database Service"
→ Both events grouped under this incident
```

**Scenario 2: Network Switch Failure** 
```
Event 1: "SWITCH-01 port down" (affects switch device)
Event 2: "WEB-01 unreachable" (affects web server connected to switch)  
Event 3: "APP-02 network timeout" (affects app server on same switch)
→ System creates 1 incident: "Infrastructure alert affecting SWITCH-01"
→ All events grouped as they share common network infrastructure
```

## API Usage

### Manual Event Processing

```bash
# Process a specific event
curl -X POST http://netbox/api/plugins/business-application/incident-automation/process-event/ \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{"event_id": 123}'
```

### Batch Processing

```bash
# Process all unprocessed events from last 24 hours
curl -X POST http://netbox/api/plugins/business-application/incident-automation/process-unprocessed/ \
  -H "Authorization: Token your-token" \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'
```

### System Status

```bash
# Get automation status and statistics
curl http://netbox/api/plugins/business-application/incident-automation/status/ \
  -H "Authorization: Token your-token"
```

## Management Commands

### Process Unprocessed Events

```bash
# Process events from last 24 hours
python manage.py process_incidents --mode=process --hours=24

# Process specific event
python manage.py process_incidents --event-id=123

# Dry run to see what would be processed
python manage.py process_incidents --mode=process --dry-run
```

### Force Re-correlation

```bash
# Re-correlate all events from last 24 hours
python manage.py process_incidents --mode=reprocess --hours=24 --force-correlate
```

### Cleanup Old Incidents

```bash
# Archive resolved incidents older than 7 days
python manage.py process_incidents --mode=cleanup --hours=168
```

## Integration with Monitoring Systems

### Webhook Integration

To integrate with external monitoring systems (Prometheus, Nagios, etc.), create events via API:

```python
import requests

def send_alert_to_netbox(alert_data):
    event_data = {
        "message": alert_data["summary"],
        "status": "triggered",
        "criticallity": "critical" if alert_data["severity"] == "critical" else "warning",
        "content_type": get_content_type_id("device"),  # or service, VM, etc.
        "object_id": get_object_id_from_alert(alert_data),
        "dedup_id": alert_data["fingerprint"],
        "event_source": get_or_create_event_source(alert_data["source"]),
        "raw": alert_data,
        "last_seen_at": alert_data["timestamp"]
    }
    
    response = requests.post(
        "http://netbox/api/plugins/business-application/events/",
        json=event_data,
        headers={"Authorization": "Token your-token"}
    )
    # Event will be automatically processed for incident creation
```

### Prometheus Alertmanager Integration

Example Alertmanager webhook config:

```yaml
# alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'netbox-webhook'

receivers:
- name: 'netbox-webhook'
  webhook_configs:
  - url: 'http://your-integration-service/alertmanager-to-netbox'
    send_resolved: true
```

## Monitoring and Troubleshooting

### Health Check

```bash
# Check system health
python manage.py shell -c "
from business_application.config import check_incident_automation_health
print(check_incident_automation_health())
"
```

### Common Issues

1. **Events not creating incidents**
   - Check if `BUSINESS_APP_AUTO_INCIDENTS_ENABLED = True`
   - Verify event status is `triggered`
   - Check minimum severity settings
   - Look at logs for errors

2. **Poor correlation quality**
   - Adjust `BUSINESS_APP_CORRELATION_THRESHOLD` (lower = more grouping)
   - Increase `BUSINESS_APP_CORRELATION_WINDOW_MINUTES`
   - Verify dependency relationships are properly configured

3. **Too many incidents created**
   - Increase correlation threshold
   - Check if dependency map is accurate
   - Review event sources for noise

### Logging

Monitor these log files:

```bash
# Check incident automation logs
tail -f /var/log/netbox/incident_automation.log

# Look for correlation patterns
grep "correlation_score" /var/log/netbox/incident_automation.log

# Check for errors
grep "ERROR" /var/log/netbox/incident_automation.log
```

## Testing the System

### 1. Create Test Events

```python
from business_application.models import Event, EventStatus, EventCrit
from dcim.models import Device
from django.contrib.contenttypes.models import ContentType

# Create test device
device = Device.objects.first()

# Create test event
event = Event.objects.create(
    message="Test database connection failed",
    status=EventStatus.TRIGGERED,
    criticallity=EventCrit.CRITICAL,
    content_type=ContentType.objects.get_for_model(Device),
    object_id=device.id,
    dedup_id="test-db-001",
    last_seen_at=timezone.now()
)

# Check if incident was created
incidents = event.incidents.all()
print(f"Event created {len(incidents)} incidents")
```

### 2. Test Correlation

```python
# Create related events that should correlate
related_device = get_related_device(device)  # Device in same service
event2 = Event.objects.create(
    message="Related service degraded",
    status=EventStatus.TRIGGERED,
    criticallity=EventCrit.WARNING,
    content_type=ContentType.objects.get_for_model(Device),
    object_id=related_device.id,
    dedup_id="test-web-001",
    last_seen_at=timezone.now()
)

# Check if events were correlated into same incident
common_incidents = set(event.incidents.all()) & set(event2.incidents.all())
print(f"Events share {len(common_incidents)} incidents")
```

## Performance Considerations

### Optimization Tips

1. **Index frequently queried fields**:
   ```sql
   CREATE INDEX idx_event_status_created ON business_application_event(status, created_at);
   CREATE INDEX idx_incident_status ON business_application_incident(status);
   ```

2. **Limit dependency traversal depth** (adjust `MAX_DEPENDENCY_DEPTH`)

3. **Use shorter correlation windows** for high-volume environments

4. **Archive old incidents** regularly using cleanup commands

5. **Monitor correlation analysis** to tune thresholds

### Scaling for High Volume

For environments with >1000 events/hour:

1. Use celery for async processing
2. Implement event batching  
3. Consider separate incident correlation service
4. Use database read replicas for correlation queries

## Webhook Notifications

Configure notifications to external systems:

```python
# Example Slack webhook payload
{
    "action": "created",
    "incident": {
        "id": 123,
        "title": "Service disruption affecting Database Service",
        "severity": "critical",
        "status": "new",
        "url": "http://netbox/plugins/business-application/incidents/123/"
    },
    "affected_services": [
        {"id": 1, "name": "Database Service", "service_type": "technical"}
    ],
    "event_count": 3
}
```

This completes the integration of automatic incident creation into your NetBox business application plugin. The system will now automatically group related alerts, reduce noise, and help you understand the blast radius of incidents through your dependency map.