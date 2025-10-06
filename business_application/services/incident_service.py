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


def _calculate_infrastructure_correlation(affected_components: List[Any],
                                          incident: Incident) -> float:
    """
    Calculate correlation based on shared infrastructure components.
    """
    event_devices = [comp for comp in affected_components if isinstance(comp, Device)]
    event_vms = [comp for comp in affected_components if isinstance(comp, VirtualMachine)]

    incident_devices = set()
    incident_vms = set()

    for service in incident.affected_services.all():
        incident_devices.update(service.devices.all())
        incident_vms.update(service.vms.all())

    device_overlap = len(set(event_devices) & incident_devices)
    vm_overlap = len(set(event_vms) & incident_vms)

    total_event_infra = len(event_devices) + len(event_vms)
    total_overlap = device_overlap + vm_overlap

    if total_event_infra > 0:
        return total_overlap / total_event_infra
    else:
        return 0.0


def _identify_root_cause_components(affected_components: List[Any]) -> List[Any]:
    """
    Identify the most likely root cause components from the affected components.
    This should return the components highest up in the dependency chain.
    """
    services = [comp for comp in affected_components if isinstance(comp, TechnicalService)]

    if not services:
        return affected_components[:1]

    root_services = []
    min_upstream_count = float('inf')

    for service in services:
        upstream_count = service.get_upstream_dependencies().count()
        if upstream_count < min_upstream_count:
            min_upstream_count = upstream_count
            root_services = [service]
        elif upstream_count == min_upstream_count:
            root_services.append(service)

    return root_services if root_services else services[:1]


def _generate_incident_title(event: Event, root_components: List[Any]) -> str:
    """
    Generate a descriptive title for the incident.
    """
    if root_components:
        component_names = [str(comp) for comp in root_components[:2]]  # Max 2 components
        component_str = ", ".join(component_names)

        if len(root_components) > 2:
            component_str += f" and {len(root_components) - 2} others"

        return f"Service disruption affecting {component_str}"
    else:
        return f"Infrastructure alert: {event.message[:50]}..."


