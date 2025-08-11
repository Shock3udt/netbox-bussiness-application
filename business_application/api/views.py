from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from business_application.models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident
)
from business_application.api.serializers import (
    BusinessApplicationSerializer, TechnicalServiceSerializer, ServiceDependencySerializer,
    EventSourceSerializer, EventSerializer, MaintenanceSerializer, ChangeTypeSerializer,
    ChangeSerializer, IncidentSerializer, GenericAlertSerializer,
    CapacitorAlertSerializer,
    SignalFXAlertSerializer,
    EmailAlertSerializer,
)
from rest_framework.permissions import IsAuthenticated
from dcim.models import Device
from virtualization.models import Cluster, VirtualMachine
from django.db.models import Q


from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from netbox.api.authentication import TokenPermissions
from django.utils import timezone
import json
import logging

from ..utils.correlation import AlertCorrelationEngine

logger = logging.getLogger('business_application.api')


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
    queryset = TechnicalService.objects.prefetch_related(
        'business_apps', 'vms', 'devices', 'clusters'
    ).all()
    serializer_class = TechnicalServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter the queryset by name or service_type from query parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        service_type = self.request.query_params.get('service_type')
        if name:
            queryset = queryset.filter(name__icontains=name)
        if service_type:
            queryset = queryset.filter(service_type=service_type)
        return queryset

class ServiceDependencyViewSet(ModelViewSet):
    """
    API endpoint for managing ServiceDependency objects.
    """
    queryset = ServiceDependency.objects.select_related(
        'upstream_service', 'downstream_service'
    ).all()
    serializer_class = ServiceDependencySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter dependencies by various parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        dependency_type = self.request.query_params.get('dependency_type')
        upstream_service = self.request.query_params.get('upstream_service')
        downstream_service = self.request.query_params.get('downstream_service')

        if name:
            queryset = queryset.filter(name__icontains=name)
        if dependency_type:
            queryset = queryset.filter(dependency_type=dependency_type)
        if upstream_service:
            queryset = queryset.filter(upstream_service__name__icontains=upstream_service)
        if downstream_service:
            queryset = queryset.filter(downstream_service__name__icontains=downstream_service)

        return queryset.order_by('name')

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

