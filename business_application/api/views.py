from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from business_application.models import BusinessApplication
from business_application.api.serializers import BusinessApplicationSerializer
from rest_framework.permissions import IsAuthenticated
from dcim.models import Device
from django.db.models import Q

import logging
logger = logging.getLogger(__name__)


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

    @action(detail=True, methods=['get'], url_path='downstream-applications')
def downstream_applications(self, request, pk=None):
    device = self.get_object()
    logger.info(f"Starting downstream traversal for device {device} (ID={device.id})")

    apps = set()
    nodes = [device]
    visited_ids = set()
    current = 0

    while current < len(nodes):
        node = nodes[current]
        logger.info(f"Visiting device {node.name} (ID={node.id})")

        # Collect apps
        found_apps = BusinessApplication.objects.filter(
            Q(devices=node) | Q(virtual_machines__device=node)
        )
        logger.info(f"Found {found_apps.count()} apps on device {node.name}")
        apps.update(found_apps)

        # Traverse cable connections
        for termination in node.cabletermination_set.all():
            cable = termination.cable

            for t in cable.a_terminations + cable.b_terminations:
                if hasattr(t, 'device') and t.device and t.device.id not in visited_ids:
                    nodes.append(t.device)
                    visited_ids.add(t.device.id)
                    logger.info(f"Found connected device: {t.device.name} (ID={t.device.id})")

        current += 1

    serializer = BusinessApplicationSerializer(apps, many=True, context={'request': request})
    logger.info(f"Returning {len(apps)} downstream apps for device {device.name} (ID={device.id})")
    return Response(serializer.data)
