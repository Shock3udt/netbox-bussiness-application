from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from business_application.models import BusinessApplication
from business_application.api.serializers import BusinessApplicationSerializer
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

class DeviceDownstreamAppsViewSet(ViewSet):
    @action(detail=True, methods=['get'], url_path='downstream-applications')
    def downstream_applications(self, request, pk=None):
        try:
            device = Device.objects.get(pk=pk)
        except Device.DoesNotExist:
            return Response({'error': 'Device not found'}, status=404)

        name_filter = request.query_params.get('device_name')
        apps = set()
        visited = set()
        nodes = [device]
        current = 0

        while current < len(nodes):
            node = nodes[current]
            visited.add(node)
            current += 1

            if name_filter and name_filter.lower() not in node.name.lower():
                continue

            apps.update(BusinessApplication.objects.filter(
                Q(devices=node) |
                Q(virtual_machines__device=node)
            ))

            for ct in node.cabletermination_set.all():
                cable = ct.cable
                for term in cable.a_terminations + cable.b_terminations:
                    next_dev = getattr(term, 'device', None)
                    if next_dev and next_dev not in visited and next_dev.role == node.role:
                        nodes.append(next_dev)

        serializer = BusinessApplicationSerializer(apps, many=True, context={'request': request})
        permission_classes = [IsAuthenticated]
        return Response(serializer.data)