class IncidentViewSet(ModelViewSet):
    """
    API endpoint for managing Incident objects.
    """
    queryset = Incident.objects.prefetch_related('responders', 'affected_services', 'events').all()
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter incidents by various parameters.
        """
        queryset = super().get_queryset()
        status = self.request.query_params.get('status')
        severity = self.request.query_params.get('severity')
        title = self.request.query_params.get('title')
        reporter = self.request.query_params.get('reporter')
        commander = self.request.query_params.get('commander')

        if status:
            queryset = queryset.filter(status=status)
        if severity:
            queryset = queryset.filter(severity=severity)
        if title:
            queryset = queryset.filter(title__icontains=title)
        if reporter:
            queryset = queryset.filter(reporter__icontains=reporter)
        if commander:
            queryset = queryset.filter(commander__icontains=commander)

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


class AlertIngestionViewSet(ViewSet):
    """
    ViewSet for handling alert ingestion from various sources.
    All endpoints require authentication via NetBox API tokens.
    """
    permission_classes = [IsAuthenticated, TokenPermissions]

    def get_permissions(self):
        """
        Ensure proper permissions for alert ingestion
        """
        return super().get_permissions()

    @action(detail=False, methods=['post'], url_path='generic')
    def generic_alert(self, request):
        """
        Generic alert endpoint accepting standardized JSON payload.

        Expected payload format:
        {
            "source": "monitoring-system",
            "timestamp": "2025-01-10T10:00:00Z",
            "severity": "critical|high|medium|low",
            "status": "triggered|ok|suppressed",
            "message": "Alert description",
            "dedup_id": "unique-alert-identifier",
            "target": {
                "type": "device|vm|service",
                "identifier": "hostname or service name"
            },
            "raw_data": {}
        }
        """
        serializer = GenericAlertSerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(f"Invalid alert payload: {serializer.errors}")
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event = self._process_alert(serializer.validated_data)

            correlation_engine = AlertCorrelationEngine()
            incident = correlation_engine.correlate_alert(event)

            return Response({
                "status": "success",
                "event_id": event.id,
                "incident_id": incident.id if incident else None,
                "message": "Alert processed successfully"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception(f"Error processing alert: {str(e)}")
            return Response(
                {"error": "Failed to process alert", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='capacitor')
    def capacitor_alert(self, request):
        """
        Capacitor-specific alert endpoint.
        Transforms Capacitor payload to standard format.
        """
        serializer = CapacitorAlertSerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(f"Invalid Capacitor alert: {serializer.errors}")
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        standard_payload = self._transform_capacitor_alert(
            serializer.validated_data
        )

        return self._process_standard_alert(standard_payload)

    @action(detail=False, methods=['post'], url_path='signalfx')
    def signalfx_alert(self, request):
        """
        SignalFX-specific alert endpoint.
        Transforms SignalFX webhook payload to standard format.
        """
        serializer = SignalFXAlertSerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(f"Invalid SignalFX alert: {serializer.errors}")
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        standard_payload = self._transform_signalfx_alert(
            serializer.validated_data
        )

        return self._process_standard_alert(standard_payload)

    @action(detail=False, methods=['post'], url_path='email')
    def email_alert(self, request):
        """
        Email alert endpoint (typically called from N8N).
        Transforms parsed email content to standard format.
        """
        serializer = EmailAlertSerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(f"Invalid email alert: {serializer.errors}")
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        standard_payload = self._transform_email_alert(
            serializer.validated_data
        )

        return self._process_standard_alert(standard_payload)

    def _process_alert(self, alert_data):
        """
        Core alert processing logic.
        Creates or updates Event object.
        """
        existing_event = Event.objects.filter(
            dedup_id=alert_data['dedup_id']
        ).first()

        if existing_event:
            existing_event.last_seen_at = timezone.now()
            existing_event.message = alert_data['message']
            existing_event.status = alert_data['status']
            existing_event.raw = alert_data.get('raw_data', {})
            existing_event.save()
            logger.info(f"Updated existing event {existing_event.id}")
            return existing_event
        else:
            event = Event.objects.create(
                dedup_id=alert_data['dedup_id'],
                message=alert_data['message'],
                status=alert_data['status'],
                criticality=self._map_severity_to_criticality(
                    alert_data['severity']
                ),
                raw=alert_data.get('raw_data', {}),
                reporter=alert_data.get('source', 'unknown'),
                event_source=self._get_or_create_event_source(
                    alert_data['source']
                ),
            )
            logger.info(f"Created new event {event.id}")
            return event

    def _process_standard_alert(self, standard_payload):
        """
        Common processing for all standardized alerts.
        """
        try:
            serializer = GenericAlertSerializer(data=standard_payload)
            if not serializer.is_valid():
                return Response(
                    {"errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            event = self._process_alert(serializer.validated_data)

            correlation_engine = AlertCorrelationEngine()
            incident = correlation_engine.correlate_alert(event)

            return Response({
                "status": "success",
                "event_id": event.id,
                "incident_id": incident.id if incident else None,
                "message": "Alert processed successfully"
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception(f"Error processing alert: {str(e)}")
            return Response(
                {"error": "Failed to process alert", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _transform_capacitor_alert(self, capacitor_data):
        """
        Transform Capacitor-specific format to standard format.
        """
        return {
            "source": "capacitor",
            "timestamp": capacitor_data.get('alert_time', timezone.now().isoformat()),
            "severity": self._map_capacitor_severity(
                capacitor_data.get('priority', 3)
            ),
            "status": "triggered" if capacitor_data.get('state') == 'ALARM' else 'ok',
            "message": capacitor_data.get('description', ''),
            "dedup_id": f"capacitor-{capacitor_data.get('alert_id', '')}",
            "target": {
                "type": "device",
                "identifier": capacitor_data.get('device_name', '')
            },
            "raw_data": capacitor_data
        }

    def _transform_signalfx_alert(self, signalfx_data):
        """
        Transform SignalFX webhook format to standard format.
        """
        return {
            "source": "signalfx",
            "timestamp": signalfx_data.get('timestamp', timezone.now().isoformat()),
            "severity": signalfx_data.get('severity', 'medium').lower(),
            "status": signalfx_data.get('alertState', 'triggered').lower(),
            "message": signalfx_data.get('alertMessage', ''),
            "dedup_id": f"signalfx-{signalfx_data.get('incidentId', '')}",
            "target": {
                "type": self._determine_target_type(signalfx_data),
                "identifier": self._extract_target_identifier(signalfx_data)
            },
            "raw_data": signalfx_data
        }

    def _transform_email_alert(self, email_data):
        """
        Transform parsed email content to standard format.
        """
        # Email data comes pre-parsed from N8N
        return {
            "source": "email",
            "timestamp": email_data.get('timestamp', timezone.now().isoformat()),
            "severity": email_data.get('severity', 'medium'),
            "status": "triggered",
            "message": email_data.get('subject', '') + '\n' + email_data.get('body', ''),
            "dedup_id": f"email-{email_data.get('message_id', '')}",
            "target": {
                "type": email_data.get('target_type', 'service'),
                "identifier": email_data.get('target_identifier', '')
            },
            "raw_data": email_data
        }

    def _map_severity_to_criticality(self, severity):
        """Map severity levels to Event criticality choices."""
        mapping = {
            'critical': 'CRITICAL',
            'high': 'HIGH',
            'medium': 'MEDIUM',
            'low': 'LOW'
        }
        return mapping.get(severity.lower(), 'MEDIUM')

    def _map_capacitor_severity(self, priority):
        """Map Capacitor priority (1-5) to standard severity."""
        mapping = {
            1: 'critical',
            2: 'high',
            3: 'medium',
            4: 'low',
            5: 'low'
        }
        return mapping.get(priority, 'medium')

    def _determine_target_type(self, signalfx_data):
        """Determine target type from SignalFX data."""
        dimensions = signalfx_data.get('dimensions', {})
        if 'host' in dimensions:
            return 'device'
        elif 'vm_name' in dimensions:
            return 'vm'
        else:
            return 'service'

    def _extract_target_identifier(self, signalfx_data):
        """Extract target identifier from SignalFX data."""
        dimensions = signalfx_data.get('dimensions', {})
        return (dimensions.get('host') or
                dimensions.get('vm_name') or
                dimensions.get('service_name', ''))

    def _get_or_create_event_source(self, source_name):
        """Get or create EventSource object."""
        return None