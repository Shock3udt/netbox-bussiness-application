# business_application/utils/pagerduty_integration.py

import requests
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple, Set
from django.conf import settings

logger = logging.getLogger('business_application.pagerduty')

# The single, global endpoint for the PagerDuty Events API v2
PAGERDUTY_EVENTS_API_URL = "https://events.pagerduty.com/v2/enqueue"


class PagerDutyIncidentManager:
    """
    Handles PagerDuty incident creation and management for NetBox incidents.
    Uses the PagerDuty Events API v2 to create incidents via event orchestration.

    Supports hierarchical per-service routing keys with upstream inheritance.
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

    def _get_service_depth(self, service, visited: Set[int] = None) -> int:
        """
        Calculate the depth of a service in the dependency hierarchy.
        Root services (no upstream dependencies) have depth 0.
        Services with upstream dependencies have depth = max(parent depths) + 1
        """
        if visited is None:
            visited = set()

        if service.id in visited:
            return 0  # Circular dependency protection
        visited.add(service.id)

        upstream_deps = service.upstream_dependencies.all()
        if not upstream_deps.exists():
            return 0  # Root service

        max_parent_depth = 0
        for dep in upstream_deps:
            parent_depth = self._get_service_depth(dep.upstream_service, visited.copy())
            max_parent_depth = max(max_parent_depth, parent_depth)

        return max_parent_depth + 1

    def _sort_services_by_hierarchy(self, services) -> List:
        """
        Sort services so that root/parent services come first.
        Services with lower depth (closer to root) come before those with higher depth.
        """
        services_with_depth = []
        for service in services:
            depth = self._get_service_depth(service)
            services_with_depth.append((depth, service))

        # Sort by depth (ascending - roots first)
        services_with_depth.sort(key=lambda x: x[0])

        return [service for depth, service in services_with_depth]

    def _find_routing_key_upstream(self, service, visited: Set[int] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Recursively search upstream (toward parents/roots) for a routing key.

        Args:
            service: TechnicalService to start searching from
            visited: Set of already visited service IDs (for circular dependency protection)

        Returns:
            Tuple of (routing_key, source_service_name) or (None, None)
        """
        if visited is None:
            visited = set()

        if service.id in visited:
            return None, None  # Circular dependency protection
        visited.add(service.id)

        # Check if this service has a routing key
        routing_key = getattr(service, 'pagerduty_routing_key', None)
        if routing_key:
            self.logger.debug(
                f"Found routing key on TechnicalService '{service.name}'"
            )
            return routing_key, f"TechnicalService: {service.name}"

        # Get upstream (parent) services and check them
        # upstream_dependencies gives us ServiceDependency objects where this service is downstream
        for dependency in service.upstream_dependencies.all():
            upstream_service = dependency.upstream_service
            routing_key, source = self._find_routing_key_upstream(upstream_service, visited.copy())
            if routing_key:
                return routing_key, source

        return None, None

    def get_routing_key_for_incident(self, incident) -> Tuple[Optional[str], Optional[str]]:
        """
        Determine the appropriate routing key for an incident.

        Algorithm:
        1. Get affected TechnicalServices
        2. Sort by hierarchy (root services first)
        3. For each service, search upstream for routing key
        4. If no service has routing key, check BusinessApplications

        Args:
            incident: The NetBox Incident object

        Returns:
            Tuple of (routing_key, source_description)
            source_description indicates where the key came from
        """
        affected_services = list(incident.affected_services.all())

        if not affected_services:
            self.logger.debug(f"Incident {incident.id} has no affected services")
            return None, None

        # Sort services by hierarchy (roots first)
        sorted_services = self._sort_services_by_hierarchy(affected_services)

        self.logger.debug(
            f"Searching for routing key in {len(sorted_services)} services "
            f"(sorted by hierarchy): {[s.name for s in sorted_services]}"
        )

        # Search each service and its upstream hierarchy for routing key
        for service in sorted_services:
            routing_key, source = self._find_routing_key_upstream(service)
            if routing_key:
                self.logger.debug(
                    f"Found routing key for incident {incident.id} from: {source}"
                )
                return routing_key, source

        # Fallback: Check BusinessApplications
        self.logger.debug(
            f"No routing key found in service hierarchy, checking BusinessApplications"
        )

        for service in sorted_services:
            for app in service.business_apps.all():
                routing_key = getattr(app, 'pagerduty_routing_key', None)
                if routing_key:
                    self.logger.debug(
                        f"Found routing key on BusinessApplication '{app.name}'"
                    )
                    return routing_key, f"BusinessApplication: {app.name}"

        self.logger.debug(f"No routing key found for incident {incident.id}")
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
                f"Configure routing key on a root TechnicalService or BusinessApplication."
            )
            return None

        try:
            self.logger.info(
                f"Creating PagerDuty incident for NetBox incident {netbox_incident.id} "
                f"using routing key from: {routing_source}"
            )

            payload = self._build_pagerduty_payload(netbox_incident, routing_key, routing_source)
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

    def _build_pagerduty_payload(self, incident, routing_key: str, routing_source: str) -> Dict:
        """Build the PagerDuty Events API payload for an incident."""

        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        severity_map = {
            'critical': 'critical',
            'high': 'error',
            'medium': 'warning',
            'low': 'info'
        }

        affected_services = list(incident.affected_services.all())
        service_names = [service.name for service in affected_services]

        # Build service details including routing key info
        service_details = []
        for service in affected_services:
            svc_routing_key, svc_routing_source = self._find_routing_key_upstream(service)
            service_info = {
                "name": service.name,
                "type": service.service_type,
                "has_pagerduty_integration": service.has_pagerduty_integration,
                "has_own_routing_key": bool(getattr(service, 'pagerduty_routing_key', None)),
                "effective_routing_source": svc_routing_source,
            }
            if service.pagerduty_service_definition:
                service_info["pagerduty_template"] = service.pagerduty_service_definition.name
            service_details.append(service_info)

        related_events = list(incident.events.all())
        event_sources = list(set([
            event.event_source.name
            for event in related_events
            if event.event_source
        ]))

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
                    "Routing Key Source": routing_source,
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


