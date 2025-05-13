from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from business_application.models import BusinessApplication
from business_application.api.serializers import BusinessApplicationSerializer
from rest_framework.permissions import IsAuthenticated
from dcim.models import Device
from django.db.models import Q


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

class DeviceDownstreamAppsViewSet(ModelViewSet):
    queryset = Device.objects.all()
    permission_classes = [IsAuthenticated]

    def _get_downstream_apps(self, device):
        apps = set()
        nodes = [device]
        visited_ids = {device.id}
        current = 0

        while current < len(nodes):
            node = nodes[current]
            found_apps = BusinessApplication.objects.filter(
                Q(devices=node) | Q(virtual_machines__device=node)
            )
            apps.update(found_apps)

            for termination in node.cabletermination_set.all():
                cable = termination.cable
                for t in cable.a_terminations + cable.b_terminations:
                    if hasattr(t, 'device') and t.device and t.device.id not in visited_ids:
                        nodes.append(t.device)
                        visited_ids.add(t.device.id)

            current += 1
        return apps

    def retrieve(self, request, pk=None):
        device = self.get_object()
        apps = self._get_downstream_apps(device)
        serializer = BusinessApplicationSerializer(apps, many=True, context={'request': request})
        return Response(serializer.data)

    def list(self, request):
        all_apps = set()
        for device in self.queryset:
            all_apps.update(self._get_downstream_apps(device))
        serializer = BusinessApplicationSerializer(all_apps, many=True, context={'request': request})
        return Response(serializer.data)
