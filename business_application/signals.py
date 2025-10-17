from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
import logging

from .models import Event, Incident, EventStatus
from .utils.correlation import AlertCorrelationEngine

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Event)
def auto_create_incident_from_event(sender, instance, created, **kwargs):
    """
    Signal to automatically process events for incident creation when they are created or updated.
    """
    if not getattr(settings, 'BUSINESS_APP_AUTO_INCIDENTS_ENABLED', True):
        return

    if instance.status != EventStatus.TRIGGERED:
        return

    if instance.incidents.exists():
        return

    try:
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

                for incident in instance.incidents.filter(
                        status__in=['new', 'investigating', 'identified']
                ):
                    check_incident_auto_resolution(incident)

        except Event.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Error tracking event status change for {instance.id}: {e}")


def check_incident_auto_resolution(incident):
    """
    Check if an incident should be automatically resolved when all related events are OK.
    """
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
    """
    Log incident creation for auditing purposes.
    """
    if created:
        logger.info(f"New incident created: {instance.id} - {instance.title}")

        if getattr(settings, 'BUSINESS_APP_INCIDENT_NOTIFICATIONS_ENABLED', False):
            pass