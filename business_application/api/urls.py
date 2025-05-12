from rest_framework.routers import DefaultRouter
from business_application.api.views import BusinessApplicationViewSet, DeviceWithApplicationsViewSet

router = DefaultRouter()
router.register(r'business-applications', BusinessApplicationViewSet, basename='businessapplication')
router.register(r'devices-with-apps', DeviceWithApplicationsViewSet, basename='devicewithapps')

urlpatterns = router.urls
