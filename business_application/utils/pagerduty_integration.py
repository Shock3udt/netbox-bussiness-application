# business_application/utils/pagerduty_integration.py
"""
PagerDuty integration module for NetBox Business Application plugin.

Handles:
- Creating PagerDuty incidents from NetBox incidents
- Resolving PagerDuty incidents when NetBox incidents are resolved
- Acknowledging PagerDuty incidents when NetBox incidents are being investigated

Routing Key Priority:
1. First affected TechnicalService with pagerduty_routing_key
2. First affected BusinessApplication with pagerduty_routing_key
3. Global fallback from plugin settings (pagerduty_events_api_key)
"""

import requests
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from django.conf import settings

logger = logging.getLogger('business_application.pagerduty')

# The single, global endpoint for the PagerDuty Events API v2
PAGERDUTY_EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"


class PagerDutyIncidentManager:
    """
    Handles PagerDuty incident creation and management for NetBox incidents.
    Uses the PagerDuty Events API v2 to create incidents via event orchestration.

    Supports per-service and per-application routing keys.
    """

    def __init__(self):
        self.logger = logger
        self.api_url = PAGERDUTY_EVENTS_API_URL

    @property
    def is_enabled(self) -> bool:
        """Check if PagerDuty integration is enabled in settings."""
        return getattr(settings, 'PLUGINS_CONFIG', {}).get(
            'business_application', {}
        ).get('pagerduty_incident_creation_enabled', False)

    def get_routing_key_for_incident(self, incident) -> Tuple[Optional[str], Optional[str]]:
        """
        Determine the appropriate routing key for an incident.

        Priority:
        1. First affected TechnicalService with pagerduty_routing_key
        2. First affected BusinessApplication with pagerduty_routing_key

        Note: There is no global fallback. Routing key must be configured
        on TechnicalService or BusinessApplication.

        Args:
            incident: The NetBox Incident object

        Returns:
            Tuple of (routing_key, source_description)
            source_description indicates where the key came from
        """
        # Priority 1: Check TechnicalServices
        for service in incident.affected_services.all():
            routing_key = getattr(service, 'pagerduty_routing_key', None)
            if routing_key:
                self.logger.debug(
                    f"Using routing key from TechnicalService '{service.name}' for incident {incident.id}"
                )
                return routing_key, f"TechnicalService: {service.name}"

        # Priority 2: Check BusinessApplications (via affected services)
        for service in incident.affected_services.all():
            for app in service.business_apps.all():
                routing_key = getattr(app, 'pagerduty_routing_key', None)
                if routing_key:
                    self.logger.debug(
                        f"Using routing key from BusinessApplication '{app.name}' for incident {incident.id}"
                    )
                    return routing_key, f"BusinessApplication: {app.name}"

        # No routing key found
        return None, None

    def create_pagerduty_incident(self, netbox_incident) -> Optional[Dict]:
        """
        Create a PagerDuty incident for the given NetBox incident.

        Args:
            netbox_incident: The NetBox incident to create in PagerDuty

        Returns:
            Dict containing PagerDuty response or None if creation failed
        """
        if not self.is_enabled:
            self.logger.debug("PagerDuty integration is disabled")
            return None

        routing_key, routing_source = self.get_routing_key_for_incident(netbox_incident)

        if not routing_key:
            self.logger.warning(
                f"No PagerDuty routing key found for incident {netbox_incident.id}. "
                f"Configure routing key on TechnicalService, BusinessApplication, or in plugin settings."
            )
            return None

        try:
            self.logger.info(
                f"Creating PagerDuty incident for NetBox incident {netbox_incident.id} "
                f"using routing key from: {routing_source}"
            )

            payload = self._build_pagerduty_payload(netbox_incident, routing_key)
            response = self._send_pagerduty_request(payload)

            if response and 'dedup_key' in response:
                # Save the PagerDuty dedup key to the NetBox incident
                netbox_incident.pagerduty_dedup_key = response['dedup_key']
                netbox_incident.save(update_fields=['pagerduty_dedup_key'])

                self.logger.info(
                    f"Successfully created PagerDuty incident for NetBox incident {netbox_incident.id}, "
                    f"dedup_key: {response['dedup_key']}, routing_source: {routing_source}"
                )
                return response
            else:
                self.logger.error(
                    f"Failed to create PagerDuty incident for NetBox incident {netbox_incident.id} "
                    f"or missing dedup_key in response: {response}"
                )
                return None

        except Exception as e:
            self.logger.exception(
                f"Error creating PagerDuty incident for NetBox incident {netbox_incident.id}: {str(e)}"
            )
            return None

    def resolve_pagerduty_incident(self, netbox_incident) -> Optional[Dict]:
        """
        Resolve a PagerDuty incident when the NetBox incident is resolved.

        Args:
            netbox_incident: The NetBox incident that was resolved

        Returns:
            Dict containing PagerDuty response or None if resolution failed
        """
        if not self.is_enabled:
            self.logger.debug("PagerDuty integration is disabled")
            return None

        # Check if we have the PagerDuty dedup key saved
        if not netbox_incident.pagerduty_dedup_key:
            self.logger.warning(
                f"No PagerDuty dedup key found for NetBox incident {netbox_incident.id}. "
                f"This incident was likely not created in PagerDuty, skipping resolution."
            )
            return None

        routing_key, routing_source = self.get_routing_key_for_incident(netbox_incident)

        if not routing_key:
            self.logger.error(
                f"No PagerDuty routing key found for incident {netbox_incident.id}. "
                f"Cannot resolve PagerDuty incident without routing key."
            )
            return None

        dedup_key = netbox_incident.pagerduty_dedup_key

        try:
            payload = {
                "routing_key": routing_key,
                "event_action": "resolve",
                "dedup_key": dedup_key,
                "client": "NetBox Business Application",
                "client_url": self._get_netbox_incident_url(netbox_incident),
            }

            response = self._send_pagerduty_request(payload)

            if response:
                self.logger.info(
                    f"Successfully resolved PagerDuty incident for NetBox incident {netbox_incident.id} "
                    f"using dedup_key: {dedup_key}, routing_source: {routing_source}"
                )
                return response
            else:
                self.logger.error(
                    f"Failed to resolve PagerDuty incident for NetBox incident {netbox_incident.id} "
                    f"using dedup_key: {dedup_key}"
                )
                return None

        except Exception as e:
            self.logger.exception(
                f"Error resolving PagerDuty incident for NetBox incident {netbox_incident.id}: {str(e)}"
            )
            return None

    def acknowledge_pagerduty_incident(self, netbox_incident) -> Optional[Dict]:
        """
        Acknowledge a PagerDuty incident when the NetBox incident is being investigated.

        Args:
            netbox_incident: The NetBox incident that is being acknowledged

        Returns:
            Dict containing PagerDuty response or None if acknowledgment failed
        """
        if not self.is_enabled:
            self.logger.debug("PagerDuty integration is disabled")
            return None

        # Check if we have the PagerDuty dedup key saved
        if not netbox_incident.pagerduty_dedup_key:
            self.logger.warning(
                f"No PagerDuty dedup key found for NetBox incident {netbox_incident.id}. "
                f"This incident was likely not created in PagerDuty, skipping acknowledgment."
            )
            return None

        routing_key, routing_source = self.get_routing_key_for_incident(netbox_incident)

        if not routing_key:
            self.logger.error(
                f"No PagerDuty routing key found for incident {netbox_incident.id}. "
                f"Cannot acknowledge PagerDuty incident without routing key."
            )
            return None

        dedup_key = netbox_incident.pagerduty_dedup_key

        try:
            payload = {
                "routing_key": routing_key,
                "event_action": "acknowledge",
                "dedup_key": dedup_key,
                "client": "NetBox Business Application",
                "client_url": self._get_netbox_incident_url(netbox_incident),
            }

            response = self._send_pagerduty_request(payload)

            if response:
                self.logger.info(
                    f"Successfully acknowledged PagerDuty incident for NetBox incident {netbox_incident.id} "
                    f"using dedup_key: {dedup_key}, routing_source: {routing_source}"
                )
                return response
            else:
                self.logger.error(
                    f"Failed to acknowledge PagerDuty incident for NetBox incident {netbox_incident.id} "
                    f"using dedup_key: {dedup_key}"
                )
                return None

        except Exception as e:
            self.logger.exception(
                f"Error acknowledging PagerDuty incident for NetBox incident {netbox_incident.id}: {str(e)}"
            )
            return None

    def _build_pagerduty_payload(self, incident, routing_key: str) -> Dict:
        """Build the PagerDuty Events API payload for an incident."""

        # Generate timestamp in ISO 8601 format with UTC
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        # Map NetBox severity to PagerDuty severity
        severity_map = {
            'critical': 'critical',
            'high': 'error',
            'medium': 'warning',
            'low': 'info'
        }

        # Get affected services information
        affected_services = list(incident.affected_services.all())
        service_names = [service.name for service in affected_services]

        # Build service details for custom details
        service_details = []
        for service in affected_services:
            service_info = {
                "name": service.name,
                "type": service.service_type,
                "has_pagerduty_integration": service.has_pagerduty_integration,
                "has_routing_key": bool(getattr(service, 'pagerduty_routing_key', None)),
            }
            if service.pagerduty_service_definition:
                service_info["pagerduty_template"] = service.pagerduty_service_definition.name
            service_details.append(service_info)

        # Get related events information
        related_events = list(incident.events.all())
        event_sources = list(set([
            event.event_source.name
            for event in related_events
            if event.event_source
        ]))

        # Get business applications
        business_apps = set()
        for service in affected_services:
            for app in service.business_apps.all():
                business_apps.add(app.name)

        payload = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "dedup_key": self._generate_dedup_key(incident),
            "client": "NetBox Business Application",
            "client_url": self._get_netbox_incident_url(incident),
            "payload": {
                "summary": self._generate_summary(incident, service_names),
                "source": f"netbox-incident-{incident.id}",
                "severity": severity_map.get(incident.severity, 'warning'),
                "timestamp": timestamp,
                "component": "business-application",
                "group": "netbox-incidents",
                "class": f"incident-{incident.severity}",
                "custom_details": {
                    "NetBox Incident ID": incident.id,
                    "NetBox Incident Title": incident.title,
                    "NetBox Incident Status": incident.status,
                    "NetBox Incident Severity": incident.severity,
                    "NetBox Incident Description": incident.description or "No description provided",
                    "Incident Reporter": incident.reporter or "System",
                    "Incident Commander": incident.commander or "Not assigned",
                    "Created At": incident.created_at.isoformat() if incident.created_at else None,
                    "Detected At": incident.detected_at.isoformat() if incident.detected_at else None,
                    "NetBox Incident URL": self._get_netbox_incident_url(incident),
                    "Affected Services": service_names,
                    "Service Count": len(affected_services),
                    "Service Details": service_details,
                    "Business Applications": list(business_apps),
                    "Related Events Count": len(related_events),
                    "Event Sources": event_sources,
                    "Responders Count": incident.responders.count() if hasattr(incident, 'responders') else 0,
                }
            }
        }

        return payload

    def _generate_dedup_key(self, incident) -> str:
        """Generate a unique deduplication key for the incident."""
        return f"netbox-incident-{incident.id}"

    def _generate_summary(self, incident, service_names: List[str]) -> str:
        """Generate a concise summary for the PagerDuty incident."""
        if service_names:
            services_text = ", ".join(service_names[:3])
            if len(service_names) > 3:
                services_text += f" and {len(service_names) - 3} more"
            return f"NetBox Incident: {services_text} - {incident.title[:100]}"
        else:
            return f"NetBox Incident: {incident.title[:150]}"

    def _get_netbox_incident_url(self, incident) -> str:
        """Generate the full NetBox URL for the incident."""
        base_url = getattr(settings, 'BASE_URL', 'https://netbox.example.com')
        if base_url.endswith('/'):
            base_url = base_url.rstrip('/')

        try:
            # Use the incident's get_absolute_url method
            relative_url = incident.get_absolute_url()
            return f"{base_url}{relative_url}"
        except Exception:
            # Fallback to manual construction
            return f"{base_url}/plugins/business-application/incidents/{incident.id}/"

    def _send_pagerduty_request(self, payload: Dict) -> Optional[Dict]:
        """Send request to PagerDuty Events API."""
        try:
            headers = {'Content-Type': 'application/json'}

            self.logger.debug(f"Sending PagerDuty request: {json.dumps(payload, indent=2)}")

            response = requests.post(
                self.api_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=30  # 30 second timeout
            )

            response.raise_for_status()  # Raise an exception for bad status codes

            response_data = response.json()
            self.logger.debug(f"PagerDuty response: {json.dumps(response_data, indent=2)}")

            return response_data

        except requests.exceptions.RequestException as e:
            self.logger.error(f"PagerDuty API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"Response status: {e.response.status_code}")
                self.logger.error(f"Response body: {e.response.text}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in PagerDuty request: {str(e)}")
            return None


# Convenience functions for easy importing
def create_pagerduty_incident(netbox_incident) -> Optional[Dict]:
    """
    Convenience function to create a PagerDuty incident.

    Args:
        netbox_incident: The NetBox incident to create in PagerDuty

    Returns:
        Dict containing PagerDuty response or None if creation failed
    """
    manager = PagerDutyIncidentManager()
    return manager.create_pagerduty_incident(netbox_incident)


def resolve_pagerduty_incident(netbox_incident) -> Optional[Dict]:
    """
    Convenience function to resolve a PagerDuty incident.

    Args:
        netbox_incident: The NetBox incident that was resolved

    Returns:
        Dict containing PagerDuty response or None if resolution failed
    """
    manager = PagerDutyIncidentManager()
    return manager.resolve_pagerduty_incident(netbox_incident)


def acknowledge_pagerduty_incident(netbox_incident) -> Optional[Dict]:
    """
    Convenience function to acknowledge a PagerDuty incident.

    Args:
        netbox_incident: The NetBox incident that is being acknowledged

    Returns:
        Dict containing PagerDuty response or None if acknowledgment failed
    """
    manager = PagerDutyIncidentManager()
    return manager.acknowledge_pagerduty_incident(netbox_incident)


def get_routing_key_info(netbox_incident) -> Dict:
    """
    Get information about which routing key would be used for an incident.
    Useful for debugging and UI display.

    Args:
        netbox_incident: The NetBox incident to check

    Returns:
        Dict with routing key information
    """
    manager = PagerDutyIncidentManager()
    routing_key, source = manager.get_routing_key_for_incident(netbox_incident)

    return {
        'has_routing_key': bool(routing_key),
        'routing_key_masked': f"{routing_key[:8]}...{routing_key[-4:]}" if routing_key and len(
            routing_key) > 12 else None,
        'routing_source': source,
        'is_enabled': manager.is_enabled,
    }