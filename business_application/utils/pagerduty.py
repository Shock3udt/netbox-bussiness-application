# business_application/utils/pagerduty.py
"""
PagerDuty Events API v2 Client

This module provides integration with PagerDuty for sending events
(trigger, acknowledge, resolve) from NetBox incidents and events.
"""

import json
import logging
from typing import Optional, Dict, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('business_application.pagerduty')


class PagerDutyConfig:
    """
    Configuration for PagerDuty integration.
    All settings are read from Django settings with sensible defaults.
    """

    @property
    def enabled(self) -> bool:
        """Whether PagerDuty integration is enabled."""
        return getattr(settings, 'PAGERDUTY_ENABLED', False)

    @property
    def events_api_url(self) -> str:
        """PagerDuty Events API v2 endpoint."""
        return getattr(
            settings,
            'PAGERDUTY_EVENTS_API_URL',
            'https://events.pagerduty.com/v2/enqueue'
        )

    @property
    def routing_key(self) -> Optional[str]:
        """
        Global routing key (integration key) for PagerDuty.
        This is the 32-character integration key from PagerDuty service.
        """
        return getattr(settings, 'PAGERDUTY_ROUTING_KEY', None)

    @property
    def source(self) -> str:
        """Source identifier for events (typically hostname or service name)."""
        return getattr(settings, 'PAGERDUTY_SOURCE', 'netbox')

    @property
    def send_on_event_create(self) -> bool:
        """Whether to send PagerDuty events when NetBox Events are created."""
        return getattr(settings, 'PAGERDUTY_SEND_ON_EVENT_CREATE', True)

    @property
    def send_on_incident_create(self) -> bool:
        """Whether to send PagerDuty events when NetBox Incidents are created."""
        return getattr(settings, 'PAGERDUTY_SEND_ON_INCIDENT_CREATE', True)

    @property
    def send_on_incident_update(self) -> bool:
        """Whether to send PagerDuty events when NetBox Incidents are updated."""
        return getattr(settings, 'PAGERDUTY_SEND_ON_INCIDENT_UPDATE', True)

    @property
    def auto_resolve(self) -> bool:
        """Whether to auto-resolve PagerDuty incidents when NetBox incidents are resolved."""
        return getattr(settings, 'PAGERDUTY_AUTO_RESOLVE', True)

    @property
    def timeout(self) -> int:
        """HTTP timeout in seconds for PagerDuty API calls."""
        return getattr(settings, 'PAGERDUTY_TIMEOUT', 30)

    @property
    def component(self) -> str:
        """Default component name for PagerDuty events."""
        return getattr(settings, 'PAGERDUTY_COMPONENT', 'netbox-business-application')

    @property
    def group(self) -> str:
        """Default group name for PagerDuty events."""
        return getattr(settings, 'PAGERDUTY_GROUP', 'infrastructure')

pagerduty_config = PagerDutyConfig()


class PagerDutyEventSeverity:
    """PagerDuty event severity levels."""
    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


class PagerDutyEventAction:
    """PagerDuty event actions."""
    TRIGGER = 'trigger'
    ACKNOWLEDGE = 'acknowledge'
    RESOLVE = 'resolve'


