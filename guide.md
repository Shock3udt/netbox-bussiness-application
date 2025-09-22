# NetBox Business Application Plugin - Incident Automation Deployment Guide

This guide provides step-by-step instructions for deploying the automatic incident creation system in your NetBox Business Application plugin.

## Overview

The incident automation system automatically groups related alerts into incidents by analyzing NetBox dependency relationships. Key features include:

- **Automatic Event Correlation** - Groups related events based on service dependencies
- **Blast Radius Identification** - Determines impact scope through dependency analysis
- **Noise Reduction** - Reduces alert fatigue by intelligent grouping
- **Real-time Processing** - Processes events automatically via Django signals
- **Manual Control** - API endpoints for manual processing and analysis

## Prerequisites

- NetBox instance (version 3.0+)
- Business Application plugin already installed and functional
- Python 3.8+ with Django 4.0+
- Proper permissions for plugin modifications

## Deployment Steps

### Step 1: Create Directory Structure

Create the required directory structure in your plugin:

```bash
cd /path/to/business_application/

# Create services directory
mkdir -p services
mkdir -p management/commands

# Create __init__.py files
touch services/__init__.py
touch management/__init__.py  
touch management/commands/__init__.py
```

Verify the structure:
```
business_application/
├── services/
│   └── __init__.py
├── management/
│   ├── __init__.py
│   └── commands/
│       └── __init__.py
├── models.py
├── apps.py
└── signals.py
```

### Step 2: Create Core Service File

Create `services/incident_service.py`:

```python
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from typing import Set, List, Optional, Any
import logging

from ..models import (
    Incident, Event, TechnicalService, ServiceDependency, IncidentStatus, IncidentSeverity,
    EventStatus, EventCrit
)
from dcim.models import Device
from virtualization.models import VirtualMachine, Cluster

logger = logging.getLogger(__name__)

class IncidentAutoCreationService:
    """
    Service for automatically creating and managing incidents from incoming alerts.
    Groups related alerts by identifying common parent services in the dependency map.
    """
    
    def __init__(self):
        self.correlation_window_minutes = 15
        self.max_dependency_depth = 5
        
    def process_incoming_event(self, event: Event) -> Optional[Incident]:
        """Main entry point for processing incoming alerts/events."""
        logger.info(f"Processing incoming event: {event.id} - {event.message}")
        
        if event.status not in [EventStatus.TRIGGERED]:
            logger.debug(f"Skipping event {event.id} - status is {event.status}")
            return None
            
        affected_components = self._get_affected_components_from_event(event)
        if not affected_components:
            logger.warning(f"No affected components found for event {event.id}")
            return None
            
        existing_incident = self._find_correlating_incident(event, affected_components)
        
        if existing_incident:
            logger.info(f"Correlating event {event.id} with existing incident {existing_incident.id}")
            self._add_event_to_incident(event, existing_incident)
            return existing_incident
        else:
            logger.info(f"Creating new incident for event {event.id}")
            return self._create_new_incident(event, affected_components)
    
    # Add remaining methods from the incident_service.py file...
    # [Include all the methods from the incident service implementation]

def process_event_for_incident(event_id: int) -> Optional[Incident]:
    """Utility function to manually process a specific event."""
    try:
        event = Event.objects.get(id=event_id)
        service = IncidentAutoCreationService()
        return service.process_incoming_event(event)
    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
        return None

def process_unprocessed_events():
    """Process all unprocessed events that haven't been assigned to incidents."""
    unprocessed_events = Event.objects.filter(
        incidents__isnull=True,
        status=EventStatus.TRIGGERED,
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).order_by('created_at')

    service = IncidentAutoCreationService()
    processed_count = 0

    for event in unprocessed_events:
        try:
            incident = service.process_incoming_event(event)
            if incident:
                processed_count += 1
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}")

    logger.info(f"Processed {processed_count} unprocessed events")
    return processed_count
```

### Step 3: Create Django Signals

Create or update `signals.py` in your plugin root:

```python
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
import logging

from .models import Event, Incident, EventStatus

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Event)
def auto_create_incident_from_event(sender, instance, created, **kwargs):
    """Signal to automatically process events for incident creation."""
    if not getattr(settings, 'BUSINESS_APP_AUTO_INCIDENTS_ENABLED', True):
        return
        
    if instance.status != EventStatus.TRIGGERED:
        return
        
    if instance.incidents.exists():
        return
        
    try:
        from .services.incident_service import IncidentAutoCreationService
        logger.info(f"Auto-processing event {instance.id} for incident creation")
        service = IncidentAutoCreationService()
        incident = service.process_incoming_event(instance)
        
        if incident:
            logger.info(f"Created/updated incident {incident.id} from event {instance.id}")
            
    except Exception as e:
        logger.error(f"Error in auto-incident creation for event {instance.id}: {e}", exc_info=True)

@receiver(pre_save, sender=Event)
def track_event_status_changes(sender, instance, **kwargs):
    """Track when events change status to potentially resolve incidents."""
    if instance.pk:
        try:
            old_instance = Event.objects.get(pk=instance.pk)
            
            if (old_instance.status == EventStatus.TRIGGERED and 
                instance.status == EventStatus.OK):
                
                for incident in instance.incidents.filter(
                    status__in=['new', 'investigating', 'identified']
                ):
                    check_incident_auto_resolution(incident)
                    
        except Event.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error tracking event status change for {instance.id}: {e}")

def check_incident_auto_resolution(incident):
    """Check if an incident should be automatically resolved."""
    if not getattr(settings, 'BUSINESS_APP_AUTO_RESOLVE_INCIDENTS', False):
        return
        
    active_events = incident.events.filter(status=EventStatus.TRIGGERED)
    
    if not active_events.exists():
        incident.status = 'monitoring'
        incident.resolved_at = timezone.now()
        incident.save(update_fields=['status', 'resolved_at'])
        logger.info(f"Auto-resolved incident {incident.id} - all related events are OK")

@receiver(post_save, sender=Incident)
def log_incident_creation(sender, instance, created, **kwargs):
    """Log incident creation for auditing."""
    if created:
        logger.info(f"New incident created: {instance.id} - {instance.title}")
```

### Step 4: Update App Configuration

Update your `apps.py`:

```python
from django.apps import AppConfig

class BusinessApplicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'business_application'
    verbose_name = 'Business Application'

    def ready(self):
        """Import signals when the app is ready."""
        import business_application.signals
```

### Step 5: Create Configuration File

Create `config.py` in your plugin root:

```python
from django.conf import settings

class IncidentAutomationConfig:
    """Configuration settings for incident automation features."""
    
    @property
    def ENABLED(self):
        return getattr(settings, 'BUSINESS_APP_AUTO_INCIDENTS_ENABLED', True)
    
    @property
    def AUTO_RESOLVE_ENABLED(self):
        return getattr(settings, 'BUSINESS_APP_AUTO_RESOLVE_INCIDENTS', False)
    
    @property
    def CORRELATION_WINDOW_MINUTES(self):
        return getattr(settings, 'BUSINESS_APP_CORRELATION_WINDOW_MINUTES', 15)
    
    @property
    def MAX_DEPENDENCY_DEPTH(self):
        return getattr(settings, 'BUSINESS_APP_MAX_DEPENDENCY_DEPTH', 5)
    
    @property
    def CORRELATION_THRESHOLD(self):
        return getattr(settings, 'BUSINESS_APP_CORRELATION_THRESHOLD', 0.3)
    
    @property
    def NOTIFICATIONS_ENABLED(self):
        return getattr(settings, 'BUSINESS_APP_INCIDENT_NOTIFICATIONS_ENABLED', False)
    
    @property
    def NOTIFICATION_WEBHOOKS(self):
        return getattr(settings, 'BUSINESS_APP_NOTIFICATION_WEBHOOKS', [])
```

### Step 6: Create Management Commands

Create `management/commands/process_incidents.py`:

