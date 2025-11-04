# business_application/utils/pagerduty_integration.py
import requests
import json
import uuid
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict
from django.conf import settings
from business_application.models import Incident, TechnicalService

logger = logging.getLogger('business_application.pagerduty')

# The single, global endpoint for the PagerDuty Events API v2
PAGERDUTY_EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"


class PagerDutyIncidentManager:
    """
    Handles PagerDuty incident creation and management for NetBox incidents.
    Uses the PagerDuty Events API v2 to create incidents via event orchestration.
    """

    def __init__(self):
        self.logger = logger
        self.api_url = PAGERDUTY_EVENTS_API_URL

    @property
    def is_enabled(self) -> bool:
        """Check if PagerDuty integration is enabled in settings or environment."""
        # Check plugin configuration first
        plugin_enabled = getattr(settings, 'PLUGINS_CONFIG', {}).get(
            'business_application', {}
        ).get('pagerduty_incident_creation_enabled', False)

        # Fall back to environment variable
        env_enabled = os.environ.get('PAGERDUTY_ENABLED', 'true').lower() == 'true'

        return plugin_enabled or env_enabled

    @property
    def routing_key(self) -> Optional[str]:
        """No default routing key - all routing keys are service-specific."""
        return None

    def find_routing_key_for_incident(self, incident: Incident) -> Optional[str]:
        """
        Find the best routing key for an incident using closest common ancestor logic.

        For each affected service, finds the closest ancestor with a routing key.
        Returns the routing key from the ancestor with shortest overall distance.
        If multiple ancestors at same distance, picks randomly.
        """
        import random

        affected_services = list(incident.affected_services.all())
        if not affected_services:
            self.logger.warning("No affected services found for incident")
            return None

        # Find closest ancestors with routing keys for each affected service
        candidates = []  # List of (service_with_routing_key, distance, source_service)

        for service in affected_services:
            # First, check if the service itself has a routing key
            if service.pagerduty_routing_key and service.pagerduty_routing_key.strip():
                candidates.append((service, 0, service))
                continue

            # Otherwise, find closest ancestor with routing key
            ancestor_service, distance = service.find_closest_ancestor_with_routing_key()
            if ancestor_service and distance is not None:
                candidates.append((ancestor_service, distance, service))

        if not candidates:
            self.logger.warning("No services with routing keys found in incident dependency chain")
            return None

        # Find the minimum distance
        min_distance = min(candidate[1] for candidate in candidates)
        closest_candidates = [c for c in candidates if c[1] == min_distance]

        # If multiple candidates at same distance, pick randomly
        chosen_candidate = random.choice(closest_candidates)
        chosen_service, distance, source_service = chosen_candidate

        self.logger.info(
            f"Selected routing key from service '{chosen_service.name}' "
            f"(distance {distance} from affected service '{source_service.name}')"
        )

        return chosen_service.pagerduty_routing_key

    def create_pagerduty_incident(self, netbox_incident: Incident) -> Optional[Dict]:
        """
        Create a PagerDuty incident for the given NetBox incident.
        Uses closest common ancestor logic to find the best routing key.

        Args:
            netbox_incident: The NetBox incident to create in PagerDuty

        Returns:
            Dict containing PagerDuty response or None if creation failed
        """
        if not self.is_enabled:
            self.logger.debug("PagerDuty integration is disabled")
            return None

        routing_key = self.find_routing_key_for_incident(netbox_incident)
        if not routing_key:
            self.logger.error("No suitable routing key found for incident using ancestor traversal")
            return None

        try:
            payload = self._build_pagerduty_payload(netbox_incident, routing_key)
            response = self._send_pagerduty_request(payload)

            if response and 'dedup_key' in response:
                # Save the PagerDuty dedup key to the NetBox incident
                netbox_incident.pagerduty_dedup_key = response['dedup_key']
                netbox_incident.save(update_fields=['pagerduty_dedup_key'])

                self.logger.info(
                    f"Successfully created PagerDuty incident for NetBox incident {netbox_incident.id}, "
                    f"dedup_key: {response['dedup_key']}"
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

    def resolve_pagerduty_incident(self, netbox_incident: Incident) -> Optional[Dict]:
        """
        Resolve a PagerDuty incident when the NetBox incident is resolved.
        Uses the same routing key selection logic as incident creation.

        Args:
            netbox_incident: The NetBox incident that was resolved

        Returns:
            Dict containing PagerDuty response or None if resolution failed
        """
        if not self.is_enabled:
            return None

        routing_key = self.find_routing_key_for_incident(netbox_incident)
        if not routing_key:
            self.logger.warning("No suitable routing key found for incident resolution")
            return None

        # Check if we have the PagerDuty dedup key saved
        if not netbox_incident.pagerduty_dedup_key:
            self.logger.warning(
                f"No PagerDuty dedup key found for NetBox incident {netbox_incident.id}. "
                f"This incident was likely not created in PagerDuty, skipping resolution."
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
                    f"using dedup_key: {dedup_key}"
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

    def _build_pagerduty_payload(self, incident: Incident) -> Dict:
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
            }
            if service.pagerduty_service_definition:
                service_info["pagerduty_template"] = service.pagerduty_service_definition.name
            service_details.append(service_info)

        # Get related events information
        related_events = list(incident.events.all())
        event_sources = list(set([event.event_source.name for event in related_events if event.event_source]))

        payload = {
            "routing_key": self.routing_key,
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
                    "Related Events Count": len(related_events),
                    "Event Sources": event_sources,
                    "Responders Count": incident.responders.count() if hasattr(incident, 'responders') else 0,
                }
            }
        }

        return payload

    def _generate_dedup_key(self, incident: Incident) -> str:
        """Generate a unique deduplication key for the incident."""
        return f"netbox-incident-{incident.id}"

    def _generate_summary(self, incident: Incident, service_names: List[str]) -> str:
        """Generate a concise summary for the PagerDuty incident."""
        if service_names:
            services_text = ", ".join(service_names[:3])
            if len(service_names) > 3:
                services_text += f" and {len(service_names) - 3} more"
            return f"NetBox Incident: {services_text} - {incident.title[:100]}"
        else:
            return f"NetBox Incident: {incident.title[:150]}"

    def _get_netbox_incident_url(self, incident: Incident) -> str:
        """Generate the full NetBox URL for the incident."""
        server_name = os.environ.get('SERVER_NAME', 'netbox.corp.redhat.com')
        base_url = f"https://{server_name}"

        try:
            relative_url = incident.get_absolute_url()
            return f"{base_url}{relative_url}"
        except Exception:
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
                timeout=30
            )

            response.raise_for_status()

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


def create_pagerduty_incident(netbox_incident: Incident) -> Optional[Dict]:
    """
    Convenience function to create a PagerDuty incident.

    Args:
        netbox_incident: The NetBox incident to create in PagerDuty

    Returns:
        Dict containing PagerDuty response or None if creation failed
    """
    manager = PagerDutyIncidentManager()
    return manager.create_pagerduty_incident(netbox_incident)


def resolve_pagerduty_incident(netbox_incident: Incident) -> Optional[Dict]:
    """
    Convenience function to resolve a PagerDuty incident.

    Args:
        netbox_incident: The NetBox incident that was resolved

    Returns:
        Dict containing PagerDuty response or None if resolution failed
    """
    manager = PagerDutyIncidentManager()
    return manager.resolve_pagerduty_incident(netbox_incident)
