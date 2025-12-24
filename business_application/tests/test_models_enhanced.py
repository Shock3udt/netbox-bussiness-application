"""
Enhanced comprehensive model tests for the business application plugin.
Tests all models, relationships, validations, and business logic.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta

from business_application.models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate,
    ServiceType, DependencyType, ServiceHealthStatus, EventStatus, EventCrit,
    MaintenanceStatus, IncidentStatus, IncidentSeverity,
    PagerDutyTemplateTypeChoices
)
from dcim.models import Device, DeviceType, DeviceRole, Site, Manufacturer
from virtualization.models import VirtualMachine, Cluster, ClusterType
from users.models import User


class BaseModelTestCase(TestCase):
    """Base test case with common setup for model tests"""

    def setUp(self):
        # Create required objects for foreign keys
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        self.manufacturer = Manufacturer.objects.create(
            name='Test Manufacturer',
            slug='test-manufacturer'
        )

        self.device_type = DeviceType.objects.create(
            model='Test Device Type',
            slug='test-device-type',
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

        self.cluster_type = ClusterType.objects.create(
            name='Test Cluster Type',
            slug='test-cluster-type'
        )

        self.device = Device.objects.create(
            name='test-device',
            device_type=self.device_type,
            device_role=self.device_role,
            site=self.site
        )

        self.cluster = Cluster.objects.create(
            name='test-cluster',
            type=self.cluster_type
        )

        self.vm = VirtualMachine.objects.create(
            name='test-vm',
            cluster=self.cluster
        )


class BusinessApplicationModelTestCase(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        # Create test data
        self.app = BusinessApplication.objects.create(
            name="Test App",
            appcode="APP001",
            description="A test business application",
            owner="Test Owner",
            delegate="Test Delegate",
            servicenow="https://example.com/servicenow"
        )
        self.app.virtual_machines.add(self.vm)
        self.app.devices.add(self.device)

    def test_business_application_creation(self):
        """Test that a BusinessApplication object is created correctly."""
        self.assertEqual(self.app.name, "Test App")
        self.assertEqual(self.app.appcode, "APP001")
        self.assertEqual(self.app.owner, "Test Owner")
        self.assertEqual(self.app.virtual_machines.count(), 1)
        self.assertEqual(self.app.devices.count(), 1)

    def test_business_application_str(self):
        """Test string representation"""
        self.assertEqual(str(self.app), "APP001")

    def test_business_application_get_absolute_url(self):
        """Test URL generation"""
        url = self.app.get_absolute_url()
        self.assertIn('businessapplication', url)
        self.assertIn(str(self.app.pk), url)

    def test_appcode_uniqueness(self):
        """Test that appcode is unique."""
        with self.assertRaises(Exception):
            BusinessApplication.objects.create(
                name="Duplicate App",
                appcode="APP001",  # Duplicate appcode
                owner="Another Owner"
            )

    def test_business_application_ordering(self):
        """Test default ordering by appcode"""
        app2 = BusinessApplication.objects.create(
            name="Another App",
            appcode="APP000",
            owner="Another Owner"
        )

        apps = list(BusinessApplication.objects.all())
        self.assertEqual(apps[0], app2)  # APP000 should come first
        self.assertEqual(apps[1], self.app)  # APP001 should come second

    def test_many_to_many_relationships(self):
        """Test ManyToMany relationships work correctly"""
        # Create additional resources
        vm2 = VirtualMachine.objects.create(
            name='test-vm-2',
            cluster=self.cluster
        )
        device2 = Device.objects.create(
            name='test-device-2',
            device_type=self.device_type,
            device_role=self.device_role,
            site=self.site
        )

        # Add to application
        self.app.virtual_machines.add(vm2)
        self.app.devices.add(device2)

        # Verify relationships
        self.assertEqual(self.app.virtual_machines.count(), 2)
        self.assertEqual(self.app.devices.count(), 2)
        self.assertIn(self.app, vm2.business_applications.all())
        self.assertIn(self.app, device2.business_applications.all())


class TechnicalServiceModelTestCase(BaseModelTestCase):
    """Test TechnicalService model"""

    def setUp(self):
        super().setUp()
        self.business_app = BusinessApplication.objects.create(
            appcode='TESTAPP001',
            name='Test Application',
            owner='Test Owner'
        )

        self.service = TechnicalService.objects.create(
            name='Test Technical Service',
            service_type=ServiceType.TECHNICAL
        )
        self.service.business_apps.add(self.business_app)
        self.service.devices.add(self.device)
        self.service.vms.add(self.vm)
        self.service.clusters.add(self.cluster)

    def test_technical_service_creation(self):
        """Test technical service creation"""
        self.assertEqual(self.service.name, 'Test Technical Service')
        self.assertEqual(self.service.service_type, ServiceType.TECHNICAL)
        self.assertEqual(self.service.business_apps.count(), 1)
        self.assertEqual(self.service.devices.count(), 1)
        self.assertEqual(self.service.vms.count(), 1)
        self.assertEqual(self.service.clusters.count(), 1)

    def test_technical_service_str(self):
        """Test string representation"""
        self.assertEqual(str(self.service), 'Test Technical Service')

    def test_service_types(self):
        """Test different service types"""
        logical_service = TechnicalService.objects.create(
            name='Logical Service',
            service_type=ServiceType.LOGICAL
        )

        self.assertEqual(logical_service.service_type, ServiceType.LOGICAL)

    def test_unique_name_constraint(self):
        """Test that service names are unique"""
        with self.assertRaises(Exception):
            TechnicalService.objects.create(
                name='Test Technical Service',  # Duplicate name
                service_type=ServiceType.LOGICAL
            )


class ServiceDependencyModelTestCase(BaseModelTestCase):
    """Test ServiceDependency model"""

    def setUp(self):
        super().setUp()
        self.upstream_service = TechnicalService.objects.create(
            name='Upstream Service',
            service_type=ServiceType.TECHNICAL
        )
        self.downstream_service = TechnicalService.objects.create(
            name='Downstream Service',
            service_type=ServiceType.TECHNICAL
        )

        self.dependency = ServiceDependency.objects.create(
            name='Test Dependency',
            upstream_service=self.upstream_service,
            downstream_service=self.downstream_service,
            dependency_type=DependencyType.NORMAL
        )

    def test_service_dependency_creation(self):
        """Test service dependency creation"""
        self.assertEqual(self.dependency.name, 'Test Dependency')
        self.assertEqual(self.dependency.upstream_service, self.upstream_service)
        self.assertEqual(self.dependency.downstream_service, self.downstream_service)
        self.assertEqual(self.dependency.dependency_type, DependencyType.NORMAL)

    def test_service_dependency_str(self):
        """Test string representation"""
        expected = f"{self.downstream_service} depends on {self.upstream_service} (Test Dependency)"
        self.assertEqual(str(self.dependency), expected)

    def test_dependency_types(self):
        """Test different dependency types"""
        redundant_dep = ServiceDependency.objects.create(
            name='Redundant Dependency',
            upstream_service=self.upstream_service,
            downstream_service=self.downstream_service,
            dependency_type=DependencyType.REDUNDANCY
        )

        self.assertEqual(redundant_dep.dependency_type, DependencyType.REDUNDANCY)

    def test_self_dependency_validation(self):
        """Test that services cannot depend on themselves"""
        dep = ServiceDependency(
            name='Self Dependency',
            upstream_service=self.upstream_service,
            downstream_service=self.upstream_service,
            dependency_type=DependencyType.NORMAL
        )

        with self.assertRaises(ValidationError):
            dep.clean()

    def test_unique_together_constraint(self):
        """Test unique constraint on upstream/downstream pair"""
        with self.assertRaises(Exception):
            ServiceDependency.objects.create(
                name='Duplicate Dependency',
                upstream_service=self.upstream_service,
                downstream_service=self.downstream_service,
                dependency_type=DependencyType.REDUNDANCY
            )


class EventModelTestCase(BaseModelTestCase):
    """Test Event model"""

    def setUp(self):
        super().setUp()
        self.event_source = EventSource.objects.create(
            name='test-source',
            description='Test event source'
        )

        self.event = Event.objects.create(
            message='Test event message',
            dedup_id='test-dedup-001',
            status=EventStatus.TRIGGERED,
            criticallity=EventCrit.CRITICAL,
            event_source=self.event_source,
            last_seen_at=timezone.now(),
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id,
            raw={'test': 'data'}
        )

    def test_event_creation(self):
        """Test event creation"""
        self.assertEqual(self.event.message, 'Test event message')
        self.assertEqual(self.event.dedup_id, 'test-dedup-001')
        self.assertEqual(self.event.status, EventStatus.TRIGGERED)
        self.assertEqual(self.event.criticallity, EventCrit.CRITICAL)
        self.assertEqual(self.event.event_source, self.event_source)
        self.assertEqual(self.event.obj, self.device)

    def test_event_str(self):
        """Test string representation"""
        self.assertEqual(str(self.event), 'Test event message...')

    def test_event_statuses(self):
        """Test different event statuses"""
        for status, label in EventStatus.CHOICES:
            event = Event.objects.create(
                message=f'Test {status} event',
                dedup_id=f'test-{status}-001',
                status=status,
                criticallity=EventCrit.INFO,
                event_source=self.event_source,
                last_seen_at=timezone.now(),
                content_type=ContentType.objects.get_for_model(Device),
                object_id=self.device.id,
                raw={}
            )
            self.assertEqual(event.status, status)

    def test_event_criticalities(self):
        """Test different event criticalities"""
        for criticality, label in EventCrit.CHOICES:
            event = Event.objects.create(
                message=f'Test {criticality} event',
                dedup_id=f'test-{criticality}-001',
                status=EventStatus.TRIGGERED,
                criticallity=criticality,
                event_source=self.event_source,
                last_seen_at=timezone.now(),
                content_type=ContentType.objects.get_for_model(Device),
                object_id=self.device.id,
                raw={}
            )
            self.assertEqual(event.criticallity, criticality)


class IncidentModelTestCase(BaseModelTestCase):
    """Test Incident model"""

    def setUp(self):
        super().setUp()
        self.technical_service = TechnicalService.objects.create(
            name='Test Service',
            service_type=ServiceType.TECHNICAL
        )

        self.incident = Incident.objects.create(
            title='Test Incident',
            description='Test incident description',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH,
            reporter='Test Reporter'
        )
        self.incident.affected_services.add(self.technical_service)
        self.incident.responders.add(self.user)

    def test_incident_creation(self):
        """Test incident creation"""
        self.assertEqual(self.incident.title, 'Test Incident')
        self.assertEqual(self.incident.status, IncidentStatus.NEW)
        self.assertEqual(self.incident.severity, IncidentSeverity.HIGH)
        self.assertEqual(self.incident.reporter, 'Test Reporter')
        self.assertEqual(self.incident.affected_services.count(), 1)
        self.assertEqual(self.incident.responders.count(), 1)

    def test_incident_str(self):
        """Test string representation"""
        self.assertEqual(str(self.incident), 'Test Incident')

    def test_incident_ordering(self):
        """Test incidents are ordered by creation date (newest first)"""
        older_incident = Incident.objects.create(
            title='Older Incident',
            status=IncidentStatus.RESOLVED,
            severity=IncidentSeverity.LOW
        )

        # Update created_at to be older
        older_incident.created_at = timezone.now() - timedelta(hours=1)
        older_incident.save()

        incidents = list(Incident.objects.all())
        self.assertEqual(incidents[0], self.incident)  # Newer first
        self.assertEqual(incidents[1], older_incident)  # Older second


class MaintenanceModelTestCase(BaseModelTestCase):
    """Test Maintenance model"""

    def setUp(self):
        super().setUp()
        now = timezone.now()

        self.maintenance = Maintenance.objects.create(
            status=MaintenanceStatus.PLANNED,
            description='Scheduled maintenance window',
            planned_start=now + timedelta(hours=1),
            planned_end=now + timedelta(hours=3),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id
        )

    def test_maintenance_creation(self):
        """Test maintenance creation"""
        self.assertEqual(self.maintenance.status, MaintenanceStatus.PLANNED)
        self.assertEqual(self.maintenance.description, 'Scheduled maintenance window')
        self.assertEqual(self.maintenance.contact, 'Test Contact')
        self.assertEqual(self.maintenance.obj, self.device)

    def test_maintenance_str(self):
        """Test string representation"""
        self.assertEqual(str(self.maintenance), 'Scheduled maintenance window...')

    def test_maintenance_statuses(self):
        """Test different maintenance statuses"""
        for status, label in MaintenanceStatus.CHOICES:
            maintenance = Maintenance.objects.create(
                status=status,
                description=f'Test {status} maintenance',
                planned_start=timezone.now(),
                planned_end=timezone.now() + timedelta(hours=1),
                contact='Test Contact',
                content_type=ContentType.objects.get_for_model(Device),
                object_id=self.device.id
            )
            self.assertEqual(maintenance.status, status)


class PagerDutyTemplateModelTestCase(BaseModelTestCase):
    """Test PagerDutyTemplate model"""

    def setUp(self):
        super().setUp()
        self.service_definition_template = PagerDutyTemplate.objects.create(
            name='Test Service Definition',
            description='Test service definition template',
            template_type=PagerDutyTemplateTypeChoices.SERVICE_DEFINITION,
            pagerduty_config={
                'name': 'Test Service',
                'description': 'Test PagerDuty service',
                'status': 'active',
                'escalation_policy': {
                    'id': 'POLICYID',
                    'type': 'escalation_policy_reference'
                }
            }
        )

        self.router_rule_template = PagerDutyTemplate.objects.create(
            name='Test Router Rule',
            description='Test router rule template',
            template_type=PagerDutyTemplateTypeChoices.ROUTER_RULE,
            pagerduty_config={
                'conditions': [{
                    'field': 'summary',
                    'operator': 'contains',
                    'value': 'database'
                }],
                'actions': {
                    'route': {
                        'value': 'SERVICEID'
                    }
                }
            }
        )

    def test_pagerduty_template_creation(self):
        """Test PagerDuty template creation"""
        self.assertEqual(self.service_definition_template.name, 'Test Service Definition')
        self.assertEqual(self.service_definition_template.template_type, PagerDutyTemplateTypeChoices.SERVICE_DEFINITION)
        self.assertIn('escalation_policy', self.service_definition_template.pagerduty_config)

        self.assertEqual(self.router_rule_template.template_type, PagerDutyTemplateTypeChoices.ROUTER_RULE)
        self.assertIn('conditions', self.router_rule_template.pagerduty_config)

    def test_pagerduty_template_str(self):
        """Test string representation"""
        self.assertEqual(str(self.service_definition_template), 'Test Service Definition')

    def test_pagerduty_config_validation(self):
        """Test PagerDuty configuration validation"""
        # Valid service definition
        is_valid, errors = self.service_definition_template.validate_pagerduty_config()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Valid router rule
        is_valid, errors = self.router_rule_template.validate_pagerduty_config()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_invalid_service_definition_validation(self):
        """Test validation of invalid service definition"""
        invalid_template = PagerDutyTemplate(
            name='Invalid Template',
            template_type=PagerDutyTemplateTypeChoices.SERVICE_DEFINITION,
            pagerduty_config={
                'name': 'Test Service',
                # Missing required fields
            }
        )

        is_valid, errors = invalid_template.validate_pagerduty_config()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_template_ordering(self):
        """Test templates are ordered by name"""
        templates = list(PagerDutyTemplate.objects.all())
        template_names = [t.name for t in templates]
        self.assertEqual(template_names, sorted(template_names))

    def test_services_using_template_property(self):
        """Test counting services using template"""
        # Initially no services using template
        self.assertEqual(self.service_definition_template.services_using_template, 0)

        # Create service using template
        service = TechnicalService.objects.create(
            name='Service with Template',
            service_type=ServiceType.TECHNICAL,
            pagerduty_service_definition=self.service_definition_template
        )

        # Should now show 1 service using template
        self.assertEqual(self.service_definition_template.services_using_template, 1)


class TechnicalServicePagerDutyIntegrationTestCase(BaseModelTestCase):
    """Test PagerDuty integration in TechnicalService"""

    def setUp(self):
        super().setUp()

        # Create PagerDuty templates
        self.service_definition = PagerDutyTemplate.objects.create(
            name='Production Service Definition',
            template_type=PagerDutyTemplateTypeChoices.SERVICE_DEFINITION,
            pagerduty_config={
                'name': 'Production Service',
                'description': 'Production service definition',
                'status': 'active',
                'escalation_policy': {'id': 'POLICY123', 'type': 'escalation_policy_reference'}
            }
        )

        self.router_rule = PagerDutyTemplate.objects.create(
            name='Production Router Rule',
            template_type=PagerDutyTemplateTypeChoices.ROUTER_RULE,
            pagerduty_config={
                'conditions': [{'field': 'summary', 'operator': 'contains', 'value': 'prod'}]
            }
        )

        # Create technical service with PagerDuty integration
        self.service = TechnicalService.objects.create(
            name='Production Web Service',
            service_type=ServiceType.TECHNICAL,
            pagerduty_service_definition=self.service_definition,
            pagerduty_router_rule=self.router_rule
        )

    def test_has_pagerduty_integration(self):
        """Test complete PagerDuty integration detection"""
        self.assertTrue(self.service.has_pagerduty_integration)

        # Test partial integration
        partial_service = TechnicalService.objects.create(
            name='Partial Service',
            service_type=ServiceType.TECHNICAL,
            pagerduty_service_definition=self.service_definition
        )
        self.assertFalse(partial_service.has_pagerduty_integration)
        self.assertTrue(partial_service.has_partial_pagerduty_integration)

    def test_pagerduty_data_retrieval(self):
        """Test retrieving PagerDuty configuration data"""
        service_data = self.service.get_pagerduty_service_data()
        self.assertIsNotNone(service_data)
        self.assertEqual(service_data['name'], 'Production Service')

        router_data = self.service.get_pagerduty_router_data()
        self.assertIsNotNone(router_data)
        self.assertIn('conditions', router_data)

    def test_pagerduty_template_name_properties(self):
        """Test PagerDuty template name properties"""
        self.assertEqual(self.service.pagerduty_service_definition_name, 'Production Service Definition')
        self.assertEqual(self.service.pagerduty_router_rule_name, 'Production Router Rule')

        # Test backward compatibility
        self.assertEqual(self.service.pagerduty_template_name, 'Production Service Definition')


class ModelChoicesTestCase(TestCase):
    """Test that all model choice sets work correctly"""

    def test_service_type_choices(self):
        """Test ServiceType choices"""
        self.assertIn(ServiceType.TECHNICAL, [choice[0] for choice in ServiceType.CHOICES])
        self.assertIn(ServiceType.LOGICAL, [choice[0] for choice in ServiceType.CHOICES])

    def test_dependency_type_choices(self):
        """Test DependencyType choices"""
        self.assertIn(DependencyType.NORMAL, [choice[0] for choice in DependencyType.CHOICES])
        self.assertIn(DependencyType.REDUNDANCY, [choice[0] for choice in DependencyType.CHOICES])

    def test_service_health_status_choices(self):
        """Test ServiceHealthStatus choices"""
        expected_statuses = [ServiceHealthStatus.DOWN, ServiceHealthStatus.DEGRADED,
                           ServiceHealthStatus.UNDER_MAINTENANCE, ServiceHealthStatus.HEALTHY]
        for status in expected_statuses:
            self.assertIn(status, [choice[0] for choice in ServiceHealthStatus.CHOICES])

    def test_event_status_choices(self):
        """Test EventStatus choices"""
        expected_statuses = [EventStatus.TRIGGERED, EventStatus.OK, EventStatus.SUPPRESSED]
        for status in expected_statuses:
            self.assertIn(status, [choice[0] for choice in EventStatus.CHOICES])

    def test_event_criticality_choices(self):
        """Test EventCrit choices"""
        expected_criticalities = [EventCrit.CRITICAL, EventCrit.WARNING, EventCrit.INFO]
        for criticality in expected_criticalities:
            self.assertIn(criticality, [choice[0] for choice in EventCrit.CHOICES])

    def test_incident_status_choices(self):
        """Test IncidentStatus choices"""
        expected_statuses = [IncidentStatus.NEW, IncidentStatus.INVESTIGATING,
                           IncidentStatus.IDENTIFIED, IncidentStatus.MONITORING,
                           IncidentStatus.RESOLVED, IncidentStatus.CLOSED]
        for status in expected_statuses:
            self.assertIn(status, [choice[0] for choice in IncidentStatus.CHOICES])

    def test_incident_severity_choices(self):
        """Test IncidentSeverity choices"""
        expected_severities = [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH,
                             IncidentSeverity.MEDIUM, IncidentSeverity.LOW]
        for severity in expected_severities:
            self.assertIn(severity, [choice[0] for choice in IncidentSeverity.CHOICES])

    def test_maintenance_status_choices(self):
        """Test MaintenanceStatus choices"""
        expected_statuses = [MaintenanceStatus.PLANNED, MaintenanceStatus.STARTED,
                           MaintenanceStatus.FINISHED, MaintenanceStatus.CANCELED]
        for status in expected_statuses:
            self.assertIn(status, [choice[0] for choice in MaintenanceStatus.CHOICES])

    def test_pagerduty_template_type_choices(self):
        """Test PagerDutyTemplateTypeChoices"""
        expected_types = [PagerDutyTemplateTypeChoices.SERVICE_DEFINITION,
                         PagerDutyTemplateTypeChoices.ROUTER_RULE]
        for template_type in expected_types:
            self.assertIn(template_type, [choice[0] for choice in PagerDutyTemplateTypeChoices.CHOICES])


class ChangeTypeModelTestCase(BaseModelTestCase):
    """Test ChangeType model"""

    def setUp(self):
        super().setUp()
        self.change_type = ChangeType.objects.create(
            name='Software Update',
            description='Software update change type'
        )

    def test_change_type_creation(self):
        """Test change type creation"""
        self.assertEqual(self.change_type.name, 'Software Update')
        self.assertEqual(self.change_type.description, 'Software update change type')

    def test_change_type_str(self):
        """Test string representation"""
        self.assertEqual(str(self.change_type), 'Software Update')

    def test_change_type_unique_name(self):
        """Test that change type names are unique"""
        with self.assertRaises(Exception):
            ChangeType.objects.create(
                name='Software Update',  # Duplicate name
                description='Another description'
            )


class ChangeModelTestCase(BaseModelTestCase):
    """Test Change model"""

    def setUp(self):
        super().setUp()
        self.change_type = ChangeType.objects.create(
            name='Hardware Update',
            description='Hardware update change type'
        )

        self.change = Change.objects.create(
            type=self.change_type,
            description='Updated server RAM',
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id
        )

    def test_change_creation(self):
        """Test change creation"""
        self.assertEqual(self.change.type, self.change_type)
        self.assertEqual(self.change.description, 'Updated server RAM')
        self.assertEqual(self.change.obj, self.device)
        self.assertIsNotNone(self.change.created_at)

    def test_change_str(self):
        """Test string representation"""
        self.assertEqual(str(self.change), 'Updated server RAM...')


class EventSourceModelTestCase(BaseModelTestCase):
    """Test EventSource model"""

    def setUp(self):
        super().setUp()
        self.event_source = EventSource.objects.create(
            name='monitoring-system',
            description='Primary monitoring system'
        )

    def test_event_source_creation(self):
        """Test event source creation"""
        self.assertEqual(self.event_source.name, 'monitoring-system')
        self.assertEqual(self.event_source.description, 'Primary monitoring system')

    def test_event_source_str(self):
        """Test string representation"""
        self.assertEqual(str(self.event_source), 'monitoring-system')

    def test_event_source_unique_name(self):
        """Test that event source names are unique"""
        with self.assertRaises(Exception):
            EventSource.objects.create(
                name='monitoring-system',  # Duplicate name
                description='Another monitoring system'
            )