```python
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import logging

from business_application.models import Event, Incident, EventStatus
from business_application.services.incident_service import (
    IncidentAutoCreationService, process_unprocessed_events
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process events for automatic incident creation and management'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['process', 'reprocess', 'cleanup'],
            default='process',
            help='Processing mode'
        )
        parser.add_argument('--hours', type=int, default=24, help='Hours to look back')
        parser.add_argument('--event-id', type=int, help='Process specific event by ID')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be processed')

    def handle(self, *args, **options):
        mode = options['mode']
        hours = options['hours']
        event_id = options['event_id']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        try:
            if event_id:
                self._process_specific_event(event_id, dry_run)
            elif mode == 'process':
                self._process_unprocessed_events(hours, dry_run)
            # Add other modes...
        except Exception as e:
            raise CommandError(f'Error during processing: {e}')
    
    def _process_specific_event(self, event_id, dry_run):
        """Process a specific event for incident creation."""
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            raise CommandError(f'Event {event_id} not found')

        self.stdout.write(f'Processing event {event_id}: {event.message}')
        
        if dry_run:
            self.stdout.write('Would process this event for incident creation')
            return

        from business_application.services.incident_service import IncidentAutoCreationService
        service = IncidentAutoCreationService()
        incident = service.process_incoming_event(event)
        
        if incident:
            self.stdout.write(
                self.style.SUCCESS(f'Event {event_id} processed - Incident {incident.id}: {incident.title}')
            )
        else:
            self.stdout.write(self.style.WARNING(f'No incident action taken for event {event_id}'))
    
    def _process_unprocessed_events(self, hours, dry_run):
        """Process events that haven't been assigned to incidents."""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        unprocessed_events = Event.objects.filter(
            incidents__isnull=True,
            status=EventStatus.TRIGGERED,
            created_at__gte=cutoff_time
        ).order_by('created_at')

        total_events = unprocessed_events.count()
        self.stdout.write(f'Found {total_events} unprocessed events in the last {hours} hours')

        if dry_run:
            for event in unprocessed_events[:10]:
                self.stdout.write(f'Would process: {event.id} - {event.message[:50]}...')
            if total_events > 10:
                self.stdout.write(f'... and {total_events - 10} more events')
            return

        processed_count = process_unprocessed_events()
        self.stdout.write(self.style.SUCCESS(f'Successfully processed {processed_count} events'))
```

### Step 7: Update API URLs

Ensure your `api/urls.py` includes the incident automation endpoints:

```python
from business_application.api.incident_automation_views import IncidentAutomationViewSet

router.register(r'incident-automation', IncidentAutomationViewSet, basename='incident-automation')
```

### Step 8: Configure NetBox Settings

Add these settings to your NetBox `configuration.py`:

```python
# Business Application Plugin - Incident Automation Settings
BUSINESS_APP_AUTO_INCIDENTS_ENABLED = True
BUSINESS_APP_AUTO_RESOLVE_INCIDENTS = True
BUSINESS_APP_CORRELATION_WINDOW_MINUTES = 15
BUSINESS_APP_MAX_DEPENDENCY_DEPTH = 5
BUSINESS_APP_CORRELATION_THRESHOLD = 0.3
```

### Step 9: Restart NetBox

Restart your NetBox services to load the new configuration:

```bash
sudo systemctl restart netbox
sudo systemctl restart netbox-rq  # If using RQ for background jobs
```

## Verification and Testing

### Test 1: Verify Imports

```bash
python manage.py shell
```

```python
# Test service import
from business_application.services.incident_service import IncidentAutoCreationService
print("Service import successful")

# Test signal import
from business_application import signals
print("Signals import successful")
```

### Test 2: Test Automatic Incident Creation

```python
from business_application.models import Event, EventSource, EventStatus, EventCrit
from django.utils import timezone

# Create a test event
event = Event.objects.create(
    message="Test database connection failed",
    status=EventStatus.TRIGGERED,
    criticallity=EventCrit.CRITICAL,
    dedup_id="test-automation-001",
    last_seen_at=timezone.now(),
    raw={"test": True}
)

# Check if incident was auto-created
print(f"Event {event.id} has {event.incidents.count()} incidents")
if event.incidents.exists():
    incident = event.incidents.first()
    print(f"Created incident: {incident.id} - {incident.title}")
```

### Test 3: Test API Endpoints

```bash
# Test automation status
curl -H "Authorization: Token your-netbox-token" \
     http://your-netbox-url/api/plugins/business-application/incident-automation/status/

# Test manual event processing
curl -X POST \
     -H "Authorization: Token your-netbox-token" \
     -H "Content-Type: application/json" \
     -d '{"event_id": 1}' \
     http://your-netbox-url/api/plugins/business-application/incident-automation/process-event/
```

### Test 4: Test Management Commands

