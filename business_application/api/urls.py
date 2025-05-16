from django.urls import path
from rest_framework.routers import DefaultRouter
from business_application.api.views import BusinessApplicationViewSet, DeviceDownstreamAppsViewSet, ClusterDownstreamAppsViewSet

router = DefaultRouter()
router.register(r'business-applications', BusinessApplicationViewSet, basename='businessapplication')
router.register(r'clusters/downstream-applications', ClusterDownstreamAppsViewSet, basename='cluster-downstream-applications')

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
    path(
        'clusters/downstream-applications/<int:pk>/',
        ClusterDownstreamAppsViewSet.as_view({'get': 'retrieve'}),
        name='cluster-downstream-applications-detail'
    ),
]
