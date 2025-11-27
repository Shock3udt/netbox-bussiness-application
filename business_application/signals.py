# business_application/signals.py
"""
Django signals for business_application plugin.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
import logging

from .models import Event, Incident, EventStatus

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Event)
def auto_create_incident_from_event(sender, instance, created, **kwargs):
    """
    Signal to automatically process events for incident creation when they are created or updated.
    Also sends events to PagerDuty if configured.
    """
    from .utils.correlation import AlertCorrelationEngine
    from .utils.pagerduty import send_event_to_pagerduty, pagerduty_config

    if pagerduty_config.enabled and pagerduty_config.send_on_event_create:
        try:
            result = send_event_to_pagerduty(instance)
            if result:
                logger.info(f"Event {instance.id} sent to PagerDuty: {result.get('status', 'unknown')}")
        except Exception as e:
            logger.error(f"Error sending event {instance.id} to PagerDuty: {e}")

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
    Track when events change status to potentially resolve incidents
    and update PagerDuty.
    """
    from .utils.pagerduty import send_event_to_pagerduty, pagerduty_config

    if instance.pk:
        try:
            old_instance = Event.objects.get(pk=instance.pk)

            if old_instance.status != instance.status:
                if pagerduty_config.enabled:
                    try:
                        logger.debug(
                            f"Event {instance.id} status changing from "
                            f"{old_instance.status} to {instance.status}"
                        )
                    except Exception as e:
                        logger.error(f"Error handling event status change: {e}")

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
def handle_incident_save(sender, instance, created, **kwargs):
    """
    Handle incident creation and updates.
    Sends incidents to PagerDuty if configured.
    """
    from .utils.pagerduty import (
        send_incident_to_pagerduty,
        pagerduty_config,
        PagerDutyEventAction
    )

    if created:
        logger.info(f"New incident created: {instance.id} - {instance.title}")

    if not pagerduty_config.enabled:
        return

    try:
        if created and pagerduty_config.send_on_incident_create:
            result = send_incident_to_pagerduty(instance, action=PagerDutyEventAction.TRIGGER)
            if result:
                logger.info(
                    f"Incident {instance.id} sent to PagerDuty: {result.get('status', 'unknown')}"
                )
        elif not created and pagerduty_config.send_on_incident_update:
            pass

    except Exception as e:
        logger.error(f"Error sending incident {instance.id} to PagerDuty: {e}")


@receiver(pre_save, sender=Incident)
def track_incident_status_changes(sender, instance, **kwargs):
    """
    Track incident status changes for PagerDuty updates.
    """
    from .utils.pagerduty import (
        update_incident_pagerduty_status,
        pagerduty_config
    )

    if not instance.pk:
        return

    if not pagerduty_config.enabled or not pagerduty_config.send_on_incident_update:
        return

    try:
        old_instance = Incident.objects.get(pk=instance.pk)

        if old_instance.status != instance.status:
            logger.debug(
                f"Incident {instance.id} status changing from "
                f"{old_instance.status} to {instance.status}"
            )

            instance._old_status = old_instance.status

    except Incident.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error tracking incident status change: {e}")


@receiver(post_save, sender=Incident)
def handle_incident_status_update(sender, instance, created, **kwargs):
    """
    Send PagerDuty update after incident status change is saved.
    """
    from .utils.pagerduty import (
        update_incident_pagerduty_status,
        pagerduty_config
    )

    if created:
        return

    if not pagerduty_config.enabled or not pagerduty_config.send_on_incident_update:
        return

    old_status = getattr(instance, '_old_status', None)
    if old_status and old_status != instance.status:
        try:
            result = update_incident_pagerduty_status(instance, old_status, instance.status)
            if result:
                logger.info(
                    f"Incident {instance.id} PagerDuty status updated: "
                    f"{old_status} -> {instance.status}"
                )
        except Exception as e:
            logger.error(f"Error updating incident {instance.id} PagerDuty status: {e}")
        finally:
            if hasattr(instance, '_old_status'):
                del instance._old_status