class PagerDutyClient:
    """
    Client for PagerDuty Events API v2.

    Usage:
        client = PagerDutyClient()

        # Trigger an event
        result = client.trigger(
            summary="Database connection failed",
            severity="critical",
            source="db-server-01",
            dedup_key="db-connection-failure-001"
        )

        # Acknowledge an event
        result = client.acknowledge(dedup_key="db-connection-failure-001")

        # Resolve an event
        result = client.resolve(dedup_key="db-connection-failure-001")
    """

    def __init__(self, routing_key: Optional[str] = None):
        """
        Initialize PagerDuty client.

        Args:
            routing_key: Optional override for the global routing key
        """
        self.config = pagerduty_config
        self._routing_key = routing_key
        self.logger = logger

    @property
    def routing_key(self) -> Optional[str]:
        """Get the routing key to use."""
        return self._routing_key or self.config.routing_key

    @property
    def is_configured(self) -> bool:
        """Check if PagerDuty is properly configured."""
        return bool(self.config.enabled and self.routing_key)

    def _send_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send event to PagerDuty Events API v2.

        Args:
            payload: Event payload dictionary

        Returns:
            Response from PagerDuty API

        Raises:
            PagerDutyError: If the API call fails
        """
        if not self.is_configured:
            self.logger.warning("PagerDuty is not configured, skipping event")
            return {'status': 'skipped', 'message': 'PagerDuty not configured'}

        payload['routing_key'] = self.routing_key

        try:
            json_data = json.dumps(payload).encode('utf-8')

            request = Request(
                self.config.events_api_url,
                data=json_data,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                method='POST'
            )

            self.logger.debug(f"Sending PagerDuty event: {payload.get('event_action')} - {payload.get('dedup_key')}")

            with urlopen(request, timeout=self.config.timeout) as response:
                response_data = json.loads(response.read().decode('utf-8'))

                self.logger.info(
                    f"PagerDuty event sent successfully: "
                    f"action={payload.get('event_action')}, "
                    f"dedup_key={payload.get('dedup_key')}, "
                    f"status={response_data.get('status')}"
                )

                return response_data

        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            self.logger.error(
                f"PagerDuty API error: {e.code} - {error_body}"
            )
            raise PagerDutyError(f"HTTP {e.code}: {error_body}") from e

        except URLError as e:
            self.logger.error(f"PagerDuty connection error: {e.reason}")
            raise PagerDutyError(f"Connection error: {e.reason}") from e

        except json.JSONDecodeError as e:
            self.logger.error(f"PagerDuty response parse error: {e}")
            raise PagerDutyError(f"Invalid JSON response: {e}") from e

        except Exception as e:
            self.logger.exception(f"Unexpected error sending PagerDuty event: {e}")
            raise PagerDutyError(f"Unexpected error: {e}") from e

    def trigger(
            self,
            summary: str,
            severity: str = PagerDutyEventSeverity.ERROR,
            source: Optional[str] = None,
            dedup_key: Optional[str] = None,
            component: Optional[str] = None,
            group: Optional[str] = None,
            event_class: Optional[str] = None,
            custom_details: Optional[Dict[str, Any]] = None,
            links: Optional[list] = None,
            images: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a new PagerDuty event.

        Args:
            summary: A brief text summary of the event (max 1024 chars)
            severity: Event severity (critical, error, warning, info)
            source: The source of the event (default: config source)
            dedup_key: Deduplication key for this event
            component: Component responsible for the event
            group: Logical grouping of components
            event_class: Class/type of the event
            custom_details: Additional details as key-value pairs
            links: List of link objects with href and text
            images: List of image objects with src, href, alt

        Returns:
            PagerDuty API response
        """
        payload = {
            'event_action': PagerDutyEventAction.TRIGGER,
            'payload': {
                'summary': summary[:1024],  # Max 1024 chars?? Maybe more... - SKU
                'severity': severity,
                'source': source or self.config.source,
                'timestamp': timezone.now().isoformat(),
            }
        }

        if dedup_key:
            payload['dedup_key'] = dedup_key

        if component:
            payload['payload']['component'] = component
        elif self.config.component:
            payload['payload']['component'] = self.config.component

        if group:
            payload['payload']['group'] = group
        elif self.config.group:
            payload['payload']['group'] = self.config.group

        if event_class:
            payload['payload']['class'] = event_class

        if custom_details:
            payload['payload']['custom_details'] = custom_details

        if links:
            payload['links'] = links

        if images:
            payload['images'] = images

        return self._send_event(payload)

    def acknowledge(self, dedup_key: str) -> Dict[str, Any]:
        """
        Acknowledge an existing PagerDuty event.

        Args:
            dedup_key: The deduplication key of the event to acknowledge

        Returns:
            PagerDuty API response
        """
        payload = {
            'event_action': PagerDutyEventAction.ACKNOWLEDGE,
            'dedup_key': dedup_key,
        }

        return self._send_event(payload)

    def resolve(self, dedup_key: str) -> Dict[str, Any]:
        """
        Resolve an existing PagerDuty event.

        Args:
            dedup_key: The deduplication key of the event to resolve

        Returns:
            PagerDuty API response
        """
        payload = {
            'event_action': PagerDutyEventAction.RESOLVE,
            'dedup_key': dedup_key,
        }

        return self._send_event(payload)


