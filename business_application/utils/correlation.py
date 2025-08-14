# business_application/utils/correlation.py
from django.db import models
from django.utils import timezone
from datetime import timedelta
import logging
from typing import Optional, List, Set

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
        1. Adds it to an existing incident
        2. Creates a new incident
        3. Returns None if no correlation is needed
        """
        try:
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
                    f"Added event {event.id} to incident {existing_incident.id}"
                )
                return existing_incident

            if self._should_create_incident(event):
                incident = self._create_incident(event, technical_services)
                self.logger.info(
                    f"Created new incident {incident.id} for event {event.id}"
                )
                return incident

            self.logger.info(
                f"Event {event.id} does not require incident creation"
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
            services = list(
                TechnicalService.objects.filter(device=target)
            )
        elif isinstance(target, VirtualMachine):
            services = list(
                TechnicalService.objects.filter(virtual_machine=target)
            )
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
        Traverses the dependency graph upstream.
        """
        dependent_services = []
        visited = set()

        def traverse_upstream(service: TechnicalService):
            if service.id in visited:
                return
            visited.add(service.id)

            dependencies = ServiceDependency.objects.filter(
                downstream_service=service
            )

            for dep in dependencies:
                upstream_service = dep.upstream_service
                dependent_services.append(upstream_service)
                traverse_upstream(upstream_service)

        for service in services:
            traverse_upstream(service)

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
                models.Q(technical_services=service) |
                models.Q(business_applications__technical_services=service),
                status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS'],
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
        """
        if incident.events.filter(dedup_id=event.dedup_id).exists():
            return False

        severity_map = {
            'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4
        }

        event_severity = severity_map.get(event.criticality, 2)
        incident_severity = severity_map.get(incident.severity, 2)

        return event_severity >= incident_severity - 1

    def _should_create_incident(self, event: Event) -> bool:
        """
        Determine if an event should trigger incident creation.
        """
        if event.status != 'triggered':
            return False
        if event.criticality in ['LOW']:
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
            'CRITICAL': 'CRITICAL',
            'HIGH': 'HIGH',
            'MEDIUM': 'MEDIUM',
            'LOW': 'LOW'
        }

        incident = Incident.objects.create(
            title=title,
            status='NEW',
            severity=severity_map.get(event.criticality, 'MEDIUM'),
            reporter=event.reporter or 'system',
            description=f"Incident created from alert: {event.message}"
        )

        incident.technical_services.set(services)

        event.incident = incident
        event.save()

        business_apps = self._find_business_applications(services)
        incident.business_applications.set(business_apps)

        return incident

    def _add_event_to_incident(self, event: Event, incident: Incident):
        """
        Add an event to an existing incident.
        """
        event.incident = incident
        event.save()

        severity_order = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        if severity_order.index(event.criticality) > severity_order.index(incident.severity):
            incident.severity = event.criticality
            incident.save()

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
            return f"{event.criticality}: {service_names} - {event.message[:100]}"
        else:
            return f"{event.criticality}: {event.message[:150]}"

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