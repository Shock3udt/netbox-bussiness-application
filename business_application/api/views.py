from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from business_application.models import (
    BusinessApplication, TechnicalService, EventSource, Event,
    Maintenance, ChangeType, Change
)
from business_application.api.serializers import (
    BusinessApplicationSerializer, TechnicalServiceSerializer, EventSourceSerializer,
    EventSerializer, MaintenanceSerializer, ChangeTypeSerializer, ChangeSerializer
)
from rest_framework.permissions import IsAuthenticated
from dcim.models import Device
from virtualization.models import Cluster, VirtualMachine
from django.db.models import Q


class BusinessApplicationViewSet(ModelViewSet):
    """
    API endpoint for managing BusinessApplication objects.
    """
    queryset = BusinessApplication.objects.prefetch_related('virtual_machines').all()
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

class TechnicalServiceViewSet(ModelViewSet):
    """
    API endpoint for managing TechnicalService objects.
    """
    queryset = TechnicalService.objects.select_related('parent').prefetch_related(
        'business_apps', 'vms', 'devices', 'clusters'
    ).all()
    serializer_class = TechnicalServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter the queryset by name or parent from query parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        parent = self.request.query_params.get('parent')
        if name:
            queryset = queryset.filter(name__icontains=name)
        if parent:
            queryset = queryset.filter(parent__name__icontains=parent)
        return queryset

class EventSourceViewSet(ModelViewSet):
    """
    API endpoint for managing EventSource objects.
    """
    queryset = EventSource.objects.prefetch_related('event_set').all()
    serializer_class = EventSourceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter the queryset by name from query parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset

class EventViewSet(ModelViewSet):
    """
    API endpoint for managing Event objects.
    """
    queryset = Event.objects.select_related('event_source', 'content_type').all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter events by various parameters.
        """
        queryset = super().get_queryset()
        status = self.request.query_params.get('status')
        criticality = self.request.query_params.get('criticality')
        event_source = self.request.query_params.get('event_source')
        message = self.request.query_params.get('message')

        if status:
            queryset = queryset.filter(status=status)
        if criticality:
            queryset = queryset.filter(criticallity=criticality)
        if event_source:
            queryset = queryset.filter(event_source__name__icontains=event_source)
        if message:
            queryset = queryset.filter(message__icontains=message)

        return queryset.order_by('-last_seen_at')

class MaintenanceViewSet(ModelViewSet):
    """
    API endpoint for managing Maintenance objects.
    """
    queryset = Maintenance.objects.select_related('content_type').all()
    serializer_class = MaintenanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter maintenance records by various parameters.
        """
        queryset = super().get_queryset()
        status = self.request.query_params.get('status')
        contact = self.request.query_params.get('contact')

        if status:
            queryset = queryset.filter(status=status)
        if contact:
            queryset = queryset.filter(contact__icontains=contact)

        return queryset.order_by('planned_start')

class ChangeTypeViewSet(ModelViewSet):
    """
    API endpoint for managing ChangeType objects.
    """
    queryset = ChangeType.objects.prefetch_related('change_set').all()
    serializer_class = ChangeTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter the queryset by name from query parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset

class ChangeViewSet(ModelViewSet):
    """
    API endpoint for managing Change objects.
    """
    queryset = Change.objects.select_related('type', 'content_type').all()
    serializer_class = ChangeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter changes by various parameters.
        """
        queryset = super().get_queryset()
        change_type = self.request.query_params.get('type')
        description = self.request.query_params.get('description')

        if change_type:
            queryset = queryset.filter(type__name__icontains=change_type)
        if description:
            queryset = queryset.filter(description__icontains=description)

        return queryset.order_by('-created_at')

class DeviceDownstreamAppsViewSet(ModelViewSet):
    """
    API endpoint for listing downstream applications associated with devices.
    """
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
                    # Changed here: check t.device.id
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

class ClusterDownstreamAppsViewSet(ModelViewSet):
    """
    API endpoint for listing downstream applications associated with clusters.
    """
    queryset = Cluster.objects.all()
    serializer_class = BusinessApplicationSerializer
    permission_classes = [IsAuthenticated]

    def _get_downstream_apps_for_cluster(self, cluster):
        apps = set()
        virtual_machines = VirtualMachine.objects.filter(cluster=cluster)
        processed_devices = set()

        for vm in virtual_machines:
            apps.update(BusinessApplication.objects.filter(virtual_machines=vm))
        return apps

    def retrieve(self, request, pk=None):
        cluster = self.get_object()
        apps = self._get_downstream_apps_for_cluster(cluster)
        serializer = BusinessApplicationSerializer(list(apps), many=True, context={'request': request})
        return Response(serializer.data)

    def list(self, request):
        name_filter = request.query_params.get('name')
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))

        clusters = self.queryset

        if name_filter:
            clusters = clusters.filter(name__icontains=name_filter)

        total = clusters.count()
        clusters = clusters[offset:offset + limit]

        result = {}

        for cluster in clusters:
            apps = self._get_downstream_apps_for_cluster(cluster)
            serializer = BusinessApplicationSerializer(list(apps), many=True, context={'request': request})

            result[cluster.id] = {
                "name": cluster.name,
                "applications": serializer.data
            }

        return Response({
            "count": total,
            "limit": limit,
            "offset": offset,
            "results": result
        })
