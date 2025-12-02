from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
import logging

from .models import Event, Incident, EventStatus

logger = logging.getLogger(__name__)

def get_pagerduty_manager():
    """Lazy import to avoid circular imports."""
    try:
        from .utils.pagerduty_integration import PagerDutyIncidentManager
        return PagerDutyIncidentManager()
    except ImportError:
        logger.warning("PagerDuty integration module not found")
        return None

_incident_status_cache = {}


@receiver(pre_save, sender=Incident)
def cache_incident_old_status(sender, instance, **kwargs):
    """Cache old incident status to detect changes."""
    if instance.pk:
        try:
            old_instance = Incident.objects.get(pk=instance.pk)
            _incident_status_cache[instance.pk] = old_instance.status
        except Incident.DoesNotExist:
            _incident_status_cache[instance.pk] = None
    else:
        _incident_status_cache[instance.pk] = None

@receiver(post_save, sender=Event)
def auto_create_incident_from_event(sender, instance, created, **kwargs):
    """
    Signal to automatically process events for incident creation when they are created or updated.
    """
    if not getattr(settings, 'BUSINESS_APP_AUTO_INCIDENTS_ENABLED', True):
        return

    if instance.status != EventStatus.TRIGGERED:
        if instance.status == EventStatus.OK:
            # Check if all events for any related incident are resolved,
            # if so, set the incident status to "monitoring"
            for incident in instance.incidents.all():
                all_ok = not incident.events.exclude(status=EventStatus.OK).exists()
                if all_ok and incident.status != 'monitoring':
                    incident.status = 'monitoring'
                    incident.save(update_fields=['status'])
            return
        return

    if instance.incidents.exists():
        return

    try:
        from .utils.correlation import AlertCorrelationEngine

        logger.info(f"Auto-processing event {instance.id} for incident creation")
        correlation_engine = AlertCorrelationEngine()
        incident = correlation_engine.correlate_alert(instance)

        if incident:
            logger.info(f"Successfully created/updated incident {incident.id} from event {instance.id}")
        else:
            logger.debug(f"No incident action taken for event {instance.id}")

    except Exception as e:
        logger.error(f"Error in auto-incident creation for event {instance.id}: {e}", exc_info=True)


@receiver(pre_save, sender=Event)
def track_event_status_changes(sender, instance, **kwargs):
    """
    Track when events change status to potentially resolve incidents.
    """
    if instance.pk:
        try:
            old_instance = Event.objects.get(pk=instance.pk)

            if (old_instance.status == EventStatus.TRIGGERED and
                    instance.status == EventStatus.OK):

                logger.info(f"Event {instance.id} changed from TRIGGERED to OK")

                for incident in instance.incidents.filter(
                        status__in=['new', 'investigating', 'identified', 'monitoring']
                ):
                    check_incident_auto_resolution(incident)

        except Event.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error tracking event status change for {instance.id}: {e}")

@receiver(post_save, sender=Incident)
def handle_incident_post_save(sender, instance, created, **kwargs):
    """
    Handle incident creation and status changes.
    - Log creation
    - Sync status changes to PagerDuty
    """
    # Log creation
    if created:
        logger.info(f"New incident created: {instance.id} - {instance.title}")

        if getattr(settings, 'BUSINESS_APP_INCIDENT_NOTIFICATIONS_ENABLED', False):
            pass

    sync_incident_status_to_pagerduty(sender, instance, created)


def sync_incident_status_to_pagerduty(sender, instance, created):
    """
    Synchronize incident status changes to PagerDuty.

    - When incident is resolved/closed -> resolve PagerDuty incident
    - When incident is investigating -> acknowledge PagerDuty incident
    """
    try:
        old_status = _incident_status_cache.get(instance.pk)
        new_status = instance.status

        if instance.pk in _incident_status_cache:
            del _incident_status_cache[instance.pk]

        if old_status == new_status and not created:
            return

        if not instance.pagerduty_dedup_key:
            logger.debug(f"Incident {instance.id} has no PagerDuty dedup key, skipping sync")
            return

        manager = get_pagerduty_manager()
        if not manager:
            return

        resolved_statuses = ['resolved', 'closed']

        if new_status in resolved_statuses and old_status not in resolved_statuses:
            logger.info(
                f"Incident {instance.id} status changed from '{old_status}' to '{new_status}', "
                f"resolving PagerDuty incident"
            )

            result = manager.resolve_pagerduty_incident(instance)

            if result:
                logger.info(f"Successfully resolved PagerDuty incident for NetBox incident {instance.id}")
            else:
                logger.warning(f"Failed to resolve PagerDuty incident for NetBox incident {instance.id}")

        elif new_status == 'investigating' and old_status in ['new', None]:
            logger.info(f"Incident {instance.id} is being investigated, sending acknowledgment to PagerDuty")

            result = manager.acknowledge_pagerduty_incident(instance)

            if result:
                logger.info(f"Successfully acknowledged PagerDuty incident for NetBox incident {instance.id}")

    except Exception as e:
        logger.exception(f"Error syncing incident {instance.id} to PagerDuty: {str(e)}")

