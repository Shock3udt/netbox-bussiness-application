from datetime import timezone

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