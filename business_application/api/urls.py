# api/urls.py - Updated with incident automation endpoints

from django.urls import path
from rest_framework.routers import DefaultRouter
from business_application.api.views import (
    BusinessApplicationViewSet, TechnicalServiceViewSet, ServiceDependencyViewSet,
    EventSourceViewSet, EventViewSet, MaintenanceViewSet, ChangeTypeViewSet, ChangeViewSet,
    IncidentViewSet, DeviceDownstreamAppsViewSet, ClusterDownstreamAppsViewSet, AlertIngestionViewSet,
    PagerDutyTemplateViewSet, ExternalWorkflowViewSet, WorkflowExecutionViewSet,
    DeviceBusinessApplicationRelationshipViewSet,
    VirtualMachineBusinessApplicationRelationshipViewSet,
    TechnicalServiceDeviceRelationshipViewSet,
    TechnicalServiceVMRelationshipViewSet,
    ServiceDependencyRelationshipViewSet
)
from business_application.api.incident_automation_views import IncidentAutomationViewSet

router = DefaultRouter()

# Basic CRUD endpoints for all models
router.register(r'business-applications', BusinessApplicationViewSet, basename='businessapplication')
router.register(r'technical-services', TechnicalServiceViewSet, basename='technicalservice')
router.register(r'service-dependencies', ServiceDependencyViewSet, basename='servicedependency')
router.register(r'event-sources', EventSourceViewSet, basename='eventsource')
router.register(r'events', EventViewSet, basename='event')
router.register(r'maintenance', MaintenanceViewSet, basename='maintenance')
router.register(r'change-types', ChangeTypeViewSet, basename='changetype')
router.register(r'changes', ChangeViewSet, basename='change')
router.register(r'incidents', IncidentViewSet, basename='incident')
router.register(r'pagerduty-templates', PagerDutyTemplateViewSet, basename='pagerdutytemplate')
router.register(r'external-workflows', ExternalWorkflowViewSet, basename='externalworkflow')
router.register(r'workflow-executions', WorkflowExecutionViewSet, basename='workflowexecution')
router.register(r'alerts', AlertIngestionViewSet, basename='alert-ingestion')


router.register(r'clusters/downstream-applications', ClusterDownstreamAppsViewSet, basename='cluster-downstream-applications')
router.register(r'incident-automation', IncidentAutomationViewSet, basename='incident-automation')

urlpatterns = router.urls + [
    path(
        'devices/downstream-applications/<int:pk>/',
        DeviceDownstreamAppsViewSet.as_view({'get': 'retrieve'}),
        name='device-downstream-applications-detail'
    ),
    path(
        'devices/downstream-applications/',
        DeviceDownstreamAppsViewSet.as_view({'get': 'list'}),
        name='device-downstream-applications-list'
    ),
    # Cluster downstream applications (custom endpoints)
    path(
        'clusters/downstream-applications/<int:pk>/',
        ClusterDownstreamAppsViewSet.as_view({'get': 'retrieve'}),
        name='cluster-downstream-applications-detail'
    ),
    # Device to business application relationships
    path(
        'device-business-app-relationships/',
        DeviceBusinessApplicationRelationshipViewSet.as_view({'get': 'list'}),
        name='device-business-app-relationships-list'
    ),
    # Virtual machine to business application relationships
    path(
        'vm-business-app-relationships/',
        VirtualMachineBusinessApplicationRelationshipViewSet.as_view({'get': 'list'}),
        name='vm-business-app-relationships-list'
    ),
    # Technical service to device relationships
    path(
        'technical-service-device-relationships/',
        TechnicalServiceDeviceRelationshipViewSet.as_view({'get': 'list'}),
        name='technical-service-device-relationships-list'
    ),
    # Technical service to virtual machine relationships
    path(
        'technical-service-vm-relationships/',
        TechnicalServiceVMRelationshipViewSet.as_view({'get': 'list'}),
        name='technical-service-vm-relationships-list'
    ),
    # Service dependency relationships (optimized)
    path(
        'service-dependency-relationships/',
        ServiceDependencyRelationshipViewSet.as_view({'get': 'list'}),
        name='service-dependency-relationships-list'
    ),
]