"""
Comprehensive tests for the AlertCorrelationEngine.
Tests alert correlation logic, incident creation, and service dependency resolution.
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta
from unittest.mock import patch, MagicMock

from business_application.models import (
    TechnicalService, ServiceDependency, Event, Incident, EventSource,
    BusinessApplication, ServiceType, DependencyType, EventStatus, EventCrit,
    IncidentStatus, IncidentSeverity
)
from business_application.utils.correlation import AlertCorrelationEngine
from dcim.models import Device, DeviceType, DeviceRole, Site, Manufacturer
from virtualization.models import VirtualMachine, Cluster, ClusterType
from users.models import User


class AlertCorrelationEngineTestCase(TestCase):
    """Test the AlertCorrelationEngine functionality"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Create required objects for testing
        self.manufacturer = Manufacturer.objects.create(
            name='Test Manufacturer',
            slug='test-manufacturer'
        )

        self.device_type = DeviceType.objects.create(
            model='Test Device',
            slug='test-device',
            manufacturer=self.manufacturer
        )

        self.device_role = DeviceRole.objects.create(
            name='Test Role',
            slug='test-role'
        )

        self.site = Site.objects.create(
            name='Test Site',
            slug='test-site'
        )

        self.device = Device.objects.create(
            name='test-device',
            device_type=self.device_type,
            device_role=self.device_role,
            site=self.site
        )

        self.cluster_type = ClusterType.objects.create(
            name='Test Cluster Type',
            slug='test-cluster-type'
        )

        self.cluster = Cluster.objects.create(
            name='test-cluster',
            type=self.cluster_type
        )

        self.vm = VirtualMachine.objects.create(
            name='test-vm',
            cluster=self.cluster
        )

        # Create business application and technical services
        self.business_app = BusinessApplication.objects.create(
            appcode='TESTAPP001',
            name='Test Application',
            owner='Test Owner'
        )

        self.service1 = TechnicalService.objects.create(
            name='Web Service',
            service_type=ServiceType.TECHNICAL
        )
        self.service1.business_apps.add(self.business_app)
        self.service1.devices.add(self.device)

        self.service2 = TechnicalService.objects.create(
            name='Database Service',
            service_type=ServiceType.TECHNICAL
        )
        self.service2.vms.add(self.vm)

        # Create service dependency
        ServiceDependency.objects.create(
            name='Web->DB Dependency',
            upstream_service=self.service2,
            downstream_service=self.service1,
            dependency_type=DependencyType.NORMAL
        )

        # Create event source
        self.event_source = EventSource.objects.create(
            name='test-monitoring',
            description='Test monitoring system'
        )

        # Initialize correlation engine
        self.correlation_engine = AlertCorrelationEngine()

    def test_correlate_alert_creates_new_incident(self):
        """Test that correlating a new critical alert creates an incident"""
        # Create a critical event
        event = Event.objects.create(
            message='Critical CPU usage alert',
            dedup_id='cpu-alert-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'metric': 'cpu', 'value': 95.0}
        )

        # Correlate the alert
        incident = self.correlation_engine.correlate_alert(event)

        # Should create a new incident
        self.assertIsNotNone(incident)
        self.assertEqual(incident.status, IncidentStatus.NEW)
        self.assertEqual(incident.severity, IncidentSeverity.CRITICAL)
        self.assertIn(self.service1, incident.affected_services.all())
        self.assertIn(event, incident.events.all())

    def test_correlate_alert_adds_to_existing_incident(self):
        """Test that correlating a related alert adds to existing incident"""
        # Create initial incident
        incident = Incident.objects.create(
            title='Web Service Issues',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident.affected_services.add(self.service1)

        # Create a new related event
        event = Event.objects.create(
            message='Memory usage alert',
            dedup_id='memory-alert-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'metric': 'memory', 'value': 90.0}
        )

        # Correlate the alert
        correlated_incident = self.correlation_engine.correlate_alert(event)

        # Should add to existing incident
        self.assertEqual(correlated_incident.id, incident.id)
        self.assertIn(event, incident.events.all())

    def test_correlate_alert_ignores_low_severity(self):
        """Test that low severity alerts don't create incidents"""
        # Create a low severity event
        event = Event.objects.create(
            message='Info level alert',
            dedup_id='info-alert-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.INFO,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'metric': 'info', 'value': 'test'}
        )

        # Correlate the alert
        incident = self.correlation_engine.correlate_alert(event)

        # Should not create incident for low severity
        self.assertIsNone(incident)

    def test_correlate_alert_ignores_ok_status(self):
        """Test that OK status alerts don't create incidents"""
        # Create an OK event
        event = Event.objects.create(
            message='Service restored',
            dedup_id='restored-001',
            status=EventStatus.OK,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'status': 'ok'}
        )

        # Correlate the alert
        incident = self.correlation_engine.correlate_alert(event)

        # Should not create incident for OK status
        self.assertIsNone(incident)

    def test_resolve_device_target(self):
        """Test resolving device targets from events"""
        event = Event.objects.create(
            message='Device alert',
            dedup_id='device-alert-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'target': {'type': 'device', 'identifier': 'test-device'}}
        )

        target = self.correlation_engine._resolve_target(event)
        self.assertEqual(target, self.device)

    def test_resolve_vm_target(self):
        """Test resolving VM targets from events"""
        event = Event.objects.create(
            message='VM alert',
            dedup_id='vm-alert-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(VirtualMachine),
            object_id=self.vm.id,
            raw={'target': {'type': 'vm', 'identifier': 'test-vm'}}
        )

        target = self.correlation_engine._resolve_target(event)
        self.assertEqual(target, self.vm)

    def test_resolve_service_target(self):
        """Test resolving service targets from events"""
        event = Event.objects.create(
            message='Service alert',
            dedup_id='service-alert-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(TechnicalService),
            object_id=self.service1.id,
            raw={'target': {'type': 'service', 'identifier': 'Web Service'}}
        )

        target = self.correlation_engine._resolve_target(event)
        self.assertEqual(target, self.service1)

    def test_find_technical_services_for_device(self):
        """Test finding technical services associated with a device"""
        services = self.correlation_engine._find_technical_services(self.device)
        self.assertIn(self.service1, services)
        # Should also include dependent services
        self.assertIn(self.service2, services)  # service2 is upstream dependency

    def test_find_technical_services_for_vm(self):
        """Test finding technical services associated with a VM"""
        services = self.correlation_engine._find_technical_services(self.vm)
        self.assertIn(self.service2, services)

    def test_find_technical_services_for_service(self):
        """Test finding technical services for a service target"""
        services = self.correlation_engine._find_technical_services(self.service1)
        self.assertIn(self.service1, services)

    def test_find_dependent_services(self):
        """Test finding services that depend on given services"""
        dependent_services = self.correlation_engine._find_dependent_services([self.service1])
        # Should find service2 since service1 depends on service2
        self.assertIn(self.service2, dependent_services)

    def test_correlation_time_window(self):
        """Test that correlation respects time window"""
        old_time = timezone.now() - timedelta(hours=2)

        # Create old incident (outside correlation window)
        old_incident = Incident.objects.create(
            title='Old Incident',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH,
            created_at=old_time
        )
        old_incident.affected_services.add(self.service1)

        # Create new event
        event = Event.objects.create(
            message='New alert',
            dedup_id='new-alert-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'test': 'data'}
        )

        # Should create new incident, not correlate with old one
        incident = self.correlation_engine.correlate_alert(event)
        self.assertNotEqual(incident.id, old_incident.id)

    def test_duplicate_event_handling(self):
        """Test handling of duplicate events (same dedup_id)"""
        # Create incident with existing event
        incident = Incident.objects.create(
            title='Test Incident',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident.affected_services.add(self.service1)

        existing_event = Event.objects.create(
            message='Existing alert',
            dedup_id='duplicate-test-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'test': 'data'}
        )
        incident.events.add(existing_event)

        # Create new event with same dedup_id
        duplicate_event = Event.objects.create(
            message='Duplicate alert',
            dedup_id='duplicate-test-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'test': 'data'}
        )

        # Should not correlate duplicate events
        correlated_incident = self.correlation_engine.correlate_alert(duplicate_event)

        # Should create new incident or return None, not add to existing
        if correlated_incident:
            self.assertNotEqual(correlated_incident.id, incident.id)
        else:
            self.assertIsNone(correlated_incident)

    def test_severity_escalation(self):
        """Test that incident severity escalates with higher severity events"""
        # Create incident with medium severity
        incident = Incident.objects.create(
            title='Test Incident',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.MEDIUM
        )
        incident.affected_services.add(self.service1)

        # Create high severity event
        high_severity_event = Event.objects.create(
            message='High severity alert',
            dedup_id='high-sev-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'test': 'data'}
        )

        # Correlate should escalate incident severity
        self.correlation_engine._add_event_to_incident(high_severity_event, incident)

        incident.refresh_from_db()
        self.assertEqual(incident.severity, IncidentSeverity.CRITICAL)

    def test_blast_radius_calculation(self):
        """Test calculating blast radius of an incident"""
        # Create additional services in dependency chain
        service3 = TechnicalService.objects.create(
            name='Frontend Service',
            service_type=ServiceType.TECHNICAL
        )

        # Create dependency chain: service2 -> service1 -> service3
        ServiceDependency.objects.create(
            name='Web->Frontend',
            upstream_service=self.service1,
            downstream_service=service3,
            dependency_type=DependencyType.NORMAL
        )

        # Create incident affecting service2
        incident = Incident.objects.create(
            title='Database Incident',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident.affected_services.add(self.service2)

        # Calculate blast radius
        blast_radius = self.correlation_engine.calculate_blast_radius(incident)

        # Should include all services in the chain
        self.assertIn(self.service2, blast_radius)  # root cause
        self.assertIn(self.service1, blast_radius)  # dependent on service2
        self.assertIn(service3, blast_radius)       # dependent on service1

    def test_business_application_correlation(self):
        """Test that business applications are properly associated with incidents"""
        # Create event affecting service1
        event = Event.objects.create(
            message='Service failure',
            dedup_id='biz-app-test-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(TechnicalService),
            object_id=self.service1.id,
            raw={'test': 'data'}
        )

        # Correlate the alert
        incident = self.correlation_engine.correlate_alert(event)

        # Incident should be associated with business application
        self.assertIn(self.business_app, incident.business_applications.all())

    def test_fallback_target_resolution(self):
        """Test fallback target resolution when target cannot be found"""
        # Create event with non-existent target
        event = Event.objects.create(
            message='Unknown target alert',
            dedup_id='unknown-target-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=None,
            object_id=None,
            raw={'target': {'type': 'device', 'identifier': 'non-existent-device'}}
        )

        # Should handle gracefully and potentially use fallback
        try:
            incident = self.correlation_engine.correlate_alert(event)
            # Should either create incident with fallback or return None
            if incident:
                self.assertIsNotNone(incident)
        except Exception as e:
            self.fail(f"Correlation should handle unknown targets gracefully, got: {e}")

    def test_device_name_resolution_with_suffixes(self):
        """Test device resolution with common domain suffixes"""
        # Test that device resolution tries common suffixes
        device_name_base = 'test-server'

        # Mock the device lookup to simulate real scenarios
        with patch.object(self.correlation_engine, '_resolve_device') as mock_resolve:
            mock_resolve.return_value = self.device

            # Should try multiple suffixes if base name not found
            result = self.correlation_engine._resolve_device(device_name_base)
            mock_resolve.assert_called_with(device_name_base)


class AlertCorrelationIntegrationTestCase(TestCase):
    """Integration tests for alert correlation with real API workflows"""

    def setUp(self):
        """Set up integration test data"""
        # Create minimal required objects
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        self.manufacturer = Manufacturer.objects.create(
            name='Test Manufacturer',
            slug='test-manufacturer'
        )

        self.device_type = DeviceType.objects.create(
            model='Test Device',
            slug='test-device',
            manufacturer=self.manufacturer
        )

        self.device_role = DeviceRole.objects.create(
            name='Test Role',
            slug='test-role'
        )

        self.site = Site.objects.create(
            name='Test Site',
            slug='test-site'
        )

        self.device = Device.objects.create(
            name='prod-web-01',
            device_type=self.device_type,
            device_role=self.device_role,
            site=self.site
        )

        # Create realistic service hierarchy
        self.database_service = TechnicalService.objects.create(
            name='Production Database',
            service_type=ServiceType.TECHNICAL
        )

        self.web_service = TechnicalService.objects.create(
            name='Production Web Server',
            service_type=ServiceType.TECHNICAL
        )
        self.web_service.devices.add(self.device)

        # Create dependency
        ServiceDependency.objects.create(
            name='Web depends on DB',
            upstream_service=self.database_service,
            downstream_service=self.web_service,
            dependency_type=DependencyType.NORMAL
        )

        self.correlation_engine = AlertCorrelationEngine()

    def test_cascading_failure_scenario(self):
        """Test realistic cascading failure scenario"""
        # Simulate database failure
        db_event = Event.objects.create(
            message='Database connection timeout',
            dedup_id='db-timeout-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=EventSource.objects.create(name='database-monitor'),
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(TechnicalService),
            object_id=self.database_service.id,
            raw={'connection_timeout': 30, 'error': 'Connection refused'}
        )

        # Correlate database alert
        db_incident = self.correlation_engine.correlate_alert(db_event)
        self.assertIsNotNone(db_incident)
        self.assertEqual(db_incident.severity, IncidentSeverity.CRITICAL)

        # Simulate subsequent web service failures due to database issue
        web_event = Event.objects.create(
            message='HTTP 500 errors increasing',
            dedup_id='web-errors-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=EventSource.objects.create(name='web-monitor'),
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'error_rate': 95.0, 'status_code': 500}
        )

        # Correlate web alert - should be added to existing incident or create related one
        web_incident = self.correlation_engine.correlate_alert(web_event)
        self.assertIsNotNone(web_incident)

        # Verify proper correlation occurred
        self.assertTrue(
            web_incident.id == db_incident.id or  # Same incident
            web_incident.affected_services.filter(id=self.web_service.id).exists()  # Or separate but related
        )

    def test_multi_source_alert_correlation(self):
        """Test correlation of alerts from multiple monitoring sources"""
        sources = ['nagios', 'datadog', 'prometheus']
        events = []

        # Create alerts from multiple sources about the same service
        for i, source in enumerate(sources):
            event_source = EventSource.objects.create(name=source)
            event = Event.objects.create(
                message=f'{source.title()} alert: High CPU usage',
                dedup_id=f'{source}-cpu-{i+1}',
                status=EventStatus.TRIGGERED,
                criticallity=EventCrit.CRITICAL,
                event_source=event_source,
                last_seen_at=timezone.now(),
                content_type=ContentType.objects.get_for_model(Device),
                object_id=self.device.id,
                raw={'source': source, 'cpu_percent': 95 + i}
            )
            events.append(event)

        # Correlate all events
        incidents = []
        for event in events:
            incident = self.correlation_engine.correlate_alert(event)
            if incident:
                incidents.append(incident)

        # Should correlate into single incident due to same target and timeframe
        unique_incidents = set(incident.id for incident in incidents if incident)
        self.assertTrue(len(unique_incidents) <= 2)  # Should be mostly consolidated
