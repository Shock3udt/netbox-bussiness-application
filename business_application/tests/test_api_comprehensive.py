"""
Comprehensive API tests for the business application plugin.
Tests all API endpoints, authentication, filtering, and edge cases.
"""

import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from datetime import datetime, timedelta

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


class BaseAPITestCase(APITestCase):
    """Base test case with common setup for API tests"""

    def setUp(self):
        # Create test user and authentication
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        # Create required objects for foreign keys
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

        # Create test business applications
        self.business_app = BusinessApplication.objects.create(
            appcode='TESTAPP001',
            name='Test Application',
            description='Test business application',
            owner='Test Owner'
        )

        # Create test technical service
        self.technical_service = TechnicalService.objects.create(
            name='Test Technical Service',
            service_type=ServiceType.TECHNICAL
        )
        self.technical_service.business_apps.add(self.business_app)
        self.technical_service.devices.add(self.device)
        self.technical_service.vms.add(self.vm)

        # Create test event source
        self.event_source = EventSource.objects.create(
            name='test-source',
            description='Test event source'
        )


class BusinessApplicationAPITests(BaseAPITestCase):
    """Test BusinessApplication API endpoints"""

    def test_list_business_applications(self):
        """Test listing business applications"""
        url = '/api/plugins/business-application/business-applications/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['appcode'], 'TESTAPP001')

    def test_create_business_application(self):
        """Test creating a business application"""
        url = '/api/plugins/business-application/business-applications/'
        data = {
            'appcode': 'NEWAPP001',
            'name': 'New Test App',
            'description': 'New test application',
            'owner': 'New Owner'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['appcode'], 'NEWAPP001')

        # Verify object was created
        self.assertTrue(
            BusinessApplication.objects.filter(appcode='NEWAPP001').exists()
        )

    def test_update_business_application(self):
        """Test updating a business application"""
        url = f'/api/plugins/business-application/business-applications/{self.business_app.id}/'
        data = {
            'appcode': 'TESTAPP001',
            'name': 'Updated Test App',
            'description': 'Updated description',
            'owner': 'Updated Owner'
        }

        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Test App')

    def test_delete_business_application(self):
        """Test deleting a business application"""
        url = f'/api/plugins/business-application/business-applications/{self.business_app.id}/'
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            BusinessApplication.objects.filter(id=self.business_app.id).exists()
        )

    def test_filter_by_name(self):
        """Test filtering business applications by name"""
        # Create another app for filtering
        BusinessApplication.objects.create(
            appcode='FILTER001',
            name='Filter Test App',
            owner='Test Owner'
        )

        url = '/api/plugins/business-application/business-applications/?name=Test%20Application'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['appcode'], 'TESTAPP001')

    def test_filter_by_appcode(self):
        """Test filtering business applications by appcode"""
        url = f'/api/plugins/business-application/business-applications/?appcode={self.business_app.appcode}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['appcode'], 'TESTAPP001')