class PagerDutyError(Exception):
    """Exception raised for PagerDuty API errors."""
    pass

def generate_dedup_key(prefix: str, obj_id: int, obj_type: str = 'generic') -> str:
    """
    Generate a consistent deduplication key for an object.

    Args:
        prefix: Prefix for the key (e.g., 'event', 'incident')
        obj_id: Object ID
        obj_type: Type of object

    Returns:
        Deduplication key string
    """
    return f"netbox-{prefix}-{obj_type}-{obj_id}"


def map_netbox_severity_to_pagerduty(severity: str) -> str:
    """
    Map NetBox criticality/severity to PagerDuty severity.

    Args:
        severity: NetBox severity (CRITICAL, HIGH, MEDIUM, LOW, etc.)

    Returns:
        PagerDuty severity string
    """
    mapping = {
        'CRITICAL': PagerDutyEventSeverity.CRITICAL,
        'critical': PagerDutyEventSeverity.CRITICAL,
        'HIGH': PagerDutyEventSeverity.ERROR,
        'high': PagerDutyEventSeverity.ERROR,
        'MEDIUM': PagerDutyEventSeverity.WARNING,
        'medium': PagerDutyEventSeverity.WARNING,
        'LOW': PagerDutyEventSeverity.INFO,
        'low': PagerDutyEventSeverity.INFO,
        'INFO': PagerDutyEventSeverity.INFO,
        'info': PagerDutyEventSeverity.INFO,
        'OK': PagerDutyEventSeverity.INFO,
        'ok': PagerDutyEventSeverity.INFO,
    }
    return mapping.get(severity, PagerDutyEventSeverity.WARNING)


def map_netbox_status_to_pagerduty_action(status: str) -> Optional[str]:
    """
    Map NetBox event/incident status to PagerDuty action.

    Args:
        status: NetBox status

    Returns:
        PagerDuty action or None if no action needed
    """
    status_lower = status.lower()

    if status_lower in ('triggered', 'new', 'investigating', 'identified'):
        return PagerDutyEventAction.TRIGGER

    if status_lower in ('acknowledged', 'monitoring'):
        return PagerDutyEventAction.ACKNOWLEDGE

    if status_lower in ('ok', 'resolved', 'closed', 'suppressed'):
        return PagerDutyEventAction.RESOLVE

    return None


def send_event_to_pagerduty(event) -> Optional[Dict[str, Any]]:
    """
    Send a NetBox Event to PagerDuty.

    Args:
        event: NetBox Event instance

    Returns:
        PagerDuty API response or None if skipped
    """
    config = pagerduty_config

    if not config.enabled or not config.send_on_event_create:
        logger.debug("PagerDuty event sending disabled, skipping")
        return None

    client = PagerDutyClient()

    if not client.is_configured:
        logger.warning("PagerDuty not configured, skipping event send")
        return None

    try:
        action = map_netbox_status_to_pagerduty_action(event.status)

        if action == PagerDutyEventAction.RESOLVE:
            return client.resolve(
                dedup_key=f"netbox-event-{event.dedup_id}"
            )
        elif action == PagerDutyEventAction.ACKNOWLEDGE:
            return client.acknowledge(
                dedup_key=f"netbox-event-{event.dedup_id}"
            )
        else:
            custom_details = {
                'event_id': event.id,
                'dedup_id': event.dedup_id,
                'status': event.status,
                'criticality': event.criticallity,
                'created_at': event.created_at.isoformat() if event.created_at else None,
                'last_seen_at': event.last_seen_at.isoformat() if event.last_seen_at else None,
            }

            if event.has_valid_target and event.obj:
                custom_details['target_type'] = event.content_type.model if event.content_type else 'unknown'
                custom_details['target_name'] = str(event.obj)
                custom_details['target_id'] = event.object_id

            if event.event_source:
                custom_details['event_source'] = event.event_source.name

            source = config.source
            if event.has_valid_target and event.obj:
                source = f"{config.source}:{event.content_type.model}:{event.obj}"

            links = []
            try:
                from django.conf import settings
                base_url = getattr(settings, 'BASE_URL', '')
                if base_url:
                    links.append({
                        'href': f"{base_url}{event.get_absolute_url()}",
                        'text': 'View Event in NetBox'
                    })
            except Exception:
                pass

            return client.trigger(
                summary=event.message[:1024],
                severity=map_netbox_severity_to_pagerduty(event.criticallity),
                source=source,
                dedup_key=f"netbox-event-{event.dedup_id}",
                component=event.event_source.name if event.event_source else 'unknown',
                event_class='netbox_event',
                custom_details=custom_details,
                links=links if links else None,
            )

    except PagerDutyError as e:
        logger.error(f"Failed to send event {event.id} to PagerDuty: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error sending event {event.id} to PagerDuty: {e}")
        return None


