from django.utils import timezone
from django.db.models import Q, Prefetch
from datetime import timedelta
from typing import Set, List, Optional, Any, Dict
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
    return 0.0


def _identify_root_cause_components(affected_components: List[Any]) -> List[Any]:
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
    if root_components:
        component_names = [str(comp) for comp in root_components[:2]]
        component_str = ", ".join(component_names)

        if len(root_components) > 2:
            component_str += f" and {len(root_components) - 2} others"

        return f"Service disruption affecting {component_str}"
    return f"Infrastructure alert: {event.message[:50]}..."


class IncidentAutoCreationService:

    def __init__(self,
                 correlation_window_minutes: int = 15,
                 max_dependency_depth: int = 3,
                 correlation_threshold: float = 0.4,
                 service_overlap_weight: float = 0.8,
                 dependency_weight: float = 0.6,
                 infrastructure_weight: float = 0.4):
        self.correlation_window_minutes = correlation_window_minutes
        self.max_dependency_depth = max_dependency_depth
        self.correlation_threshold = correlation_threshold
        self.service_overlap_weight = service_overlap_weight
        self.dependency_weight = dependency_weight
        self.infrastructure_weight = infrastructure_weight
        self._cache = {}

    def process_incoming_event(self, event: Event) -> Optional[Incident]:
        if not event:
            logger.warning("Received null event")
            return None

        logger.info(f"Processing incoming event: {event.id} - {event.message}")

        if event.status not in [EventStatus.TRIGGERED]:
            logger.debug(f"Skipping event {event.id} - status is {event.status}")
            return None

        try:
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
        except Exception as e:
            logger.error(f"Error processing event {event.id}: {e}", exc_info=True)
            raise

    def _get_affected_components_from_event(self, event: Event) -> List[Any]:
        components = []

        if not event.obj:
            return components

        components.append(event.obj)

        if isinstance(event.obj, Device):
            related_services = TechnicalService.objects.filter(devices=event.obj).select_related()
            components.extend(related_services)
        elif isinstance(event.obj, VirtualMachine):
            related_services = TechnicalService.objects.filter(vms=event.obj).select_related()
            components.extend(related_services)
        elif isinstance(event.obj, Cluster):
            cluster_vms = VirtualMachine.objects.filter(cluster=event.obj)
            related_services = TechnicalService.objects.filter(vms__in=cluster_vms).distinct()
            components.extend(related_services)

        return components

    def _find_correlating_incident(self, event: Event, affected_components: List[Any]) -> Optional[Incident]:
        open_incidents = Incident.objects.filter(
            status__in=[IncidentStatus.NEW, IncidentStatus.INVESTIGATING, IncidentStatus.IDENTIFIED]
        ).prefetch_related(
            Prefetch('affected_services', queryset=TechnicalService.objects.select_related())
        ).order_by('-created_at')[:50]

        best_incident = None
        best_correlation_score = 0.0
        correlation_details = []

        for incident in open_incidents:
            correlation_score = self._calculate_correlation_score(
                affected_components, incident, event
            )

            correlation_details.append({
                'incident_id': incident.id,
                'score': correlation_score
            })

            if correlation_score > best_correlation_score:
                best_correlation_score = correlation_score
                best_incident = incident

        logger.debug(f"Correlation scores for event {event.id}: {correlation_details}")

        if best_correlation_score >= self.correlation_threshold:
            logger.info(f"Found correlating incident {best_incident.id} with score {best_correlation_score}")
            return best_incident

        return None

    def _calculate_correlation_score(self, affected_components: List[Any],
                                     incident: Incident, event: Event) -> float:
        score = 0.0

        event_services = [comp for comp in affected_components if isinstance(comp, TechnicalService)]
        incident_services = list(incident.affected_services.all())

        if event_services and incident_services:
            common_services = set(event_services) & set(incident_services)
            if common_services:
                score += self.service_overlap_weight

        dependency_score = self._calculate_dependency_correlation(event_services, incident_services)
        score += dependency_score * self.dependency_weight

        infra_score = _calculate_infrastructure_correlation(affected_components, incident)
        score += infra_score * self.infrastructure_weight

        time_diff_minutes = (timezone.now() - incident.created_at).total_seconds() / 60

        if time_diff_minutes > self.correlation_window_minutes:
            time_factor = max(0.5, 1 - ((time_diff_minutes - self.correlation_window_minutes) / 90))
        else:
            time_factor = 1.0

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
        if service1.id == service2.id:
            return 1.0

        cache_key = (min(service1.id, service2.id), max(service1.id, service2.id))
        if cache_key in self._cache:
            return self._cache[cache_key]

        strength = 0.0

        if self._is_service_dependent_on(service1, service2, max_depth=self.max_dependency_depth):
            strength = 0.8
        elif self._is_service_dependent_on(service2, service1, max_depth=self.max_dependency_depth):
            strength = 0.8
        else:
            common_deps = self._find_common_dependencies(service1, service2)
            if common_deps:
                strength = 0.5

        self._cache[cache_key] = strength
        return strength

    def _is_service_dependent_on(self, dependent_service: TechnicalService,
                                 upstream_service: TechnicalService,
                                 max_depth: int = 3,
                                 visited: Set[int] = None) -> bool:
        if max_depth <= 0:
            return False

        if visited is None:
            visited = set()

        if dependent_service.id in visited:
            return False

        visited.add(dependent_service.id)

        direct_upstream = ServiceDependency.objects.filter(
            downstream_service=dependent_service,
            upstream_service=upstream_service
        ).exists()

        if direct_upstream:
            return True

        for dep in dependent_service.get_upstream_dependencies():
            if self._is_service_dependent_on(dep.downstream_service, upstream_service, max_depth - 1, visited):
                return True

        return False

    def _find_common_dependencies(self, service1: TechnicalService,
                                  service2: TechnicalService) -> Set[TechnicalService]:
        service1_upstream = self._get_all_upstream_services(service1)
        service2_upstream = self._get_all_upstream_services(service2)
        return service1_upstream & service2_upstream

    def _get_all_upstream_services(self, service: TechnicalService,
                                   visited: Set[int] = None,
                                   depth: int = 0) -> Set[TechnicalService]:
        if visited is None:
            visited = set()

        if depth > self.max_dependency_depth:
            return set()

        if service.id in visited:
            return set()

        visited.add(service.id)
        upstream_services = set()

        try:
            for dep in service.get_upstream_dependencies():
                upstream_services.add(dep.downstream_service)
                upstream_services.update(
                    self._get_all_upstream_services(dep.downstream_service, visited, depth + 1)
                )
        except Exception as e:
            logger.error(f"Error getting upstream services for {service.id}: {e}")

        return upstream_services

    def _create_new_incident(self, event: Event, affected_components: List[Any]) -> Incident:
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

        logger.info(f"Created new incident {incident.id}: {title} with {len(affected_services)} services")
        return incident

    def _add_event_to_incident(self, event: Event, incident: Incident):
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
            old_severity = incident.severity
            incident.severity = event_severity
            incident.save(update_fields=['severity'])
            logger.info(f"Updated incident {incident.id} severity from {old_severity} to {event_severity}")

        affected_components = self._get_affected_components_from_event(event)
        new_services = [comp for comp in affected_components if isinstance(comp, TechnicalService)]

        if new_services:
            current_services = set(incident.affected_services.all())
            all_services = current_services | set(new_services)
            if len(all_services) > len(current_services):
                incident.affected_services.set(all_services)
                logger.info(f"Added {len(all_services) - len(current_services)} new services to incident {incident.id}")

        logger.info(f"Added event {event.id} to incident {incident.id}")

    def clear_cache(self):
        self._cache.clear()
        logger.debug("Cleared dependency relationship cache")


def process_event_for_incident(event_id: int) -> Optional[Incident]:
    try:
        event = Event.objects.select_related('obj').get(id=event_id)
        service = IncidentAutoCreationService()
        return service.process_incoming_event(event)
    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
        return None
    except Exception as e:
        logger.error(f"Unexpected error processing event {event_id}: {e}", exc_info=True)
        return None


def process_unprocessed_events(batch_size: int = 100) -> Dict[str, int]:
    unprocessed_events = Event.objects.filter(
        incidents__isnull=True,
        status=EventStatus.TRIGGERED,
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).select_related('obj').order_by('created_at')[:batch_size]

    service = IncidentAutoCreationService()
    processed_count = 0
    error_count = 0
    correlated_count = 0
    new_incident_count = 0

    for event in unprocessed_events:
        try:
            incident = service.process_incoming_event(event)
            if incident:
                processed_count += 1
                if incident.events.count() > 1:
                    correlated_count += 1
                else:
                    new_incident_count += 1
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing event {event.id}: {e}")

    service.clear_cache()

    stats = {
        'processed': processed_count,
        'errors': error_count,
        'correlated': correlated_count,
        'new_incidents': new_incident_count
    }

    logger.info(f"Batch processing complete: {stats}")
    return stats