class TechnicalServiceAPITests(BaseAPITestCase):
    """Test TechnicalService API endpoints"""

    def test_list_technical_services(self):
        """Test listing technical services"""
        url = '/api/plugins/business-application/technical-services/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Technical Service')

    def test_create_technical_service(self):
        """Test creating a technical service"""
        url = '/api/plugins/business-application/technical-services/'
        data = {
            'name': 'New Technical Service',
            'service_type': ServiceType.LOGICAL
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Technical Service')
        self.assertEqual(response.data['service_type'], ServiceType.LOGICAL)

    def test_filter_by_service_type(self):
        """Test filtering technical services by service type"""
        # Create a logical service
        TechnicalService.objects.create(
            name='Logical Service',
            service_type=ServiceType.LOGICAL
        )

        url = f'/api/plugins/business-application/technical-services/?service_type={ServiceType.LOGICAL}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['service_type'], ServiceType.LOGICAL)


class ServiceDependencyAPITests(BaseAPITestCase):
    """Test ServiceDependency API endpoints"""

    def setUp(self):
        super().setUp()

        # Create upstream service
        self.upstream_service = TechnicalService.objects.create(
            name='Upstream Service',
            service_type=ServiceType.TECHNICAL
        )

        # Create service dependency
        self.service_dependency = ServiceDependency.objects.create(
            name='Test Dependency',
            upstream_service=self.upstream_service,
            downstream_service=self.technical_service,
            dependency_type=DependencyType.NORMAL
        )

    def test_list_service_dependencies(self):
        """Test listing service dependencies"""
        url = '/api/plugins/business-application/service-dependencies/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Dependency')

    def test_create_service_dependency(self):
        """Test creating a service dependency"""
        # Create another service for dependency
        new_service = TechnicalService.objects.create(
            name='New Service',
            service_type=ServiceType.TECHNICAL
        )

        url = '/api/plugins/business-application/service-dependencies/'
        data = {
            'name': 'New Dependency',
            'upstream_service': self.technical_service.id,
            'downstream_service': new_service.id,
            'dependency_type': DependencyType.REDUNDANCY
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Dependency')

    def test_filter_by_dependency_type(self):
        """Test filtering dependencies by type"""
        url = f'/api/plugins/business-application/service-dependencies/?dependency_type={DependencyType.NORMAL}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['dependency_type'], DependencyType.NORMAL)


class EventAPITests(BaseAPITestCase):
    """Test Event API endpoints"""

    def setUp(self):
        super().setUp()

        # Create test event
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

    def test_list_events(self):
        """Test listing events"""
        url = '/api/plugins/business-application/events/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['message'], 'Test event message')

    def test_filter_by_status(self):
        """Test filtering events by status"""
        url = f'/api/plugins/business-application/events/?status={EventStatus.TRIGGERED}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['status'], EventStatus.TRIGGERED)

    def test_filter_by_criticality(self):
        """Test filtering events by criticality"""
        url = f'/api/plugins/business-application/events/?criticality={EventCrit.CRITICAL}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['criticallity'], EventCrit.CRITICAL)


class IncidentAPITests(BaseAPITestCase):
    """Test Incident API endpoints"""

    def setUp(self):
        super().setUp()

        # Create test incident
        self.incident = Incident.objects.create(
            title='Test Incident',
            description='Test incident description',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH,
            reporter='Test Reporter'
        )
        self.incident.affected_services.add(self.technical_service)

    def test_list_incidents(self):
        """Test listing incidents"""
        url = '/api/plugins/business-application/incidents/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Test Incident')

    def test_create_incident(self):
        """Test creating an incident"""
        url = '/api/plugins/business-application/incidents/'
        data = {
            'title': 'New Test Incident',
            'description': 'New test incident',
            'status': IncidentStatus.NEW,
            'severity': IncidentSeverity.CRITICAL,
            'reporter': 'New Reporter'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Test Incident')
        self.assertEqual(response.data['severity'], IncidentSeverity.CRITICAL)

    def test_filter_by_severity(self):
        """Test filtering incidents by severity"""
        url = f'/api/plugins/business-application/incidents/?severity={IncidentSeverity.HIGH}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['severity'], IncidentSeverity.HIGH)


class AlertIngestionAPITests(BaseAPITestCase):
    """Test Alert Ingestion API endpoints"""

    def test_generic_alert_ingestion(self):
        """Test generic alert ingestion endpoint"""
        url = '/api/plugins/business-application/alerts/generic/'

        alert_data = {
            'source': 'test-monitoring',
            'timestamp': timezone.now().isoformat(),
            'severity': 'high',
            'status': 'triggered',
            'message': 'CPU usage exceeded threshold',
            'dedup_id': 'test-generic-alert-001',
            'target': {
                'type': 'device',
                'identifier': self.device.name
            },
            'raw_data': {
                'metric': 'cpu',
                'value': 95.2
            }
        }

        response = self.client.post(url, alert_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('event_id', response.data)
        self.assertEqual(response.data['status'], 'success')

        # Verify event was created
        self.assertTrue(
            Event.objects.filter(dedup_id='test-generic-alert-001').exists()
        )

    def test_capacitor_alert_ingestion(self):
        """Test Capacitor-specific alert ingestion"""
        url = '/api/plugins/business-application/alerts/capacitor/'

        capacitor_data = {
            'alert_id': 'CAP-TEST-001',
            'device_name': self.device.name,
            'description': 'Interface down',
            'priority': 1,
            'state': 'ALARM',
            'alert_time': timezone.now().isoformat(),
            'metric_name': 'interface_status',
            'metric_value': 0,
            'threshold': 1
        }

        response = self.client.post(url, capacitor_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('event_id', response.data)

        # Verify event was created with correct dedup_id
        self.assertTrue(
            Event.objects.filter(dedup_id='capacitor-CAP-TEST-001').exists()
        )

    def test_signalfx_alert_ingestion(self):
        """Test SignalFX alert ingestion"""
        url = '/api/plugins/business-application/alerts/signalfx/'

        signalfx_data = {
            'incidentId': 'sfx-test-001',
            'alertState': 'TRIGGERED',
            'alertMessage': 'API latency above SLO',
            'severity': 'high',
            'timestamp': int(timezone.now().timestamp() * 1000),
            'dimensions': {'host': self.device.name},
            'detectorName': 'Latency SLO',
            'detectorUrl': 'https://signalfx.example/detectors/123',
            'rule': 'p95 > 300ms'
        }

        response = self.client.post(url, signalfx_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('event_id', response.data)

        # Verify event was created
        self.assertTrue(
            Event.objects.filter(dedup_id='signalfx-sfx-test-001').exists()
        )

    def test_email_alert_ingestion(self):
        """Test email alert ingestion"""
        url = '/api/plugins/business-application/alerts/email/'

        email_data = {
            'message_id': '<test@example.com>',
            'subject': 'Server alert: memory high',
            'body': 'Memory usage is over 90%',
            'sender': 'monitor@example.com',
            'severity': 'medium',
            'target_type': 'device',
            'target_identifier': self.device.name,
            'headers': {'X-Env': 'test'},
            'attachments': []
        }

        response = self.client.post(url, email_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('event_id', response.data)

        # Verify event was created
        self.assertTrue(
            Event.objects.filter(dedup_id='email-<test@example.com>').exists()
        )

    def test_invalid_alert_data(self):
        """Test alert ingestion with invalid data"""
        url = '/api/plugins/business-application/alerts/generic/'

        invalid_data = {
            'source': 'test-source',
            # Missing required fields
        }

        response = self.client.post(url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)


class AuthenticationTests(APITestCase):
    """Test API authentication and permissions"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.token = Token.objects.create(user=self.user)

    def test_unauthenticated_request(self):
        """Test that unauthenticated requests are rejected"""
        client = APIClient()
        url = '/api/plugins/business-application/business-applications/'
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_request(self):
        """Test that authenticated requests are accepted"""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        url = '/api/plugins/business-application/business-applications/'
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_token(self):
        """Test that invalid tokens are rejected"""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token invalid-token')
        url = '/api/plugins/business-application/business-applications/'
        response = client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PagerDutyTemplateAPITests(BaseAPITestCase):
    """Test PagerDutyTemplate API endpoints"""

    def setUp(self):
        super().setUp()

        # Create test PagerDuty template
        self.pagerduty_template = PagerDutyTemplate.objects.create(
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

    def test_list_pagerduty_templates(self):
        """Test listing PagerDuty templates"""
        url = '/api/plugins/business-application/pagerduty-templates/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Service Definition')

    def test_create_pagerduty_template(self):
        """Test creating a PagerDuty template"""
        url = '/api/plugins/business-application/pagerduty-templates/'
        data = {
            'name': 'New Router Rule',
            'description': 'New router rule template',
            'template_type': PagerDutyTemplateTypeChoices.ROUTER_RULE,
            'pagerduty_config': {
                'conditions': [
                    {
                        'field': 'summary',
                        'operator': 'contains',
                        'value': 'database'
                    }
                ],
                'actions': {
                    'route': {
                        'value': 'SERVICEID'
                    }
                }
            }
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Router Rule')
        self.assertEqual(response.data['template_type'], PagerDutyTemplateTypeChoices.ROUTER_RULE)


class DeviceDownstreamAppsAPITests(BaseAPITestCase):
    """Test device downstream applications endpoints"""

    def test_device_downstream_apps_detail(self):
        """Test getting downstream apps for a specific device"""
        url = f'/api/plugins/business-application/devices/downstream-applications/{self.device.id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        # Should include the business app associated with the technical service
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['appcode'], 'TESTAPP001')

    def test_device_downstream_apps_list(self):
        """Test listing all devices with their downstream apps"""
        url = '/api/plugins/business-application/devices/downstream-applications/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn(str(self.device.id), response.data['results'])


class ClusterDownstreamAppsAPITests(BaseAPITestCase):
    """Test cluster downstream applications endpoints"""

    def test_cluster_downstream_apps_detail(self):
        """Test getting downstream apps for a specific cluster"""
        url = f'/api/plugins/business-application/clusters/downstream-applications/{self.cluster.id}/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        # Should include the business app associated with the technical service
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['appcode'], 'TESTAPP001')

    def test_cluster_downstream_apps_list(self):
        """Test listing all clusters with their downstream apps"""
        url = '/api/plugins/business-application/clusters/downstream-applications/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn(str(self.cluster.id), response.data['results'])
