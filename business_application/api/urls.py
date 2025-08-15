from django.urls import path
from rest_framework.routers import DefaultRouter
from business_application.api.views import (
    BusinessApplicationViewSet, TechnicalServiceViewSet, ServiceDependencyViewSet,
    EventSourceViewSet, EventViewSet, MaintenanceViewSet, ChangeTypeViewSet, ChangeViewSet,
    IncidentViewSet, DeviceDownstreamAppsViewSet, ClusterDownstreamAppsViewSet, AlertIngestionViewSet, PagerDutyTemplateViewSet
)

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
router.register(r'alerts', AlertIngestionViewSet, basename='alert-ingestion')


# Complex endpoints for downstream application analysis
router.register(r'clusters/downstream-applications', ClusterDownstreamAppsViewSet, basename='cluster-downstream-applications')

urlpatterns = router.urls + [
    # Device downstream applications (custom endpoints)
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
]