# Convenience functions
def create_pagerduty_incident(netbox_incident) -> Optional[Dict]:
    """Create a PagerDuty incident."""
    manager = PagerDutyIncidentManager()
    return manager.create_pagerduty_incident(netbox_incident)


def resolve_pagerduty_incident(netbox_incident) -> Optional[Dict]:
    """Resolve a PagerDuty incident."""
    manager = PagerDutyIncidentManager()
    return manager.resolve_pagerduty_incident(netbox_incident)


def acknowledge_pagerduty_incident(netbox_incident) -> Optional[Dict]:
    """Acknowledge a PagerDuty incident."""
    manager = PagerDutyIncidentManager()
    return manager.acknowledge_pagerduty_incident(netbox_incident)


def get_routing_key_info(netbox_incident) -> Dict:
    """
    Get information about which routing key would be used for an incident.
    Useful for debugging and UI display.
    """
    manager = PagerDutyIncidentManager()
    routing_key, source = manager.get_routing_key_for_incident(netbox_incident)

    # Get hierarchy info
    affected_services = list(netbox_incident.affected_services.all())
    sorted_services = manager._sort_services_by_hierarchy(affected_services)

    hierarchy_info = []
    for service in sorted_services:
        depth = manager._get_service_depth(service)
        svc_key, svc_source = manager._find_routing_key_upstream(service)
        hierarchy_info.append({
            'service_name': service.name,
            'depth': depth,
            'has_own_key': bool(getattr(service, 'pagerduty_routing_key', None)),
            'effective_routing_source': svc_source,
        })

    return {
        'has_routing_key': bool(routing_key),
        'routing_key_masked': f"{routing_key[:8]}...{routing_key[-4:]}" if routing_key and len(
            routing_key) > 12 else None,
        'routing_source': source,
        'is_enabled': manager.is_enabled,
        'service_hierarchy': hierarchy_info,
    }