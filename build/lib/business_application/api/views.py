from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import json
import logging
from datetime import datetime, date

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
from dcim.models import Device
from virtualization.models import Cluster, VirtualMachine
from django.db.models import Q

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
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='generic')
    def generic_alert(self, request):
        """
        Generic alert endpoint accepting standardized JSON payload.
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

    def _clean_raw_data(self, raw_data):
        """
        Ensure raw data is JSON serializable and return as dict.
        """

        def json_serializer(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        try:
            # Try to serialize and deserialize to ensure it's clean JSON
            json_str = json.dumps(raw_data, default=json_serializer)
            return json.loads(json_str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Could not serialize raw_data as JSON: {e}")
            return {"error": "Raw data not serializable", "original_type": str(type(raw_data))}

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
            existing_event.criticallity = self._map_severity_to_criticality(alert_data['severity'])
            existing_event.save()
            logger.info(f"Updated existing event {existing_event.id}")
            return existing_event
        else:
            current_time = timezone.now()

            # Resolve target object
            target_obj, content_type = self._resolve_target(alert_data.get('target', {}))

            # If we couldn't resolve any target object, we can't create the event
            if not target_obj or not content_type:
                raise ValueError(
                    f"Could not resolve target object for alert. "
                    f"Target: {alert_data.get('target', {})}. "
                    f"Ensure at least one Device or TechnicalService exists in the system."
                )

            event_data = {
                'dedup_id': alert_data['dedup_id'],
                'message': alert_data['message'],
                'status': alert_data['status'],
                'criticallity': self._map_severity_to_criticality(alert_data['severity']),
                'raw': alert_data.get('raw_data', {}),
                'last_seen_at': current_time,
                'event_source': self._get_or_create_event_source(alert_data['source']),
                'object_id': target_obj.id,
                'content_type': content_type,
            }

            event = Event.objects.create(**event_data)
            logger.info(f"Created new event {event.id} for {target_obj}")
            return event

    def _resolve_target(self, target_data):
        """
        Resolve target object from target data.
        Returns (target_object, content_type) tuple.
        """
        if not target_data or not target_data.get('type') or not target_data.get('identifier'):
            logger.warning(f"Invalid target data: {target_data}")
            return self._get_fallback_target()

        target_type = target_data['type']
        identifier = target_data['identifier']

        try:
            from django.contrib.contenttypes.models import ContentType

            if target_type == 'device':
                from dcim.models import Device
                target_obj = Device.objects.filter(name=identifier).first()
                if not target_obj:
                    # Auto-create missing device for alert testing
                    logger.info(f"Creating device {identifier} for alert processing")
                    target_obj = self._create_test_device(identifier)
                if target_obj:
                    return target_obj, ContentType.objects.get_for_model(Device)

            elif target_type == 'vm':
                from virtualization.models import VirtualMachine
                target_obj = VirtualMachine.objects.filter(name=identifier).first()
                if target_obj:
                    return target_obj, ContentType.objects.get_for_model(VirtualMachine)

            elif target_type == 'service':
                target_obj = TechnicalService.objects.filter(name=identifier).first()
                if target_obj:
                    return target_obj, ContentType.objects.get_for_model(TechnicalService)

            else:
                logger.warning(f"Unknown target type: {target_type}")

        except Exception as e:
            logger.error(f"Error resolving target {target_type}:{identifier}: {e}")

        # If we couldn't resolve the target, use fallback
        logger.warning(f"Could not resolve target {target_type}:{identifier}, using fallback")
        return self._get_fallback_target()

    def _get_fallback_target(self):
        """
        Get a fallback target object when the actual target cannot be resolved.
        This ensures we always have a valid object_id and content_type.
        """
        try:
            from django.contrib.contenttypes.models import ContentType
            from dcim.models import Device

            # Try to get any existing device as fallback
            fallback_device = Device.objects.first()
            if fallback_device:
                return fallback_device, ContentType.objects.get_for_model(Device)

            # If no devices exist, try to get any TechnicalService
            fallback_service = TechnicalService.objects.first()
            if fallback_service:
                return fallback_service, ContentType.objects.get_for_model(TechnicalService)

        except Exception as e:
            logger.error(f"Error getting fallback target: {e}")

        return None, None

    def _create_test_device(self, device_name):
        """
        Create a minimal test device for alert processing.
        This is used when a device referenced in an alert doesn't exist.
        """
        try:
            from dcim.models import Device, DeviceType, DeviceRole, Site, Manufacturer

            # Get or create required objects for device creation
            manufacturer, _ = Manufacturer.objects.get_or_create(
                name='Unknown',
                defaults={'name': 'Unknown', 'slug': 'unknown'}
            )

            device_type, _ = DeviceType.objects.get_or_create(
                model='Unknown Device',
                manufacturer=manufacturer,
                defaults={
                    'model': 'Unknown Device',
                    'slug': 'unknown-device',
                    'manufacturer': manufacturer
                }
            )

            device_role, _ = DeviceRole.objects.get_or_create(
                name='Alert Target',
                defaults={'name': 'Alert Target', 'slug': 'alert-target'}
            )

            site, _ = Site.objects.get_or_create(
                name='Unknown Site',
                defaults={'name': 'Unknown Site', 'slug': 'unknown-site'}
            )

            # Create the device
            device = Device.objects.create(
                name=device_name,
                device_type=device_type,
                device_role=device_role,
                site=site
            )

            logger.info(f"Created test device: {device_name}")
            return device

        except Exception as e:
            logger.error(f"Error creating test device {device_name}: {e}")
            return None

    def _process_standard_alert(self, standard_payload):
        """
        Common processing for all standardized alerts.
        Bypasses serializer validation since data is already transformed.
        """
        try:
            # Process the alert directly without re-validation
            event = self._process_alert(standard_payload)

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
            "timestamp": capacitor_data.get('alert_time', timezone.now()),
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
            "raw_data": self._clean_raw_data(capacitor_data)
        }

    def _transform_signalfx_alert(self, signalfx_data):
        """
        Transform SignalFX webhook format to standard format.
        """
        return {
            "source": "signalfx",
            "timestamp": signalfx_data.get('timestamp', timezone.now()),
            "severity": signalfx_data.get('severity', 'medium').lower(),
            "status": signalfx_data.get('alertState', 'triggered').lower(),
            "message": signalfx_data.get('alertMessage', ''),
            "dedup_id": f"signalfx-{signalfx_data.get('incidentId', '')}",
            "target": {
                "type": self._determine_target_type(signalfx_data),
                "identifier": self._extract_target_identifier(signalfx_data)
            },
            "raw_data": self._clean_raw_data(signalfx_data)
        }

    def _transform_email_alert(self, email_data):
        """
        Transform parsed email content to standard format.
        """
        return {
            "source": "email",
            "timestamp": email_data.get('timestamp', timezone.now()),
            "severity": email_data.get('severity', 'medium'),
            "status": "triggered",
            "message": email_data.get('subject', '') + '\n' + email_data.get('body', ''),
            "dedup_id": f"email-{email_data.get('message_id', '')}",
            "target": {
                "type": email_data.get('target_type', 'service'),
                "identifier": email_data.get('target_identifier', '')
            },
            "raw_data": self._clean_raw_data(email_data)
        }

    def _get_or_create_event_source(self, source_name):
        """Get or create EventSource object."""
        event_source, created = EventSource.objects.get_or_create(
            name=source_name,
            defaults={
                'name': source_name,
                'description': f'Auto-created source for {source_name}',
            }
        )
        if created:
            logger.info(f"Created new event source: {source_name}")
        return event_source

    def _map_severity_to_criticality(self, severity):
        """Map severity levels to Event criticallity choices (note the typo in field name)."""
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