def send_incident_to_pagerduty(incident, action: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Send a NetBox Incident to PagerDuty.

    Args:
        incident: NetBox Incident instance
        action: Optional override for action (trigger, acknowledge, resolve)

    Returns:
        PagerDuty API response or None if skipped
    """
    config = pagerduty_config

    if not config.enabled:
        logger.debug("PagerDuty disabled, skipping")
        return None

    client = PagerDutyClient()

    if not client.is_configured:
        logger.warning("PagerDuty not configured, skipping incident send")
        return None

    try:
        dedup_key = f"netbox-incident-{incident.id}"

        if not action:
            action = map_netbox_status_to_pagerduty_action(incident.status)

        if action == PagerDutyEventAction.RESOLVE:
            if not config.auto_resolve:
                logger.debug("PagerDuty auto-resolve disabled, skipping")
                return None
            return client.resolve(dedup_key=dedup_key)

        elif action == PagerDutyEventAction.ACKNOWLEDGE:
            return client.acknowledge(dedup_key=dedup_key)

        else:
            summary = f"[{incident.severity.upper()}] {incident.title}"

            custom_details = {
                'incident_id': incident.id,
                'title': incident.title,
                'description': incident.description[:2000] if incident.description else None,
                'status': incident.status,
                'severity': incident.severity,
                'created_at': incident.created_at.isoformat() if incident.created_at else None,
                'detected_at': incident.detected_at.isoformat() if incident.detected_at else None,
                'reporter': incident.reporter,
                'commander': incident.commander,
            }

            affected_services = list(incident.affected_services.values_list('name', flat=True))
            if affected_services:
                custom_details['affected_services'] = affected_services
                custom_details['affected_services_count'] = len(affected_services)

            custom_details['events_count'] = incident.events.count()

            responders = list(incident.responders.values_list('username', flat=True))
            if responders:
                custom_details['responders'] = responders

            component = 'multiple-services'
            if affected_services:
                if len(affected_services) == 1:
                    component = affected_services[0]
                else:
                    component = f"{affected_services[0]} (+{len(affected_services) - 1} more)"

            links = []
            try:
                from django.conf import settings
                base_url = getattr(settings, 'BASE_URL', '')
                if base_url:
                    links.append({
                        'href': f"{base_url}{incident.get_absolute_url()}",
                        'text': 'View Incident in NetBox'
                    })
            except Exception:
                pass

            return client.trigger(
                summary=summary[:1024],
                severity=map_netbox_severity_to_pagerduty(incident.severity),
                source=config.source,
                dedup_key=dedup_key,
                component=component,
                event_class='netbox_incident',
                custom_details=custom_details,
                links=links if links else None,
            )

    except PagerDutyError as e:
        logger.error(f"Failed to send incident {incident.id} to PagerDuty: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error sending incident {incident.id} to PagerDuty: {e}")
        return None


def update_incident_pagerduty_status(incident, old_status: str, new_status: str) -> Optional[Dict[str, Any]]:
    """
    Update PagerDuty based on incident status change.

    Args:
        incident: NetBox Incident instance
        old_status: Previous status
        new_status: New status

    Returns:
        PagerDuty API response or None if skipped
    """
    config = pagerduty_config

    if not config.enabled or not config.send_on_incident_update:
        return None

    old_action = map_netbox_status_to_pagerduty_action(old_status)
    new_action = map_netbox_status_to_pagerduty_action(new_status)

    if old_action != new_action and new_action:
        return send_incident_to_pagerduty(incident, action=new_action)

    return None