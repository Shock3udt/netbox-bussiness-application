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
    """
    API endpoint for listing downstream applications associated with devices.
    """
    queryset = Device.objects.all()
    permission_classes = [IsAuthenticated]

    def _get_downstream_apps(self, device):
        seen_ids = set()
        nodes = [device]
        apps = set()

        while nodes:
            node = nodes.pop()
            if node.id in seen_ids:
                continue
            seen_ids.add(node.id)
        
            apps.update(BusinessApplication.objects.filter(
                Q(devices=node) | Q(virtual_machines__device=node)
            ))

            for termination in node.cabletermination_set.select_related('cable').prefetch_related('cable__a_terminations__device', 'cable__b_terminations__device'):
                cable = termination.cable
                for t in cable.a_terminations + cable.b_terminations:
                    if hasattr(t, 'device') and t.device:
                        nodes.append(t.device)

        return apps

    def retrieve(self, request, pk=None):
        device = self.get_object()
        apps = self._get_downstream_apps(device)
        serializer = BusinessApplicationSerializer(apps, many=True, context={'request': request})
        return Response(serializer.data)

    def list(self, request):
        name_filter = request.query_params.get('name')
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
    
        devices = self.queryset
    
        if name_filter:
            devices = devices.filter(name__icontains=name_filter)
    
        total = devices.count()
        devices = devices[offset:offset + limit]
    
        result = {}
    
        for device in devices:
            apps = self._get_downstream_apps(device)
            serializer = BusinessApplicationSerializer(apps, many=True, context={'request': request})
    
            result[device.id] = {
                "name": device.name,
                "applications": serializer.data
            }
    
        return Response({
            "count": total,
            "limit": limit,
            "offset": offset,
            "results": result
        })
