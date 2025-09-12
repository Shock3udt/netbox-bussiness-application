"""
Comprehensive tests for health status calculation in TechnicalService model.
Tests all health status scenarios including dependencies, maintenance, and incidents.
"""

from django.test import TestCase
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta

from business_application.models import (
    TechnicalService, ServiceDependency, Incident, Maintenance,
    ServiceType, DependencyType, ServiceHealthStatus,
    IncidentStatus, IncidentSeverity, MaintenanceStatus
)
from dcim.models import Device, DeviceType, DeviceRole, Site, Manufacturer
from virtualization.models import VirtualMachine, Cluster, ClusterType
from users.models import User


class HealthStatusCalculationTestCase(TestCase):
    """Test health status calculation for technical services"""

    def setUp(self):
        """Set up test data"""
        # Create required objects
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

        # Create test services
        self.service = TechnicalService.objects.create(
            name='Test Service',
            service_type=ServiceType.TECHNICAL
        )
        self.service.devices.add(self.device)
        self.service.vms.add(self.vm)

        self.upstream_service = TechnicalService.objects.create(
            name='Upstream Service',
            service_type=ServiceType.TECHNICAL
        )

        self.downstream_service = TechnicalService.objects.create(
            name='Downstream Service',
            service_type=ServiceType.TECHNICAL
        )

    def test_healthy_service_no_issues(self):
        """Test that a service with no issues is healthy"""
        self.assertEqual(self.service.health_status, ServiceHealthStatus.HEALTHY)

    def test_service_down_due_to_incident(self):
        """Test that a service is down when it has active incidents"""
        # Create active incident
        incident = Incident.objects.create(
            title='Test Incident',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident.affected_services.add(self.service)

        self.assertEqual(self.service.health_status, ServiceHealthStatus.DOWN)

    def test_service_healthy_after_incident_resolved(self):
        """Test that service returns to healthy after incident is resolved"""
        # Create resolved incident
        incident = Incident.objects.create(
            title='Resolved Incident',
            status=IncidentStatus.RESOLVED,
            severity=IncidentSeverity.HIGH,
            resolved_at=timezone.now()
        )
        incident.affected_services.add(self.service)

        self.assertEqual(self.service.health_status, ServiceHealthStatus.HEALTHY)

    def test_service_under_maintenance(self):
        """Test that a service under maintenance shows correct status"""
        now = timezone.now()

        # Create ongoing maintenance on the service
        Maintenance.objects.create(
            status=MaintenanceStatus.STARTED,
            description='Routine maintenance',
            planned_start=now - timedelta(hours=1),
            planned_end=now + timedelta(hours=1),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(TechnicalService),
            object_id=self.service.id
        )

        self.assertEqual(self.service.health_status, ServiceHealthStatus.UNDER_MAINTENANCE)

    def test_service_under_maintenance_on_device(self):
        """Test that service is under maintenance when its device is under maintenance"""
        now = timezone.now()

        # Create maintenance on the device
        Maintenance.objects.create(
            status=MaintenanceStatus.STARTED,
            description='Device maintenance',
            planned_start=now - timedelta(hours=1),
            planned_end=now + timedelta(hours=1),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(Device),
            object_id=self.device.id
        )

        self.assertEqual(self.service.health_status, ServiceHealthStatus.UNDER_MAINTENANCE)

    def test_service_under_maintenance_on_vm(self):
        """Test that service is under maintenance when its VM is under maintenance"""
        now = timezone.now()

        # Create maintenance on the VM
        Maintenance.objects.create(
            status=MaintenanceStatus.STARTED,
            description='VM maintenance',
            planned_start=now - timedelta(hours=1),
            planned_end=now + timedelta(hours=1),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(VirtualMachine),
            object_id=self.vm.id
        )

        self.assertEqual(self.service.health_status, ServiceHealthStatus.UNDER_MAINTENANCE)

    def test_service_down_due_to_normal_dependency(self):
        """Test that service is down when normal dependency is down"""
        # Create normal dependency
        ServiceDependency.objects.create(
            name='Normal Dependency',
            upstream_service=self.upstream_service,
            downstream_service=self.service,
            dependency_type=DependencyType.NORMAL
        )

        # Create incident on upstream service
        incident = Incident.objects.create(
            title='Upstream Incident',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident.affected_services.add(self.upstream_service)

        self.assertEqual(self.service.health_status, ServiceHealthStatus.DOWN)

    def test_service_degraded_due_to_normal_dependency_degraded(self):
        """Test that service is degraded when normal dependency is degraded"""
        # Create another upstream service
        upstream_service2 = TechnicalService.objects.create(
            name='Upstream Service 2',
            service_type=ServiceType.TECHNICAL
        )

        # Create normal dependency
        ServiceDependency.objects.create(
            name='Normal Dependency',
            upstream_service=self.upstream_service,
            downstream_service=self.service,
            dependency_type=DependencyType.NORMAL
        )

        # Create dependency on upstream_service2
        ServiceDependency.objects.create(
            name='Another Dependency',
            upstream_service=upstream_service2,
            downstream_service=self.upstream_service,
            dependency_type=DependencyType.NORMAL
        )

        # Put upstream_service2 under maintenance (which should make upstream_service degraded)
        now = timezone.now()
        Maintenance.objects.create(
            status=MaintenanceStatus.STARTED,
            description='Maintenance',
            planned_start=now - timedelta(hours=1),
            planned_end=now + timedelta(hours=1),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(TechnicalService),
            object_id=upstream_service2.id
        )

        self.assertEqual(self.service.health_status, ServiceHealthStatus.DEGRADED)

    def test_redundant_dependency_all_down(self):
        """Test redundant dependency where all services are down"""
        # Create two upstream services for redundancy
        upstream1 = TechnicalService.objects.create(
            name='Redundant Service 1',
            service_type=ServiceType.TECHNICAL
        )
        upstream2 = TechnicalService.objects.create(
            name='Redundant Service 2',
            service_type=ServiceType.TECHNICAL
        )

        # Create redundant dependencies with same name (redundancy group)
        ServiceDependency.objects.create(
            name='Database Cluster',
            upstream_service=upstream1,
            downstream_service=self.service,
            dependency_type=DependencyType.REDUNDANCY
        )
        ServiceDependency.objects.create(
            name='Database Cluster',
            upstream_service=upstream2,
            downstream_service=self.service,
            dependency_type=DependencyType.REDUNDANCY
        )

        # Create incidents on both upstream services
        incident1 = Incident.objects.create(
            title='Incident 1',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident1.affected_services.add(upstream1)

        incident2 = Incident.objects.create(
            title='Incident 2',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident2.affected_services.add(upstream2)

        # Service should be down because all redundant services are down
        self.assertEqual(self.service.health_status, ServiceHealthStatus.DOWN)

    def test_redundant_dependency_partial_failure(self):
        """Test redundant dependency where some services are down"""
        # Create two upstream services for redundancy
        upstream1 = TechnicalService.objects.create(
            name='Redundant Service 1',
            service_type=ServiceType.TECHNICAL
        )
        upstream2 = TechnicalService.objects.create(
            name='Redundant Service 2',
            service_type=ServiceType.TECHNICAL
        )

        # Create redundant dependencies
        ServiceDependency.objects.create(
            name='Load Balancer Pool',
            upstream_service=upstream1,
            downstream_service=self.service,
            dependency_type=DependencyType.REDUNDANCY
        )
        ServiceDependency.objects.create(
            name='Load Balancer Pool',
            upstream_service=upstream2,
            downstream_service=self.service,
            dependency_type=DependencyType.REDUNDANCY
        )

        # Create incident on only one upstream service
        incident = Incident.objects.create(
            title='Partial Failure',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident.affected_services.add(upstream1)

        # Service should be degraded because some redundant services are down
        self.assertEqual(self.service.health_status, ServiceHealthStatus.DEGRADED)

    def test_redundant_dependency_all_healthy(self):
        """Test redundant dependency where all services are healthy"""
        # Create two upstream services for redundancy
        upstream1 = TechnicalService.objects.create(
            name='Redundant Service 1',
            service_type=ServiceType.TECHNICAL
        )
        upstream2 = TechnicalService.objects.create(
            name='Redundant Service 2',
            service_type=ServiceType.TECHNICAL
        )

        # Create redundant dependencies
        ServiceDependency.objects.create(
            name='Redundant Group',
            upstream_service=upstream1,
            downstream_service=self.service,
            dependency_type=DependencyType.REDUNDANCY
        )
        ServiceDependency.objects.create(
            name='Redundant Group',
            upstream_service=upstream2,
            downstream_service=self.service,
            dependency_type=DependencyType.REDUNDANCY
        )

        # All services healthy, so service should be healthy
        self.assertEqual(self.service.health_status, ServiceHealthStatus.HEALTHY)

    def test_circular_dependency_protection(self):
        """Test that circular dependencies don't cause infinite loops"""
        # Create circular dependency
        ServiceDependency.objects.create(
            name='Circular A->B',
            upstream_service=self.service,
            downstream_service=self.upstream_service,
            dependency_type=DependencyType.NORMAL
        )
        ServiceDependency.objects.create(
            name='Circular B->A',
            upstream_service=self.upstream_service,
            downstream_service=self.service,
            dependency_type=DependencyType.NORMAL
        )

        # This should not cause infinite recursion
        health_status = self.service.health_status
        self.assertIn(health_status, [
            ServiceHealthStatus.HEALTHY,
            ServiceHealthStatus.DEGRADED,
            ServiceHealthStatus.DOWN,
            ServiceHealthStatus.UNDER_MAINTENANCE
        ])

    def test_complex_dependency_chain(self):
        """Test complex dependency chain with mixed types"""
        # Create a complex dependency chain:
        # service -> upstream_service (normal) -> [redundant1, redundant2] (redundancy)
        redundant1 = TechnicalService.objects.create(
            name='Redundant Service 1',
            service_type=ServiceType.TECHNICAL
        )
        redundant2 = TechnicalService.objects.create(
            name='Redundant Service 2',
            service_type=ServiceType.TECHNICAL
        )

        # Normal dependency: service depends on upstream_service
        ServiceDependency.objects.create(
            name='Normal Dep',
            upstream_service=self.upstream_service,
            downstream_service=self.service,
            dependency_type=DependencyType.NORMAL
        )

        # Redundant dependencies: upstream_service depends on redundant services
        ServiceDependency.objects.create(
            name='Database Pool',
            upstream_service=redundant1,
            downstream_service=self.upstream_service,
            dependency_type=DependencyType.REDUNDANCY
        )
        ServiceDependency.objects.create(
            name='Database Pool',
            upstream_service=redundant2,
            downstream_service=self.upstream_service,
            dependency_type=DependencyType.REDUNDANCY
        )

        # If one redundant service fails, upstream should be degraded,
        # which should make our service degraded
        incident = Incident.objects.create(
            title='Redundant Failure',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident.affected_services.add(redundant1)

        self.assertEqual(self.service.health_status, ServiceHealthStatus.DEGRADED)

        # If both redundant services fail, upstream should be down,
        # which should make our service down
        incident2 = Incident.objects.create(
            title='Complete Failure',
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH
        )
        incident2.affected_services.add(redundant2)

        self.assertEqual(self.service.health_status, ServiceHealthStatus.DOWN)

    def test_maintenance_degrades_dependent_services(self):
        """Test that service under maintenance causes dependent services to be degraded"""
        # Create dependency: downstream_service depends on self.service
        ServiceDependency.objects.create(
            name='Test Dependency',
            upstream_service=self.service,
            downstream_service=self.downstream_service,
            dependency_type=DependencyType.NORMAL
        )

        # Put self.service under maintenance
        now = timezone.now()
        Maintenance.objects.create(
            status=MaintenanceStatus.STARTED,
            description='Service maintenance',
            planned_start=now - timedelta(hours=1),
            planned_end=now + timedelta(hours=1),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(TechnicalService),
            object_id=self.service.id
        )

        # self.service should be under maintenance
        self.assertEqual(self.service.health_status, ServiceHealthStatus.UNDER_MAINTENANCE)

        # downstream_service should be degraded (not under maintenance)
        self.assertEqual(self.downstream_service.health_status, ServiceHealthStatus.DEGRADED)

    def test_finished_maintenance_doesnt_affect_status(self):
        """Test that finished maintenance doesn't affect health status"""
        now = timezone.now()

        # Create finished maintenance
        Maintenance.objects.create(
            status=MaintenanceStatus.FINISHED,
            description='Finished maintenance',
            planned_start=now - timedelta(hours=2),
            planned_end=now - timedelta(hours=1),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(TechnicalService),
            object_id=self.service.id
        )

        self.assertEqual(self.service.health_status, ServiceHealthStatus.HEALTHY)

    def test_planned_maintenance_doesnt_affect_status(self):
        """Test that planned (not started) maintenance doesn't affect health status"""
        now = timezone.now()

        # Create planned maintenance (in the future)
        Maintenance.objects.create(
            status=MaintenanceStatus.PLANNED,
            description='Future maintenance',
            planned_start=now + timedelta(hours=1),
            planned_end=now + timedelta(hours=2),
            contact='Test Contact',
            content_type=ContentType.objects.get_for_model(TechnicalService),
            object_id=self.service.id
        )

        self.assertEqual(self.service.health_status, ServiceHealthStatus.HEALTHY)

    def test_multiple_incident_statuses(self):
        """Test different incident statuses and their effect on health"""
        # Test different incident statuses that should make service down
        for incident_status in [IncidentStatus.NEW, IncidentStatus.INVESTIGATING, IncidentStatus.IDENTIFIED]:
            with self.subTest(status=incident_status):
                # Clean up previous incidents
                Incident.objects.all().delete()

                incident = Incident.objects.create(
                    title=f'Test Incident - {incident_status}',
                    status=incident_status,
                    severity=IncidentSeverity.HIGH
                )
                incident.affected_services.add(self.service)

                self.assertEqual(self.service.health_status, ServiceHealthStatus.DOWN)

        # Test incident statuses that should not make service down
        for incident_status in [IncidentStatus.MONITORING, IncidentStatus.RESOLVED, IncidentStatus.CLOSED]:
            with self.subTest(status=incident_status):
                # Clean up previous incidents
                Incident.objects.all().delete()

                incident = Incident.objects.create(
                    title=f'Test Incident - {incident_status}',
                    status=incident_status,
                    severity=IncidentSeverity.HIGH,
                    resolved_at=timezone.now() if incident_status in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED] else None
                )
                incident.affected_services.add(self.service)

                self.assertEqual(self.service.health_status, ServiceHealthStatus.HEALTHY)


class ServiceDependencyTestCase(TestCase):
    """Test service dependency methods and calculations"""

    def setUp(self):
        self.service1 = TechnicalService.objects.create(
            name='Service 1',
            service_type=ServiceType.TECHNICAL
        )
        self.service2 = TechnicalService.objects.create(
            name='Service 2',
            service_type=ServiceType.TECHNICAL
        )
        self.service3 = TechnicalService.objects.create(
            name='Service 3',
            service_type=ServiceType.TECHNICAL
        )

    def test_get_upstream_dependencies(self):
        """Test getting upstream dependencies"""
        # service2 depends on service1
        dep = ServiceDependency.objects.create(
            name='Test Dependency',
            upstream_service=self.service1,
            downstream_service=self.service2
        )

        upstream_deps = self.service2.get_upstream_dependencies()
        self.assertEqual(upstream_deps.count(), 1)
        self.assertEqual(upstream_deps.first(), dep)

    def test_get_downstream_dependencies(self):
        """Test getting downstream dependencies"""
        # service2 depends on service1
        dep = ServiceDependency.objects.create(
            name='Test Dependency',
            upstream_service=self.service1,
            downstream_service=self.service2
        )

        downstream_deps = self.service1.get_downstream_dependencies()
        self.assertEqual(downstream_deps.count(), 1)
        self.assertEqual(downstream_deps.first(), dep)

    def test_get_downstream_business_applications(self):
        """Test getting downstream business applications"""
        from business_application.models import BusinessApplication

        # Create business applications
        app1 = BusinessApplication.objects.create(
            appcode='APP001',
            name='App 1',
            owner='Owner 1'
        )
        app2 = BusinessApplication.objects.create(
            appcode='APP002',
            name='App 2',
            owner='Owner 2'
        )

        # Associate apps with services
        self.service2.business_apps.add(app1)
        self.service3.business_apps.add(app2)

        # Create dependency chain: service1 -> service2 -> service3
        ServiceDependency.objects.create(
            name='Dep 1-2',
            upstream_service=self.service1,
            downstream_service=self.service2
        )
        ServiceDependency.objects.create(
            name='Dep 2-3',
            upstream_service=self.service2,
            downstream_service=self.service3
        )

        # service1 should see both apps in its downstream impact
        downstream_apps = self.service1.get_downstream_business_applications()
        self.assertEqual(len(downstream_apps), 2)
        self.assertIn(app1, downstream_apps)
        self.assertIn(app2, downstream_apps)
