# business_application/signals.py
"""
Django signals for business_application plugin.

Handles automatic incident creation from events and PagerDuty notifications.
"""

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
    Also sends events to PagerDuty if configured.
    """
    # Send to PagerDuty if enabled
    try:
        from .utils.pagerduty import send_event_to_pagerduty, pagerduty_config

        if pagerduty_config.enabled and pagerduty_config.send_on_event_create:
            result = send_event_to_pagerduty(instance)
            if result:
                logger.info(f"Event {instance.id} sent to PagerDuty: {result.get('status', 'unknown')}")
    except Exception as e:
        logger.error(f"Error sending event {instance.id} to PagerDuty: {e}")

    # Auto incident creation
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
    Also sends resolve to PagerDuty if configured.
    """
    if not getattr(settings, 'BUSINESS_APP_AUTO_RESOLVE_INCIDENTS', False):
        return

    active_events = incident.events.filter(status=EventStatus.TRIGGERED)

    if not active_events.exists():
        incident.status = 'resolved'
        incident.resolved_at = timezone.now()
        incident.save(update_fields=['status', 'resolved_at'])

        logger.info(f"Auto-resolved incident {incident.id} - all related events are OK")

        # Send resolve to PagerDuty
        try:
            from .utils.pagerduty import send_incident_to_pagerduty, pagerduty_config, PagerDutyEventAction

            if pagerduty_config.enabled and pagerduty_config.auto_resolve:
                result = send_incident_to_pagerduty(incident, action=PagerDutyEventAction.RESOLVE)
                if result:
                    logger.info(f"Auto-resolved PagerDuty incident for NetBox incident {incident.id}")
        except Exception as e:
            logger.error(f"Failed to auto-resolve PagerDuty incident for {incident.id}: {e}")


@receiver(post_save, sender=Incident)
def handle_incident_creation(sender, instance, created, **kwargs):
    """
    Handle incident creation - log and send to PagerDuty if configured.
    """
    if created:
        logger.info(f"New incident created: {instance.id} - {instance.title}")

        # Send to PagerDuty
        try:
            from .utils.pagerduty import send_incident_to_pagerduty, pagerduty_config, PagerDutyEventAction

            if pagerduty_config.enabled and pagerduty_config.send_on_incident_create:
                result = send_incident_to_pagerduty(instance, action=PagerDutyEventAction.TRIGGER)
                if result:
                    logger.info(f"Incident {instance.id} sent to PagerDuty: {result.get('status', 'unknown')}")
        except Exception as e:
            logger.error(f"Error sending incident {instance.id} to PagerDuty: {e}")

        # Notification webhook (placeholder for future implementation)
        if getattr(settings, 'BUSINESS_APP_INCIDENT_NOTIFICATIONS_ENABLED', False):
            pass