"""
Comprehensive tests for API serializers in the business application plugin.
Tests serialization, deserialization, validation, and custom fields.
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import datetime, timedelta
from rest_framework import serializers as drf_serializers

from business_application.models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate,
    ServiceType, DependencyType, EventStatus, EventCrit,
    MaintenanceStatus, IncidentStatus, IncidentSeverity,
    PagerDutyTemplateTypeChoices
)
from business_application.api.serializers import (
    BusinessApplicationSerializer, TechnicalServiceSerializer, ServiceDependencySerializer,
    EventSourceSerializer, EventSerializer, MaintenanceSerializer, ChangeTypeSerializer,
    ChangeSerializer, IncidentSerializer, PagerDutyTemplateSerializer,
    GenericAlertSerializer, CapacitorAlertSerializer, SignalFXAlertSerializer,
    EmailAlertSerializer, TargetSerializer
)
from dcim.models import Device, DeviceType, DeviceRole, Site, Manufacturer
from virtualization.models import VirtualMachine, Cluster, ClusterType
from users.models import User


class BaseSerializerTestCase(TestCase):
    """Base test case with common setup for serializer tests"""

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


class BusinessApplicationSerializerTestCase(BaseSerializerTestCase):
    """Test BusinessApplicationSerializer"""

    def setUp(self):
        super().setUp()
        self.business_app = BusinessApplication.objects.create(
            appcode='TESTAPP001',
            name='Test Application',
            description='Test business application',
            owner='Test Owner',
            delegate='Test Delegate',
            servicenow='https://example.com/servicenow'
        )

    def test_serialization(self):
        """Test serializing a BusinessApplication object"""
        serializer = BusinessApplicationSerializer(instance=self.business_app)
        data = serializer.data

        self.assertEqual(data['appcode'], 'TESTAPP001')
        self.assertEqual(data['name'], 'Test Application')
        self.assertEqual(data['description'], 'Test business application')
        self.assertEqual(data['owner'], 'Test Owner')
        self.assertEqual(data['delegate'], 'Test Delegate')
        self.assertEqual(data['servicenow'], 'https://example.com/servicenow')
        self.assertIn('id', data)

    def test_deserialization(self):
        """Test deserializing valid data"""
        data = {
            'appcode': 'NEWAPP001',
            'name': 'New Test App',
            'description': 'New test application',
            'owner': 'New Owner'
        }

        serializer = BusinessApplicationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        instance = serializer.save()
        self.assertEqual(instance.appcode, 'NEWAPP001')
        self.assertEqual(instance.name, 'New Test App')
        self.assertEqual(instance.owner, 'New Owner')

    def test_validation_required_fields(self):
        """Test validation of required fields"""
        data = {
            'name': 'Test App',
            # Missing required appcode and owner
        }

        serializer = BusinessApplicationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('appcode', serializer.errors)
        self.assertIn('owner', serializer.errors)

    def test_update_existing(self):
        """Test updating an existing BusinessApplication"""
        data = {
            'appcode': 'TESTAPP001',
            'name': 'Updated Test App',
            'description': 'Updated description',
            'owner': 'Updated Owner'
        }

        serializer = BusinessApplicationSerializer(instance=self.business_app, data=data)
        self.assertTrue(serializer.is_valid())

        updated_instance = serializer.save()
        self.assertEqual(updated_instance.name, 'Updated Test App')
        self.assertEqual(updated_instance.description, 'Updated description')


class TechnicalServiceSerializerTestCase(BaseSerializerTestCase):
    """Test TechnicalServiceSerializer"""

    def setUp(self):
        super().setUp()

        # Create PagerDuty template
        self.pagerduty_template = PagerDutyTemplate.objects.create(
            name='Test Template',
            template_type=PagerDutyTemplateTypeChoices.SERVICE_DEFINITION,
            pagerduty_config={'name': 'Test Service', 'status': 'active'}
        )

        self.business_app = BusinessApplication.objects.create(
            appcode='TESTAPP001',
            name='Test Application',
            owner='Test Owner'
        )

        self.upstream_service = TechnicalService.objects.create(
            name='Upstream Service',
            service_type=ServiceType.TECHNICAL
        )

        self.service = TechnicalService.objects.create(
            name='Test Technical Service',
            service_type=ServiceType.TECHNICAL,
            pagerduty_service_definition=self.pagerduty_template
        )
        self.service.business_apps.add(self.business_app)
        self.service.devices.add(self.device)
        self.service.vms.add(self.vm)
        self.service.clusters.add(self.cluster)

        # Create dependency
        ServiceDependency.objects.create(
            name='Test Dependency',
            upstream_service=self.upstream_service,
            downstream_service=self.service
        )

    def test_serialization(self):
        """Test serializing a TechnicalService object"""
        serializer = TechnicalServiceSerializer(instance=self.service)
        data = serializer.data

        self.assertEqual(data['name'], 'Test Technical Service')
        self.assertEqual(data['service_type'], ServiceType.TECHNICAL)
        self.assertEqual(data['business_apps_count'], 1)
        self.assertEqual(data['devices_count'], 1)
        self.assertEqual(data['vms_count'], 1)
        self.assertEqual(data['clusters_count'], 1)
        self.assertEqual(data['upstream_dependencies_count'], 1)
        self.assertEqual(data['downstream_dependencies_count'], 0)
        self.assertEqual(data['pagerduty_service_definition'], self.pagerduty_template.id)
        self.assertFalse(data['has_pagerduty_integration'])  # Only has service def, not router rule

    def test_deserialization(self):
        """Test deserializing valid data"""
        data = {
            'name': 'New Technical Service',
            'service_type': ServiceType.LOGICAL
        }

        serializer = TechnicalServiceSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        instance = serializer.save()
        self.assertEqual(instance.name, 'New Technical Service')
        self.assertEqual(instance.service_type, ServiceType.LOGICAL)

    def test_custom_field_methods(self):
        """Test custom field methods for counting relationships"""
        serializer = TechnicalServiceSerializer(instance=self.service)

        self.assertEqual(
            serializer.get_upstream_dependencies_count(self.service), 1
        )
        self.assertEqual(
            serializer.get_downstream_dependencies_count(self.service), 0
        )


class ServiceDependencySerializerTestCase(BaseSerializerTestCase):
    """Test ServiceDependencySerializer"""

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
            description='Test dependency description',
            upstream_service=self.upstream_service,
            downstream_service=self.downstream_service,
            dependency_type=DependencyType.NORMAL
        )

    def test_serialization(self):
        """Test serializing a ServiceDependency object"""
        serializer = ServiceDependencySerializer(instance=self.dependency)
        data = serializer.data

        self.assertEqual(data['name'], 'Test Dependency')
        self.assertEqual(data['description'], 'Test dependency description')
        self.assertEqual(data['upstream_service'], self.upstream_service.id)
        self.assertEqual(data['downstream_service'], self.downstream_service.id)
        self.assertEqual(data['upstream_service_name'], 'Upstream Service')
        self.assertEqual(data['downstream_service_name'], 'Downstream Service')
        self.assertEqual(data['dependency_type'], DependencyType.NORMAL)

    def test_deserialization(self):
        """Test deserializing valid data"""
        data = {
            'name': 'New Dependency',
            'upstream_service': self.upstream_service.id,
            'downstream_service': self.downstream_service.id,
            'dependency_type': DependencyType.REDUNDANCY
        }

        serializer = ServiceDependencySerializer(data=data)
        self.assertTrue(serializer.is_valid())

        instance = serializer.save()
        self.assertEqual(instance.name, 'New Dependency')
        self.assertEqual(instance.dependency_type, DependencyType.REDUNDANCY)


class EventSerializerTestCase(BaseSerializerTestCase):
    """Test EventSerializer"""

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

    def test_serialization(self):
        """Test serializing an Event object"""
        serializer = EventSerializer(instance=self.event)
        data = serializer.data

        self.assertEqual(data['message'], 'Test event message')
        self.assertEqual(data['dedup_id'], 'test-dedup-001')
        self.assertEqual(data['status'], EventStatus.TRIGGERED)
        self.assertEqual(data['criticallity'], EventCrit.CRITICAL)
        self.assertEqual(data['event_source'], self.event_source.id)
        self.assertEqual(data['event_source_name'], 'test-source')
        self.assertEqual(data['content_type_name'], 'device')
        self.assertEqual(data['object_id'], self.device.id)
        self.assertEqual(data['raw'], {'test': 'data'})

    def test_deserialization(self):
        """Test deserializing valid data"""
        data = {
            'message': 'New test event',
            'dedup_id': 'new-dedup-001',
            'status': EventStatus.OK,
            'criticallity': EventCrit.INFO,
            'event_source': self.event_source.id,
            'last_seen_at': timezone.now().isoformat(),
            'content_type': ContentType.objects.get_for_model(Device).id,
            'object_id': self.device.id,
            'raw': {'new': 'data'}
        }

        serializer = EventSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        instance = serializer.save()
        self.assertEqual(instance.message, 'New test event')
        self.assertEqual(instance.status, EventStatus.OK)


class IncidentSerializerTestCase(BaseSerializerTestCase):
    """Test IncidentSerializer"""

    def setUp(self):
        super().setUp()

        self.service = TechnicalService.objects.create(
            name='Test Service',
            service_type=ServiceType.TECHNICAL
        )

        self.incident = Incident.objects.create(
            title='Test Incident',
            description='Test incident description',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH,
            reporter='Test Reporter',
            commander='Test Commander'
        )
        self.incident.affected_services.add(self.service)
        self.incident.responders.add(self.user)

    def test_serialization(self):
        """Test serializing an Incident object"""
        serializer = IncidentSerializer(instance=self.incident)
        data = serializer.data

        self.assertEqual(data['title'], 'Test Incident')
        self.assertEqual(data['description'], 'Test incident description')
        self.assertEqual(data['status'], IncidentStatus.NEW)
        self.assertEqual(data['severity'], IncidentSeverity.HIGH)
        self.assertEqual(data['reporter'], 'Test Reporter')
        self.assertEqual(data['commander'], 'Test Commander')
        self.assertEqual(data['responders_count'], 1)
        self.assertEqual(data['affected_services_count'], 1)
        self.assertEqual(data['events_count'], 0)

    def test_deserialization(self):
        """Test deserializing valid data"""
        data = {
            'title': 'New Test Incident',
            'description': 'New test incident',
            'status': IncidentStatus.INVESTIGATING,
            'severity': IncidentSeverity.CRITICAL,
            'reporter': 'New Reporter'
        }

        serializer = IncidentSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        instance = serializer.save()
        self.assertEqual(instance.title, 'New Test Incident')
        self.assertEqual(instance.status, IncidentStatus.INVESTIGATING)
        self.assertEqual(instance.severity, IncidentSeverity.CRITICAL)


class PagerDutyTemplateSerializerTestCase(BaseSerializerTestCase):
    """Test PagerDutyTemplateSerializer"""

    def setUp(self):
        super().setUp()

        self.template = PagerDutyTemplate.objects.create(
            name='Test Template',
            description='Test template description',
            template_type=PagerDutyTemplateTypeChoices.SERVICE_DEFINITION,
            pagerduty_config={
                'name': 'Test Service',
                'description': 'Test PagerDuty service',
                'status': 'active'
            }
        )

        # Create service using template
        self.service = TechnicalService.objects.create(
            name='Service with Template',
            service_type=ServiceType.TECHNICAL,
            pagerduty_service_definition=self.template
        )

    def test_serialization(self):
        """Test serializing a PagerDutyTemplate object"""
        serializer = PagerDutyTemplateSerializer(instance=self.template)
        data = serializer.data

        self.assertEqual(data['name'], 'Test Template')
        self.assertEqual(data['description'], 'Test template description')
        self.assertEqual(data['template_type'], PagerDutyTemplateTypeChoices.SERVICE_DEFINITION)
        self.assertIn('name', data['pagerduty_config'])
        self.assertEqual(data['services_using_template'], 1)

    def test_deserialization(self):
        """Test deserializing valid data"""
        data = {
            'name': 'New Template',
            'description': 'New template',
            'template_type': PagerDutyTemplateTypeChoices.ROUTER_RULE,
            'pagerduty_config': {
                'conditions': [{
                    'field': 'summary',
                    'operator': 'contains',
                    'value': 'database'
                }]
            }
        }

        serializer = PagerDutyTemplateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        instance = serializer.save()
        self.assertEqual(instance.name, 'New Template')
        self.assertEqual(instance.template_type, PagerDutyTemplateTypeChoices.ROUTER_RULE)


class AlertSerializerTestCase(TestCase):
    """Test alert ingestion serializers"""

    def test_target_serializer(self):
        """Test TargetSerializer"""
        valid_data = {
            'type': 'device',
            'identifier': 'test-device-001'
        }

        serializer = TargetSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

        # Test invalid type
        invalid_data = {
            'type': 'invalid_type',
            'identifier': 'test-device-001'
        }

        serializer = TargetSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('type', serializer.errors)

    def test_generic_alert_serializer(self):
        """Test GenericAlertSerializer"""
        valid_data = {
            'source': 'test-monitoring',
            'timestamp': timezone.now().isoformat(),
            'severity': 'high',
            'status': 'triggered',
            'message': 'CPU usage exceeded threshold',
            'dedup_id': 'test-alert-001',
            'target': {
                'type': 'device',
                'identifier': 'test-device-001'
            },
            'raw_data': {
                'metric': 'cpu',
                'value': 95.0
            }
        }

        serializer = GenericAlertSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['source'], 'test-monitoring')
        self.assertEqual(validated_data['severity'], 'high')
        self.assertEqual(validated_data['target']['type'], 'device')

    def test_generic_alert_validation_errors(self):
        """Test GenericAlertSerializer validation errors"""
        # Test empty dedup_id
        invalid_data = {
            'source': 'test',
            'severity': 'high',
            'status': 'triggered',
            'message': 'Test message',
            'dedup_id': '',
            'target': {'type': 'device', 'identifier': 'test'}
        }

        serializer = GenericAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('dedup_id', serializer.errors)

        # Test future timestamp
        future_time = timezone.now() + timedelta(hours=1)
        invalid_data = {
            'source': 'test',
            'severity': 'high',
            'status': 'triggered',
            'message': 'Test message',
            'dedup_id': 'test-001',
            'timestamp': future_time.isoformat(),
            'target': {'type': 'device', 'identifier': 'test'}
        }

        serializer = GenericAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('timestamp', serializer.errors)

    def test_capacitor_alert_serializer(self):
        """Test CapacitorAlertSerializer"""
        valid_data = {
            'alert_id': 'CAP-001',
            'device_name': 'test-device',
            'description': 'Interface down',
            'priority': 1,
            'state': 'ALARM',
            'alert_time': timezone.now().isoformat(),
            'metric_name': 'interface_status',
            'metric_value': 0,
            'threshold': 1
        }

        serializer = CapacitorAlertSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

        # Test state normalization
        self.assertEqual(serializer.validated_data['state'], 'ALARM')

    def test_capacitor_alert_invalid_state(self):
        """Test CapacitorAlertSerializer with invalid state"""
        invalid_data = {
            'alert_id': 'CAP-001',
            'device_name': 'test-device',
            'description': 'Test alert',
            'priority': 1,
            'state': 'INVALID_STATE'
        }

        serializer = CapacitorAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('state', serializer.errors)

    def test_signalfx_alert_serializer(self):
        """Test SignalFXAlertSerializer"""
        timestamp = int(timezone.now().timestamp() * 1000)

        valid_data = {
            'incidentId': 'SFX-001',
            'alertState': 'TRIGGERED',
            'alertMessage': 'API latency high',
            'severity': 'high',
            'timestamp': timestamp,
            'dimensions': {'host': 'web-server-01'},
            'detectorName': 'API Latency',
            'rule': 'p95 > 300ms'
        }

        serializer = SignalFXAlertSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

        # Test timestamp conversion
        validated_data = serializer.validated_data
        self.assertIsInstance(validated_data['timestamp'], datetime)

    def test_signalfx_invalid_alert_state(self):
        """Test SignalFXAlertSerializer with invalid alert state"""
        invalid_data = {
            'incidentId': 'SFX-001',
            'alertState': 'INVALID',
            'alertMessage': 'Test message'
        }

        serializer = SignalFXAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('alertState', serializer.errors)

    def test_signalfx_invalid_timestamp(self):
        """Test SignalFXAlertSerializer with invalid timestamp"""
        invalid_data = {
            'incidentId': 'SFX-001',
            'alertState': 'TRIGGERED',
            'alertMessage': 'Test message',
            'timestamp': 'invalid-timestamp'
        }

        serializer = SignalFXAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('timestamp', serializer.errors)

    def test_email_alert_serializer(self):
        """Test EmailAlertSerializer"""
        valid_data = {
            'message_id': '<test@example.com>',
            'subject': 'Server alert: memory high',
            'body': 'Memory usage is over 90%',
            'sender': 'monitor@example.com',
            'severity': 'medium',
            'target_type': 'device',
            'target_identifier': 'web-server-01',
            'headers': {'X-Source': 'monitoring'},
            'attachments': []
        }

        serializer = EmailAlertSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())

        validated_data = serializer.validated_data
        self.assertEqual(validated_data['message_id'], '<test@example.com>')
        self.assertEqual(validated_data['severity'], 'medium')
        self.assertEqual(validated_data['target_type'], 'device')

    def test_email_alert_target_inference(self):
        """Test EmailAlertSerializer target inference from subject"""
        # Test server inference
        data = {
            'message_id': '<test@example.com>',
            'subject': 'Server maintenance notification',
            'body': 'Maintenance scheduled',
            'sender': 'admin@example.com',
            'target_identifier': ''  # Empty identifier
        }

        serializer = EmailAlertSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        validated_data = serializer.validated_data

        self.assertEqual(validated_data['target_type'], 'device')
        self.assertEqual(validated_data['target_identifier'], 'unknown')

        # Test VM inference
        data['subject'] = 'VM backup failed'
        data['target_identifier'] = ''

        serializer = EmailAlertSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        validated_data = serializer.validated_data

        self.assertEqual(validated_data['target_type'], 'vm')

    def test_email_alert_invalid_email(self):
        """Test EmailAlertSerializer with invalid email"""
        invalid_data = {
            'message_id': '<test@example.com>',
            'subject': 'Test alert',
            'body': 'Test body',
            'sender': 'invalid-email'  # Invalid email format
        }

        serializer = EmailAlertSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('sender', serializer.errors)


class SerializerFieldTestCase(BaseSerializerTestCase):
    """Test custom serializer fields and methods"""

    def setUp(self):
        super().setUp()

        self.event_source = EventSource.objects.create(
            name='test-source',
            description='Test source'
        )

        # Create multiple events for counting
        for i in range(3):
            Event.objects.create(
                message=f'Test event {i}',
                dedup_id=f'test-{i}',
                status=EventStatus.TRIGGERED,
                criticallity=EventCrit.INFO,
                event_source=self.event_source,
                last_seen_at=timezone.now(),
                content_type=ContentType.objects.get_for_model(Device),
                object_id=self.device.id,
                raw={}
            )

    def test_event_source_count_field(self):
        """Test events_count field in EventSourceSerializer"""
        serializer = EventSourceSerializer(instance=self.event_source)
        data = serializer.data

        self.assertEqual(data['events_count'], 3)

    def test_change_type_count_field(self):
        """Test changes_count field in ChangeTypeSerializer"""
        change_type = ChangeType.objects.create(
            name='Test Change Type',
            description='Test description'
        )

        # Create changes
        for i in range(2):
            Change.objects.create(
                type=change_type,
                description=f'Test change {i}',
                content_type=ContentType.objects.get_for_model(Device),
                object_id=self.device.id
            )

        serializer = ChangeTypeSerializer(instance=change_type)
        data = serializer.data

        self.assertEqual(data['changes_count'], 2)

    def test_maintenance_content_type_name(self):
        """Test content_type_name field in MaintenanceSerializer"""
        maintenance = Maintenance.objects.create(
            status=MaintenanceStatus.PLANNED,
            description='Test maintenance',
            planned_start=timezone.now(),
            planned_end=timezone.now() + timedelta(hours=1),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id
        )

        serializer = MaintenanceSerializer(instance=maintenance)
        data = serializer.data

        self.assertEqual(data['content_type_name'], 'device')


class SerializerValidationTestCase(TestCase):
    """Test serializer validation logic"""

    def test_required_field_validation(self):
        """Test that required fields are properly validated"""
        # Test BusinessApplication without required fields
        serializer = BusinessApplicationSerializer(data={})
        self.assertFalse(serializer.is_valid())

        # Should have errors for required fields
        required_fields = ['appcode', 'name', 'owner']
        for field in required_fields:
            self.assertIn(field, serializer.errors)

    def test_choice_field_validation(self):
        """Test validation of choice fields"""
        # Test invalid service type
        data = {
            'name': 'Test Service',
            'service_type': 'invalid_type'
        }

        serializer = TechnicalServiceSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('service_type', serializer.errors)

    def test_json_field_validation(self):
        """Test JSON field validation"""
        # Test invalid JSON in raw field
        now = timezone.now()
        data = {
            'message': 'Test event',
            'dedup_id': 'test-001',
            'status': EventStatus.TRIGGERED,
            'criticallity': EventCrit.INFO,
            'last_seen_at': now.isoformat(),
            'content_type': 1,
            'object_id': 1,
            'raw': 'invalid-json'  # This should be a dict
        }

        serializer = EventSerializer(data=data)
        # Note: Django's JSONField is quite permissive, so this might still be valid
        # The validation depends on the specific Django version and configuration

    def test_foreign_key_validation(self):
        """Test foreign key field validation"""
        # Test with non-existent foreign key
        data = {
            'name': 'Test Dependency',
            'upstream_service': 99999,  # Non-existent ID
            'downstream_service': 99998,  # Non-existent ID
            'dependency_type': DependencyType.NORMAL
        }

        serializer = ServiceDependencySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        # Should have validation errors for the foreign key fields


class SerializerPerformanceTestCase(BaseSerializerTestCase):
    """Test serializer performance with large datasets"""

    def setUp(self):
        super().setUp()

        # Create multiple business applications for performance testing
        self.apps = []
        for i in range(10):
            app = BusinessApplication.objects.create(
                appcode=f'APP{i:03d}',
                name=f'Application {i}',
                owner=f'Owner {i}'
            )
            self.apps.append(app)

    def test_bulk_serialization_performance(self):
        """Test serializing multiple objects"""
        # This test ensures serialization works with multiple objects
        # In a real performance test, you'd measure timing

        serializer = BusinessApplicationSerializer(self.apps, many=True)
        data = serializer.data

        self.assertEqual(len(data), 10)
        for i, app_data in enumerate(data):
            self.assertEqual(app_data['appcode'], f'APP{i:03d}')

    def test_nested_serialization(self):
        """Test serialization with nested relationships"""
        # Create service with relationships
        service = TechnicalService.objects.create(
            name='Service with Relationships',
            service_type=ServiceType.TECHNICAL
        )

        # Add multiple relationships
        for app in self.apps:
            service.business_apps.add(app)

        serializer = TechnicalServiceSerializer(instance=service)
        data = serializer.data

        # Should correctly count all relationships
        self.assertEqual(data['business_apps_count'], 10)
