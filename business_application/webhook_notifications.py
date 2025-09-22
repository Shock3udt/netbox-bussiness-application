import requests
import logging
from django.conf import settings
from typing import List, Dict, Any

from .config import IncidentAutomationConfig

logger = logging.getLogger(__name__)
config = IncidentAutomationConfig()


class IncidentNotificationService:
    """
    Service for sending incident notifications to external systems.
    """

    def __init__(self):
        self.webhooks = config.NOTIFICATION_WEBHOOKS
        self.enabled = config.NOTIFICATIONS_ENABLED

    def send_incident_created_notification(self, incident):
        """Send notification when a new incident is created."""
        if not self.enabled or not self.webhooks:
            return

        payload = self._build_incident_payload(incident, 'created')
        self._send_to_webhooks(payload)

    def send_incident_updated_notification(self, incident):
        """Send notification when an incident is updated."""
        if not self.enabled or not self.webhooks:
            return

        payload = self._build_incident_payload(incident, 'updated')
        self._send_to_webhooks(payload)

    def send_incident_resolved_notification(self, incident):
        """Send notification when an incident is resolved."""
        if not self.enabled or not self.webhooks:
            return

        payload = self._build_incident_payload(incident, 'resolved')
        self._send_to_webhooks(payload)

    def _build_incident_payload(self, incident, action: str) -> Dict[str, Any]:
        """Build the notification payload for an incident."""
        payload = {
            'action': action,
            'incident': {
                'id': incident.id,
                'title': incident.title,
                'description': incident.description,
                'status': incident.status,
                'severity': incident.severity,
                'created_at': incident.created_at.isoformat(),
                'detected_at': incident.detected_at.isoformat() if incident.detected_at else None,
                'resolved_at': incident.resolved_at.isoformat() if incident.resolved_at else None,
                'commander': incident.commander,
                'reporter': incident.reporter,
                'url': f"{settings.BASE_URL}{incident.get_absolute_url()}" if hasattr(settings, 'BASE_URL') else None
            },
            'affected_services': [
                {
                    'id': service.id,
                    'name': service.name,
                    'service_type': service.service_type
                }
                for service in incident.affected_services.all()
            ],
            'event_count': incident.events.count(),
            'responder_count': incident.responders.count()
        }

        return payload

    def _send_to_webhooks(self, payload: Dict[str, Any]):
        """Send payload to all configured webhooks."""
        for webhook_url in self.webhooks:
            try:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                logger.info(f"Successfully sent notification to {webhook_url}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to send notification to {webhook_url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending notification to {webhook_url}: {e}")

def get_incident_automation_config():
    """Get the incident automation configuration instance."""
    return IncidentAutomationConfig()

def check_incident_automation_health():
    """
    Check the health of the incident automation system.
    Returns a dict with status information.
    """
    config = get_incident_automation_config()

    health_status = {
        'enabled': config.ENABLED,
        'auto_resolve_enabled': config.AUTO_RESOLVE_ENABLED,
        'notifications_enabled': config.NOTIFICATIONS_ENABLED,
        'webhook_count': len(config.NOTIFICATION_WEBHOOKS),
        'correlation_window_minutes': config.CORRELATION_WINDOW_MINUTES,
        'correlation_threshold': config.CORRELATION_THRESHOLD,
        'configuration_valid': True,
        'issues': []
    }

    if config.CORRELATION_THRESHOLD < 0 or config.CORRELATION_THRESHOLD > 1:
        health_status['configuration_valid'] = False
        health_status['issues'].append('CORRELATION_THRESHOLD must be between 0 and 1')

    if config.CORRELATION_WINDOW_MINUTES < 1:
        health_status['configuration_valid'] = False
        health_status['issues'].append('CORRELATION_WINDOW_MINUTES must be at least 1')

    if config.MAX_DEPENDENCY_DEPTH < 1:
        health_status['configuration_valid'] = False
        health_status['issues'].append('MAX_DEPENDENCY_DEPTH must be at least 1')

    return health_status