class IncidentAutoCreationService:
    """
    Service for automatically creating and managing incidents from incoming alerts.
    Groups related alerts by identifying common parent services in the dependency map.
    """

    def __init__(self):
        self.correlation_window_minutes = 15
        self.max_dependency_depth = 3
        self.correlation_threshold = 0.4

    def process_incoming_event(self, event: Event) -> Incident | None:
        """
        Main entry point for processing incoming alerts/events.
        Either creates a new incident or adds the event to an existing one.
        """
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

    def _get_affected_components_from_event(self, event: Event) -> List[Any]:
        """
        Extract the affected components (devices, VMs, services, etc.) from an event.
        """
        components = []

        if event.obj:
            components.append(event.obj)

        if isinstance(event.obj, (Device, VirtualMachine)):
            related_services = TechnicalService.objects.filter(
                Q(devices=event.obj) if isinstance(event.obj, Device)
                else Q(vms=event.obj)
            )
            components.extend(related_services)

        elif isinstance(event.obj, Cluster):
            cluster_vms = VirtualMachine.objects.filter(cluster=event.obj)
            related_services = TechnicalService.objects.filter(vms__in=cluster_vms)
            components.extend(related_services)

        elif isinstance(event.obj, TechnicalService):
            pass

        return components

    def _find_correlating_incident(self, event: Event, affected_components: List[Any]) -> Optional[Incident]:
        """
        Find existing open incidents that should be correlated with this event.
        """
        open_incidents = Incident.objects.filter(
            status__in=[IncidentStatus.NEW, IncidentStatus.INVESTIGATING, IncidentStatus.IDENTIFIED]
        ).prefetch_related('affected_services').order_by('-created_at')

        best_incident = None
        best_correlation_score = 0

        for incident in open_incidents:
            correlation_score = self._calculate_correlation_score(
                affected_components, incident, event
            )

            if correlation_score > best_correlation_score:
                best_correlation_score = correlation_score
                best_incident = incident

        if best_correlation_score >= self.correlation_threshold:
            return best_incident

        return None

    def _calculate_correlation_score(self, affected_components: List[Any],
                                     incident: Incident, event: Event) -> float:
        """
        Calculate how strongly this event correlates with an existing incident.
        Returns a score between 0 and 1.
        """
        score = 0.0

        event_services = [comp for comp in affected_components if isinstance(comp, TechnicalService)]
        incident_services = list(incident.affected_services.all())

        if event_services and incident_services:
            common_services = set(event_services) & set(incident_services)
            if common_services:
                score += 0.8

        dependency_score = self._calculate_dependency_correlation(event_services, incident_services)
        score += dependency_score * 0.6

        infra_score = _calculate_infrastructure_correlation(affected_components, incident)
        score += infra_score * 0.4

        time_diff_minutes = (timezone.now() - incident.created_at).total_seconds() / 60

        if time_diff_minutes > self.correlation_window_minutes:
            time_factor = max(0.5, 1 - ((time_diff_minutes - self.correlation_window_minutes) / 90))
        else:
            time_factor = 1.0  # Žádný decay v rámci correlation window

        score *= time_factor

        if hasattr(event, 'criticallity') and hasattr(incident, 'severity'):
            severity_map = {
                EventCrit.CRITICAL: IncidentSeverity.CRITICAL,
                EventCrit.WARNING: IncidentSeverity.MEDIUM,
                EventCrit.INFO: IncidentSeverity.LOW
            }
            if severity_map.get(event.criticallity) == incident.severity:
                score += 0.1

        return min(score, 1.0)

    def _calculate_dependency_correlation(self, event_services: List[TechnicalService],
                                          incident_services: List[TechnicalService]) -> float:
        """
        Calculate correlation based on dependency relationships between services.
        """
        if not event_services or not incident_services:
            return 0.0

        max_correlation = 0.0

        for event_service in event_services:
            for incident_service in incident_services:
                relationship_strength = self._get_dependency_relationship_strength(
                    event_service, incident_service
                )
                max_correlation = max(max_correlation, relationship_strength)

        return max_correlation

    def _get_dependency_relationship_strength(self, service1: TechnicalService,
                                              service2: TechnicalService) -> float:
        """
        Calculate the strength of dependency relationship between two services.
        """
        if service1 == service2:
            return 1.0

        if self._is_service_dependent_on(service1, service2, max_depth=self.max_dependency_depth):
            return 0.8
        elif self._is_service_dependent_on(service2, service1, max_depth=self.max_dependency_depth):
            return 0.8

        common_deps = self._find_common_dependencies(service1, service2)
        if common_deps:
            return 0.5

        return 0.0

    def _is_service_dependent_on(self, dependent_service: TechnicalService,
                                 upstream_service: TechnicalService, max_depth: int = 3) -> bool:
        """
        Check if dependent_service depends on upstream_service (directly or indirectly).
        """
        if max_depth <= 0:
            return False

        direct_upstream = ServiceDependency.objects.filter(
            downstream_service=dependent_service,
            upstream_service=upstream_service
        ).exists()

        if direct_upstream:
            return True

        for dep in dependent_service.get_upstream_dependencies():
            if self._is_service_dependent_on(dep.upstream_service, upstream_service, max_depth - 1):
                return True

        return False

    def _find_common_dependencies(self, service1: TechnicalService,
                                  service2: TechnicalService) -> Set[TechnicalService]:
        """
        Find common upstream dependencies between two services.
        """
        service1_upstream = self._get_all_upstream_services(service1)
        service2_upstream = self._get_all_upstream_services(service2)

        return service1_upstream & service2_upstream

    def _get_all_upstream_services(self, service: TechnicalService,
                                   visited: Set[int] = None, depth: int = 0) -> Set[TechnicalService]:
        """
        Get all upstream services for a given service (recursively).
        """
        if visited is None:
            visited = set()

        if depth > self.max_dependency_depth:
            return set()

        if service.id in visited:
            return set()

        visited.add(service.id)
        upstream_services = set()

        for dep in service.get_upstream_dependencies():
            upstream_services.add(dep.upstream_service)
            upstream_services.update(
                self._get_all_upstream_services(dep.upstream_service, visited, depth + 1)
            )

        return upstream_services

    def _create_new_incident(self, event: Event, affected_components: List[Any]) -> Incident:
        """
        Create a new incident for the given event and affected components.
        """
        severity_map = {
            EventCrit.CRITICAL: IncidentSeverity.CRITICAL,
            EventCrit.WARNING: IncidentSeverity.MEDIUM,
            EventCrit.INFO: IncidentSeverity.LOW
        }
        severity = severity_map.get(event.criticallity, IncidentSeverity.MEDIUM)

        root_components = _identify_root_cause_components(affected_components)

        title = _generate_incident_title(event, root_components)

        incident = Incident.objects.create(
            title=title,
            description=f"Auto-generated incident from event: {event.message}",
            status=IncidentStatus.NEW,
            severity=severity,
            detected_at=event.created_at,
            reporter="Auto-Incident System"
        )

        incident.events.add(event)

        affected_services = [comp for comp in affected_components if isinstance(comp, TechnicalService)]
        if affected_services:
            incident.affected_services.set(affected_services)

        logger.info(f"Created new incident {incident.id}: {title}")
        return incident

    def _add_event_to_incident(self, event: Event, incident: Incident):
        """
        Add an event to an existing incident and update incident metadata.
        """
        # Add the event
        incident.events.add(event)

        severity_priority = {
            IncidentSeverity.LOW: 1,
            IncidentSeverity.MEDIUM: 2,
            IncidentSeverity.HIGH: 3,
            IncidentSeverity.CRITICAL: 4
        }

        event_severity_map = {
            EventCrit.INFO: IncidentSeverity.LOW,
            EventCrit.WARNING: IncidentSeverity.MEDIUM,
            EventCrit.CRITICAL: IncidentSeverity.CRITICAL
        }

        event_severity = event_severity_map.get(event.criticallity, IncidentSeverity.MEDIUM)

        if severity_priority.get(event_severity, 0) > severity_priority.get(incident.severity, 0):
            incident.severity = event_severity
            incident.save(update_fields=['severity'])

        affected_components = self._get_affected_components_from_event(event)
        new_services = [comp for comp in affected_components if isinstance(comp, TechnicalService)]

        if new_services:
            current_services = set(incident.affected_services.all())
            all_services = current_services | set(new_services)
            incident.affected_services.set(all_services)

        logger.info(f"Added event {event.id} to incident {incident.id}")


def process_event_for_incident(event_id: int) -> Optional[Incident]:
    """
    Utility function to manually process a specific event for incident creation.
    """
    try:
        event = Event.objects.get(id=event_id)
        service = IncidentAutoCreationService()
        return service.process_incoming_event(event)
    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
        return None


def process_unprocessed_events():
    """
    Process all unprocessed events that haven't been assigned to incidents.
    """
    # Find events that are not associated with any incident
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