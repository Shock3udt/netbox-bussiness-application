from django.urls import path
from rest_framework.routers import DefaultRouter
from business_application.api.views import BusinessApplicationViewSet, DeviceDownstreamAppsViewSet

router = DefaultRouter()
router.register(r'business-applications', BusinessApplicationViewSet, basename='businessapplication')

device_downstream_view = DeviceDownstreamAppsViewSet.as_view({
    'get': 'downstream_applications'
})

urlpatterns = router.urls + [
    path(
        'devices/<int:pk>/downstream-applications/',
        device_downstream_view,
        name='device-downstream-applications'
    )
]
