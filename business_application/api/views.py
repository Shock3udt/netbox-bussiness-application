from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from business_application.models import BusinessApplication
from business_application.api.serializers import BusinessApplicationSerializer
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
            # CHANGE: vm.host changed to vm.device
            if vm.device and vm.device.id not in processed_devices:
                nodes = [vm.device] # Changed here
                visited_ids = {vm.device.id} # Changed here
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
                processed_devices.add(vm.device.id) # Changed here
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
