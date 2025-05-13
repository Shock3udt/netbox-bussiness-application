from django.urls import path
from rest_framework.routers import DefaultRouter
from business_application.api.views import BusinessApplicationViewSet, DeviceDownstreamAppsViewSet

router = DefaultRouter()
router.register(r'business-applications', BusinessApplicationViewSet, basename='businessapplication')
router.register(r'devices', DeviceDownstreamAppsViewSet, basename='devicedownstreamapps')
