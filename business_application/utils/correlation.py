# business_application/utils/correlation.py
from django.db import models
from django.utils import timezone
from datetime import timedelta
import logging
from typing import Optional, List

from dcim.models import Device, Cable
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
        1. Adds it to an existing incident (only for HIGH/CRITICAL events)
        2. Creates a new incident (only for HIGH/CRITICAL events)
        3. Returns None if no correlation is needed
        """
        try:
            # Skip correlation for invalid events
            if not event.is_valid or not event.has_valid_target:
                self.logger.warning(
                    f"Skipping correlation for invalid event {event.id}"
                )
                return None

            if not self._should_try_to_correlate(event):
                self.logger.info(
                    f"Event {event.id} (status: {event.status}, criticality: {event.criticallity}) "
                    f"does not require incident creation"
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

    def _find_affected_devices(self, target: models.Model) -> List[Device]:
        """
        Find all devices affected by an event using dual approach:
        1. Cable-based: Follow physical cable connections
        2. Service-based: Find devices from affected technical services via existing relationships
        
        Returns combined set of affected devices.
        """
        affected_devices = set()
        
        # Approach 1: Cable-based device discovery
        cable_devices = self._find_devices_via_cables(target)
        affected_devices.update(cable_devices)
        
        # Approach 2: Service-based device discovery via existing TechnicalService.devices relationships
        service_devices = self._find_devices_via_services(target)
        affected_devices.update(service_devices)
        
        self.logger.info(
            f"Found {len(affected_devices)} affected devices for {target}: "
            f"{len(cable_devices)} via cables, {len(service_devices)} via services"
        )
        
        return list(affected_devices)

    def _find_devices_via_cables(self, target: models.Model) -> List[Device]:
        """
        Find devices connected via NetBox cable infrastructure.
        Traverses network topology to identify downstream impact.
        """
        if not isinstance(target, Device):
            return []
            
        connected_devices = set()
        visited = set()
        
        def traverse_cables(device: Device, depth: int = 0):
            if device.id in visited or depth > 5:  # Prevent infinite loops and limit depth
                return
            visited.add(device.id)
            
            try:
                # Find interfaces on this device
                interfaces = device.interfaces.all()
                
                for interface in interfaces:
                    # Check if interface has a cable connection
                    if hasattr(interface, 'cable') and interface.cable:
                        cable = interface.cable
                        
                        self.logger.warning(type(cable.a_terminations))
                        self.logger.warning(type(cable.b_terminations))
                        self.logger.warning(cable.a_terminations)
                        self.logger.warning(cable.b_terminations)
                        
                        # a_terminations and b_terminations are lists
                        # Check if this interface is on the A side by comparing object IDs
                        a_termination_ids = [t.id for t in cable.a_terminations]
                        is_a_side = interface.id in a_termination_ids
                        
                        # Get the other end of the cable
                        if is_a_side:
                            # This interface is on A side, get B side
                            # A side = upstream, B side = downstream
                            other_terminations = cable.b_terminations
                        else:
                            # This interface is on B side, so it is a downstream device or peer
                            # We're following the downstream devices only
                            other_terminations = []
                        
                        for termination in other_terminations:
                            # Get the device from the termination
                            if hasattr(termination, 'device'):
                                self.logger.warning(termination.device)
                                connected_device = termination.device
                                if isinstance(connected_device, Device) and connected_device != device:
                                    connected_devices.add(connected_device)
                                    traverse_cables(connected_device, depth + 1)
                                    self.logger.warning(connected_device)
                                    self.logger.warning("pridal js jsem to")
                            elif hasattr(termination, 'interface') and termination.interface:
                                # Handle interface terminations
                                connected_device = termination.interface.device
                                if isinstance(connected_device, Device) and connected_device != device:
                                    connected_devices.add(connected_device)
                                    traverse_cables(connected_device, depth + 1)
                                    self.logger.warning(connected_device)
                                    self.logger.warning("pridal js jsem to 2")
            except Exception as e:
                self.logger.warning(f"Error processing device {device} at depth {depth}: {e}")
        
        try:
            traverse_cables(target)
        except Exception as e:
            self.logger.warning(f"Error traversing cables for device {target}: {e}")
            
        return list(connected_devices)

    def _find_devices_via_services(self, target: models.Model) -> List[Device]:
        """
        Find devices associated with affected technical services via existing relationships.
        Leverages existing ServiceDependency graph and TechnicalService.devices relationships.
        """
        devices = set()
        
        # Get technical services affected by this target
        technical_services = self._find_technical_services(target)
        
        # Collect devices from all affected services using existing TechnicalService.devices relationship
        for service in technical_services:
            service_devices = service.devices.all()  # Use existing ManyToManyField from lines 203-205 in models.py
            devices.update(service_devices)
            
        return list(devices)

    def _find_existing_incident(
            self, services: List[TechnicalService], event: Event
    ) -> Optional[Incident]:
        """
        Find an existing incident that this event should be correlated with.
        First checks if any incident already contains an event with the same dedup_id.
        """
        # First, check if any open incident already has an event with this dedup_id
        existing_incident_with_event = Incident.objects.filter(
            events__dedup_id=event.dedup_id,
            status__in=['new', 'investigating', 'identified']
        ).first()

        if existing_incident_with_event:
            self.logger.info(
                f"Found existing incident {existing_incident_with_event.id} with event dedup_id {event.dedup_id}"
            )
            return existing_incident_with_event

        for service in services:
            incidents = Incident.objects.filter(
                affected_services=service,
                status__in=['new', 'investigating', 'identified']
            ).distinct().order_by('-created_at')

            for incident in incidents:
                if not incident.events.filter(dedup_id=event.dedup_id).exists():
                    return incident


        return None

    def _should_try_to_correlate(
            self, event: Event
    ) -> bool:
        """
        Determine if an event should be correlated with an incident.
        """

        if event.criticallity not in ['HIGH', 'CRITICAL']:
            return False

        return True

    def _should_create_incident(self, event: Event) -> bool:
        """
        Determine if an event should trigger incident creation.
        """
        if event.status != 'triggered':
            return False

        return True

    def _create_incident(
            self, event: Event, services: List[TechnicalService]
    ) -> Incident:
        """
        Create a new incident from an event.
        Now also populates affected_devices using dual discovery approach.
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

        # Find and set affected devices using dual approach
        try:
            target_object = self._resolve_target(event)
            if target_object:
                affected_devices = self._find_affected_devices(target_object)
                if affected_devices:
                    incident.affected_devices.set(affected_devices)
                    self.logger.info(
                        f"Set {len(affected_devices)} affected devices for new incident {incident.id}"
                    )
        except Exception as e:
            self.logger.error(f"Error setting affected devices for new incident: {e}")

        # Add event to incident using the many-to-many relationship
        incident.events.add(event)

        return incident

    def _add_event_to_incident(self, event: Event, incident: Incident):
        """
        Add an event to an existing incident.
        """
        # Add event to incident using the many-to-many relationship
        incident.events.add(event)

        try:
            target_object = self._resolve_target(event)
            if target_object:
                # Update affected services
                new_services = self._find_technical_services(target_object)
                if new_services:
                    current_services = set(incident.affected_services.all())
                    all_services = current_services | set(new_services)

                    if len(all_services) > len(current_services):
                        incident.affected_services.set(all_services)
                        self.logger.info(
                            f"Added {len(all_services) - len(current_services)} new services to incident {incident.id}"
                        )

                # Update affected devices using dual approach
                new_devices = self._find_affected_devices(target_object)
                if new_devices:
                    current_devices = set(incident.affected_devices.all())
                    all_devices = current_devices | set(new_devices)

                    if len(all_devices) > len(current_devices):
                        incident.affected_devices.set(all_devices)
                        self.logger.info(
                            f"Added {len(all_devices) - len(current_devices)} new devices to incident {incident.id}"
                        )
        except Exception as e:
            self.logger.error(f"Error updating services and devices for incident {incident.id}: {e}")

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
    ):
        """
        Calculate the blast radius (downstream impact) of an incident.
        Now returns both affected services and devices.
        """
        affected_services = set()
        affected_devices = set()

        root_services = list(incident.affected_services.all())
        root_devices = list(incident.affected_devices.all())

        # Traverse service dependencies
        def traverse_downstream_services(service: TechnicalService):
            dependencies = ServiceDependency.objects.filter(
                upstream_service=service
            )

            for dep in dependencies:
                downstream_service = dep.downstream_service
                if downstream_service not in affected_services:
                    affected_services.add(downstream_service)
                    # Add devices from this downstream service via existing relationships
                    service_devices = downstream_service.devices.all()
                    affected_devices.update(service_devices)
                    traverse_downstream_services(downstream_service)

        # Process root services
        for service in root_services:
            affected_services.add(service)
            # Add devices from root services via existing relationships
            service_devices = service.devices.all()
            affected_devices.update(service_devices)
            traverse_downstream_services(service)

        # Process root devices and find connected devices via cables
        for device in root_devices:
            affected_devices.add(device)
            # Find cable-connected devices
            cable_devices = self._find_devices_via_cables(device)
            affected_devices.update(cable_devices)

        return list(affected_services), list(affected_devices)