def check_incident_auto_resolution(incident):
    """
    Check if an incident should be automatically resolved when all related events are OK.

    When all events are OK:
    1. Change incident status to 'resolved' (or 'monitoring' based on config)
    2. This triggers sync_incident_status_to_pagerduty which resolves PagerDuty incident
    """
    if not getattr(settings, 'BUSINESS_APP_AUTO_RESOLVE_INCIDENTS', True):
        logger.debug(f"Auto-resolve disabled, skipping check for incident {incident.id}")
        return False

    try:
        active_events = incident.events.filter(status=EventStatus.TRIGGERED)
        total_events = incident.events.count()
        ok_events = incident.events.filter(status=EventStatus.OK).count()

        logger.debug(
            f"Incident {incident.id}: {active_events.count()} triggered, "
            f"{ok_events} ok, {total_events} total"
        )

        if not active_events.exists() and ok_events > 0:
            logger.info(
                f"All events for incident {incident.id} are OK, auto-resolving incident"
            )

            incident.status = 'resolved'
            incident.resolved_at = timezone.now()
            incident.save(update_fields=['status', 'resolved_at', 'updated_at'])

            logger.info(f"Auto-resolved incident {incident.id} - all related events are OK")
            return True

        return False

    except Exception as e:
        logger.error(f"Error in check_incident_auto_resolution for incident {incident.id}: {e}")
        return False

def manually_resolve_incident_with_pagerduty(incident_id):
    """
    Utility function to manually resolve an incident and sync to PagerDuty.

    Args:
        incident_id: The ID of the incident to resolve

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        incident = Incident.objects.get(pk=incident_id)

        if incident.status in ['resolved', 'closed']:
            logger.info(f"Incident {incident_id} is already resolved/closed")
            return True

        incident.status = 'resolved'
        incident.resolved_at = timezone.now()
        incident.save()

        return True

    except Incident.DoesNotExist:
        logger.error(f"Incident {incident_id} not found")
        return False
    except Exception as e:
        logger.exception(f"Error manually resolving incident {incident_id}: {str(e)}")
        return False


def bulk_resolve_events_and_check_incidents(event_ids):
    """
    Utility function to bulk resolve events and check if related incidents
    should be auto-resolved.

    Args:
        event_ids: List of event IDs to mark as 'ok'

    Returns:
        dict: Results with resolved events and incidents
    """
    try:
        results = {
            'events_resolved': 0,
            'incidents_resolved': [],
            'errors': []
        }

        events = Event.objects.filter(id__in=event_ids)
        related_incidents = set()

        for event in events:
            for incident in event.incidents.filter(
                    status__in=['new', 'investigating', 'identified', 'monitoring']
            ):
                related_incidents.add(incident.id)

        updated = events.update(status=EventStatus.OK, last_seen_at=timezone.now())
        results['events_resolved'] = updated

        logger.info(f"Bulk resolved {updated} events to OK status")

        for incident_id in related_incidents:
            try:
                incident = Incident.objects.get(pk=incident_id)
                if check_incident_auto_resolution(incident):
                    results['incidents_resolved'].append(incident_id)
            except Exception as e:
                results['errors'].append(f"Incident {incident_id}: {str(e)}")

        return results

    except Exception as e:
        logger.exception(f"Error in bulk_resolve_events_and_check_incidents: {str(e)}")
        return {'events_resolved': 0, 'incidents_resolved': [], 'errors': [str(e)]}