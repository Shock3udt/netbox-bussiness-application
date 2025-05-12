from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from business_application.models import BusinessApplication
from business_application.api.serializers import BusinessApplicationSerializer, DeviceWithApplicationsSerializer
from rest_framework.permissions import IsAuthenticated
from dcim.models import Device


class BusinessApplicationViewSet(ModelViewSet):
    """
    API endpoint for managing BusinessApplication objects.
    """
    queryset = BusinessApplication.objects.prefetch_related('virtual_machines', 'devices').all()
    serializer_class = BusinessApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter the queryset by name or appcode from query parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        appcode = self.request.query_params.get('appcode')
        if name:
            queryset = queryset.filter(name__icontains=name)
        if appcode:
            queryset = queryset.filter(appcode__iexact=appcode)
        return queryset

class DeviceWithApplicationsViewSet(ReadOnlyModelViewSet):
    """
    API endpoint that lists Devices with their related Business Applications.
    """
    queryset = Device.objects.prefetch_related('business_applications').all()
    serializer_class = DeviceWithApplicationsSerializer
    permission_classes = [IsAuthenticated]
