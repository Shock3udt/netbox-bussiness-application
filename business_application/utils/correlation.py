# business_application/utils/correlation.py
from django.db import models
from django.utils import timezone
from datetime import timedelta
import logging
from typing import Optional, List

from dcim.models import Device
from virtualization.models import VirtualMachine
from business_application.models import (
    Event, Incident, TechnicalService, ServiceDependency,
    BusinessApplication
)

logger = logging.getLogger('business_application.correlation')


class AlertCorrelationEngine:
    """
    Core engine for correlating alerts into incidents.
    Implements the correlation logic based on service dependencies.
    """

    # Configuration
    CORRELATION_WINDOW_MINUTES = 30  # Time window for correlating alerts
    INCIDENT_AUTO_CLOSE_HOURS = 24  # Auto-close incidents after this time

    def __init__(self):
        self.logger = logger

    def correlate_alert(self, event: Event) -> Optional[Incident]:
        """
        Main correlation method. Processes an event and either:
        1. Adds it to an existing incident (ALL events if incident exists)
        2. Creates a new incident (only for triggered, non-low/OK events)
        3. Returns None if no correlation is needed

        Updated behavior: ALL events on affected resources are assigned to
        existing incidents, but only meaningful events create new incidents.
        """
        try:
            # Skip correlation for invalid events
            if not event.is_valid or not event.has_valid_target:
                self.logger.warning(
                    f"Skipping correlation for invalid event {event.id}"
                )
                return None

            target_object = self._resolve_target(event)
            if not target_object:
                self.logger.warning(
                    f"Could not resolve target for event {event.id}"
                )
                return None

            technical_services = self._find_technical_services(target_object)
            if not technical_services:
                self.logger.info(
                    f"No technical services found for {target_object}"
                )
                return None

            existing_incident = self._find_existing_incident(
                technical_services, event
            )

            if existing_incident:
                self._add_event_to_incident(event, existing_incident)
                self.logger.info(
                    f"Added event {event.id} (status: {event.status}, "
                    f"criticality: {event.criticallity}) to existing incident {existing_incident.id}"
                )
                return existing_incident

            if self._should_create_incident(event):
                incident = self._create_incident(event, technical_services)
                self.logger.info(
                    f"Created new incident {incident.id} for event {event.id} "
                    f"(status: {event.status}, criticality: {event.criticallity})"
                )
                return incident

            self.logger.info(
                f"Event {event.id} (status: {event.status}, criticality: {event.criticallity}) "
                f"does not require incident creation and no existing incident found"
            )
            return None

        except Exception as e:
            self.logger.exception(
                f"Error correlating event {event.id}: {str(e)}"
            )
            return None

    def _resolve_target(self, event: Event) -> Optional[models.Model]:
        """
        Resolve the target object from the event.
        Returns Device, VirtualMachine, or TechnicalService instance.
        """

        if event.object_id and event.content_type:
            return event.content_type.get_object_for_this_type(
                pk=event.object_id
            )

        if not hasattr(event, 'raw') or not event.raw:
            return None

        target_info = event.raw.get('target', {})
        target_type = target_info.get('type')
        identifier = target_info.get('identifier')

        if not target_type or not identifier:
            return None

        if target_type == 'device':
            return self._resolve_device(identifier)
        elif target_type == 'vm':
            return self._resolve_vm(identifier)
        elif target_type == 'service':
            return self._resolve_service(identifier)

        return None

    def _resolve_device(self, identifier: str) -> Optional[Device]:
        """Resolve device by name or primary IP."""
        device = Device.objects.filter(name=identifier).first()
        if device:
            return device

        if '.' not in identifier:
            for suffix in ['.example.com', '.local', '.internal']:
                device = Device.objects.filter(
                    name=f"{identifier}{suffix}"
                ).first()
                if device:
                    return device

        return None

    def _resolve_vm(self, identifier: str) -> Optional[VirtualMachine]:
        """Resolve VM by name."""
        return VirtualMachine.objects.filter(name=identifier).first()

    def _resolve_service(self, identifier: str) -> Optional[TechnicalService]:
        """Resolve technical service by name."""
        return TechnicalService.objects.filter(name=identifier).first()

    def _find_technical_services(
            self, target: models.Model
    ) -> List[TechnicalService]:
        """
        Find all technical services associated with the target object.
        """
        services = []

        if isinstance(target, Device):
            services = list(target.technical_services.all())
        elif isinstance(target, VirtualMachine):
            services = list(target.technical_services.all())
        elif isinstance(target, TechnicalService):
            services = [target]

        dependent_services = self._find_dependent_services(services)
        services.extend(dependent_services)

        return list(set(services))  # Remove duplicates

    def _find_dependent_services(
            self, services: List[TechnicalService]
    ) -> List[TechnicalService]:
        """
        Find all services that depend on the given services.
        Traverses the dependency graph downstream.
        """
        dependent_services = []
        visited = set()

        def traverse_downstream(service: TechnicalService):
            if service.id in visited:
                return
            visited.add(service.id)

            dependencies = ServiceDependency.objects.filter(
                upstream_service=service
            )

            for dep in dependencies:
                downstream_service = dep.downstream_service
                dependent_services.append(downstream_service)
                traverse_downstream(downstream_service)

        for service in services:
            traverse_downstream(service)

        return dependent_services

    def _find_existing_incident(
            self, services: List[TechnicalService], event: Event
    ) -> Optional[Incident]:
        """
        Find an existing incident that this event should be correlated with.
        """
        # Time window for correlation
        time_threshold = timezone.now() - timedelta(
            minutes=self.CORRELATION_WINDOW_MINUTES
        )

        for service in services:
            incidents = Incident.objects.filter(
                affected_services=service,
                status__in=['new', 'investigating', 'identified'],
                created_at__gte=time_threshold
            ).distinct()

            for incident in incidents:
                if self._should_correlate_with_incident(event, incident):
                    return incident

        return None

    def _should_correlate_with_incident(
            self, event: Event, incident: Incident
    ) -> bool:
        """
        Determine if an event should be correlated with an incident.
        Now assigns ALL events (including OK/low priority) to existing incidents.
        """
        # Don't add duplicate events (same dedup_id)
        if incident.events.filter(dedup_id=event.dedup_id).exists():
            return False

        # Assign ALL events to existing incidents, regardless of severity/status
        # This includes OK events, low priority events, etc.
        return True


    def _should_create_incident(self, event: Event) -> bool:
        """
        Determine if an event should trigger incident creation.
        Only creates incidents for triggered events with meaningful criticality.
        """
        # Only triggered events can create incidents
        if event.status != 'triggered':
            return False

        # Don't create incidents for OK/resolved events or low priority events
        if event.criticallity in ['LOW', 'OK']:
            return False

        return True

    def _create_incident(
            self, event: Event, services: List[TechnicalService]
    ) -> Incident:
        """
        Create a new incident from an event.
        """
        title = self._generate_incident_title(event, services)

        severity_map = {
            'CRITICAL': 'critical',
            'HIGH': 'high',
            'MEDIUM': 'medium',
            'LOW': 'low'
        }

        incident = Incident.objects.create(
            title=title,
            status='new',  # Use lowercase to match IncidentStatus.NEW
            severity=severity_map.get(event.criticallity, 'medium'),  # Use lowercase to match IncidentSeverity
            reporter='system',  # Events don't have reporter field, use system as default
            description=f"Incident created from alert: {event.message}"
        )

        # Set technical services affected by this incident
        incident.affected_services.set(services)

        # Add event to incident using the many-to-many relationship
        incident.events.add(event)

        return incident

    def _add_event_to_incident(self, event: Event, incident: Incident):
        """
        Add an event to an existing incident.
        Now handles ALL event types including OK/low priority events.
        """
        # Add event to incident using the many-to-many relationship
        incident.events.add(event)
        
        # Only escalate incident severity if event is more critical (never downgrade)
        event_severity_map = {'OK': 'low', 'LOW': 'low', 'MEDIUM': 'medium', 'HIGH': 'high', 'CRITICAL': 'critical'}
        severity_order = ['low', 'medium', 'high', 'critical']
        mapped_event_severity = event_severity_map.get(event.criticallity, 'medium')

        current_incident_severity_index = severity_order.index(incident.severity)
        event_severity_index = severity_order.index(mapped_event_severity)

        # Only escalate, never downgrade incident severity
        if event_severity_index > current_incident_severity_index:
            incident.severity = mapped_event_severity
            self.logger.info(
                f"Escalated incident {incident.id} severity from {incident.severity} to {mapped_event_severity}"
            )

        # Always update incident timestamp to show activity
        incident.updated_at = timezone.now()
        incident.save()

    def _generate_incident_title(
            self, event: Event, services: List[TechnicalService]
    ) -> str:
        """
        Generate a descriptive incident title.
        """
        if services:
            service_names = ', '.join([s.name for s in services[:3]])
            if len(services) > 3:
                service_names += f" and {len(services) - 3} more"
            return f"{event.criticallity}: {service_names} - {event.message[:100]}"
        else:
            return f"{event.criticallity}: {event.message[:150]}"

    def _find_business_applications(
            self, services: List[TechnicalService]
    ) -> List[BusinessApplication]:
        """
        Find all business applications associated with the technical services.
        """
        apps = set()
        for service in services:
            service_apps = service.business_applications.all()
            apps.update(service_apps)

        return list(apps)

    def calculate_blast_radius(
            self, incident: Incident
    ) -> List[TechnicalService]:
        """
        Calculate the blast radius (downstream impact) of an incident.
        """
        affected_services = set()

        root_services = list(incident.technical_services.all())

        def traverse_downstream(service: TechnicalService):
            dependencies = ServiceDependency.objects.filter(
                upstream_service=service
            )

            for dep in dependencies:
                downstream_service = dep.downstream_service
                if downstream_service not in affected_services:
                    affected_services.add(downstream_service)
                    traverse_downstream(downstream_service)

        for service in root_services:
            affected_services.add(service)
            traverse_downstream(service)

        return list(affected_services)