```bash
# Test dry run
python manage.py process_incidents --dry-run

# Process unprocessed events
python manage.py process_incidents --mode=process --hours=24

# Process specific event
python manage.py process_incidents --event-id=123
```

## API Endpoints

The system provides these API endpoints for automation control:

- `GET /api/plugins/business-application/incident-automation/status/` - System status
- `POST /api/plugins/business-application/incident-automation/process-event/` - Process specific event
- `POST /api/plugins/business-application/incident-automation/process-unprocessed/` - Batch processing
- `POST /api/plugins/business-application/incident-automation/force-correlate/` - Re-correlation
- `GET /api/plugins/business-application/incident-automation/correlation-analysis/` - Analysis

## Configuration Options

### Correlation Settings

- `BUSINESS_APP_CORRELATION_WINDOW_MINUTES` (default: 15) - Time window for event correlation
- `BUSINESS_APP_CORRELATION_THRESHOLD` (default: 0.3) - Minimum correlation score (0-1)
- `BUSINESS_APP_MAX_DEPENDENCY_DEPTH` (default: 5) - Maximum dependency traversal depth

### Automation Behavior

- `BUSINESS_APP_AUTO_INCIDENTS_ENABLED` (default: True) - Enable/disable automation
- `BUSINESS_APP_AUTO_RESOLVE_INCIDENTS` (default: False) - Auto-resolve when all events clear

### Notifications

- `BUSINESS_APP_INCIDENT_NOTIFICATIONS_ENABLED` (default: False) - Enable notifications
- `BUSINESS_APP_NOTIFICATION_WEBHOOKS` (default: []) - Webhook URLs for notifications

## Monitoring and Maintenance

### Log Monitoring

Monitor these log locations:
- `/var/log/netbox/incident_automation.log` - Automation activity
- `/var/log/netbox/netbox.log` - General NetBox logs

Key log patterns to watch:
```bash
# Successful incident creation
grep "Created new incident" /var/log/netbox/incident_automation.log

# Correlation activity  
grep "correlation_score" /var/log/netbox/incident_automation.log

# Errors
grep "ERROR" /var/log/netbox/incident_automation.log
```

### Performance Monitoring

Monitor these metrics:
- Event processing time
- Incident creation rate
- Correlation accuracy
- System resource usage during processing

### Regular Maintenance

Run these commands periodically:

```bash
# Weekly: Process any missed events
python manage.py process_incidents --mode=process --hours=168

# Monthly: Clean up old resolved incidents  
python manage.py process_incidents --mode=cleanup --hours=720

# As needed: Re-correlate recent events for better grouping
python manage.py process_incidents --mode=reprocess --hours=24 --force-correlate
```

## Troubleshooting

### Common Issues

**1. Events not creating incidents**
- Check `BUSINESS_APP_AUTO_INCIDENTS_ENABLED = True`
- Verify event status is `triggered`
- Check logs for signal processing errors
- Ensure services directory has `__init__.py`

**2. Import errors**
```bash
ModuleNotFoundError: No module named 'business_application.services'
```
Solution: Create `services/__init__.py` file

**3. Poor correlation quality**
- Adjust `BUSINESS_APP_CORRELATION_THRESHOLD` (lower = more grouping)
- Increase `BUSINESS_APP_CORRELATION_WINDOW_MINUTES`
- Verify service dependency relationships are configured

**4. High resource usage**
- Reduce `BUSINESS_APP_MAX_DEPENDENCY_DEPTH`
- Add database indexes on frequently queried fields
- Consider processing events in smaller batches

### Debug Commands

```bash
# Check system health
python manage.py shell -c "
from business_application.config import check_incident_automation_health
print(check_incident_automation_health())
"

# Analyze correlation patterns
curl -H "Authorization: Token your-token" \
     "http://your-netbox/api/plugins/business-application/incident-automation/correlation-analysis/?hours=24"

# Manual event processing with detailed logging
python manage.py process_incidents --event-id=123 --verbosity=2
```

## Support

For issues and support:
1. Check NetBox logs for error details
2. Verify all configuration settings
3. Test with simple events first
4. Use dry-run mode for testing changes
5. Monitor correlation analysis for tuning insights

The incident automation system provides powerful alert correlation capabilities while maintaining flexibility for customization based on your specific infrastructure and operational needs.