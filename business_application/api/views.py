from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import json
import logging
from datetime import datetime, date
try:
    from dateutil import parser as dateutil_parser
except ImportError:
    dateutil_parser = None

from business_application.models import (
    BusinessApplication, TechnicalService, ServiceDependency, EventSource, Event,
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate
)
from business_application.api.serializers import (
    BusinessApplicationSerializer, TechnicalServiceSerializer, ServiceDependencySerializer,
    EventSourceSerializer, EventSerializer, MaintenanceSerializer, ChangeTypeSerializer,
    ChangeSerializer, IncidentSerializer, GenericAlertSerializer,
    CapacitorAlertSerializer,
    SignalFXAlertSerializer,
    EmailAlertSerializer,
    GitLabSerializer,
    PagerDutyTemplateSerializer
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
    ).select_related('pagerduty_template').all()
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

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """
        Bulk delete events by IDs.
        Expects a JSON payload with 'ids' array.
        """
        try:
            ids = request.data.get('ids', [])
            if not ids:
                return Response(
                    {'error': 'No event IDs provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not isinstance(ids, list):
                return Response(
                    {'error': 'IDs must be provided as an array'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate that all IDs are integers
            try:
                ids = [int(id) for id in ids]
            except (ValueError, TypeError):
                return Response(
                    {'error': 'All IDs must be valid integers'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get events that exist and user can delete
            queryset = self.get_queryset()
            events_to_delete = queryset.filter(id__in=ids)

            if not events_to_delete.exists():
                return Response(
                    {'error': 'No valid events found for the provided IDs'},
                    status=status.HTTP_404_NOT_FOUND
                )

            deleted_count = events_to_delete.count()
            events_to_delete.delete()

            logger.info(f'Bulk deleted {deleted_count} events by user {request.user}')

            return Response(
                {
                    'success': True,
                    'deleted_count': deleted_count,
                    'message': f'Successfully deleted {deleted_count} events'
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.exception(f'Error during bulk delete: {str(e)}')
            return Response(
                {'error': 'Failed to delete events', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='bulk-update-status')
    def bulk_update_status(self, request):
        """
        Bulk update event status.
        Expects a JSON payload with 'ids' array and 'status' field.
        """
        try:
            ids = request.data.get('ids', [])
            new_status = request.data.get('status')

            if not ids:
                return Response(
                    {'error': 'No event IDs provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not new_status:
                return Response(
                    {'error': 'No status provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate status value
            from business_application.models import EventStatus
            valid_statuses = [choice[0] for choice in EventStatus.CHOICES]
            if new_status not in valid_statuses:
                return Response(
                    {'error': f'Invalid status. Must be one of: {valid_statuses}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            queryset = self.get_queryset()
            events_to_update = queryset.filter(id__in=ids)

            if not events_to_update.exists():
                return Response(
                    {'error': 'No valid events found for the provided IDs'},
                    status=status.HTTP_404_NOT_FOUND
                )

            updated_count = events_to_update.update(status=new_status)

            logger.info(f'Bulk updated status to {new_status} for {updated_count} events by user {request.user}')

            return Response(
                {
                    'success': True,
                    'updated_count': updated_count,
                    'message': f'Successfully updated status for {updated_count} events'
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.exception(f'Error during bulk status update: {str(e)}')
            return Response(
                {'error': 'Failed to update event status', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """
        Bulk delete incidents by IDs.
        Expects a JSON payload with 'ids' array.
        """
        try:
            ids = request.data.get('ids', [])
            if not ids:
                return Response(
                    {'error': 'No incident IDs provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            queryset = self.get_queryset()
            incidents_to_delete = queryset.filter(id__in=ids)

            if not incidents_to_delete.exists():
                return Response(
                    {'error': 'No valid incidents found for the provided IDs'},
                    status=status.HTTP_404_NOT_FOUND
                )

            deleted_count = incidents_to_delete.count()
            incidents_to_delete.delete()

            logger.info(f'Bulk deleted {deleted_count} incidents by user {request.user}')

            return Response(
                {
                    'success': True,
                    'deleted_count': deleted_count,
                    'message': f'Successfully deleted {deleted_count} incidents'
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.exception(f'Error during bulk delete: {str(e)}')
            return Response(
                {'error': 'Failed to delete incidents', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='bulk-update-status')
    def bulk_update_status(self, request):
        """
        Bulk update incident status.
        Expects a JSON payload with 'ids' array and 'status' field.
        """
        try:
            ids = request.data.get('ids', [])
            new_status = request.data.get('status')

            if not ids or not new_status:
                return Response(
                    {'error': 'Both ids and status are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate status value
            from business_application.models import IncidentStatus
            valid_statuses = [choice[0] for choice in IncidentStatus.CHOICES]
            if new_status not in valid_statuses:
                return Response(
                    {'error': f'Invalid status. Must be one of: {valid_statuses}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            queryset = self.get_queryset()
            incidents_to_update = queryset.filter(id__in=ids)

            if not incidents_to_update.exists():
                return Response(
                    {'error': 'No valid incidents found for the provided IDs'},
                    status=status.HTTP_404_NOT_FOUND
                )

            updated_count = incidents_to_update.update(status=new_status)

            logger.info(f'Bulk updated status to {new_status} for {updated_count} incidents by user {request.user}')

            return Response(
                {
                    'success': True,
                    'updated_count': updated_count,
                    'message': f'Successfully updated status for {updated_count} incidents'
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.exception(f'Error during bulk status update: {str(e)}')
            return Response(
                {'error': 'Failed to update incident status', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='blast-radius')
    def blast_radius(self, request, pk=None):
        """
        Calculate the blast radius (downstream impact) of an incident.
        Returns all services that could be affected by this incident.
        """
        try:
            incident = self.get_object()

            # Use the correlation engine to calculate blast radius
            from ..utils.correlation import AlertCorrelationEngine
            correlation_engine = AlertCorrelationEngine()
            affected_services = correlation_engine.calculate_blast_radius(incident)

            # Serialize the services
            service_data = []
            for service in affected_services:
                service_data.append({
                    'id': service.id,
                    'name': service.name,
                    'service_type': service.service_type,
                    'health_status': service.health_status
                })

            return Response({
                'incident_id': incident.id,
                'incident_title': incident.title,
                'affected_services_count': len(affected_services),
                'affected_services': service_data
            })

        except Exception as e:
            logger.exception(f'Error calculating blast radius: {str(e)}')
            return Response(
                {'error': 'Failed to calculate blast radius', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PagerDutyTemplateViewSet(ModelViewSet):
    """
    API endpoint for managing PagerDutyTemplate objects.
    """
    queryset = PagerDutyTemplate.objects.prefetch_related('technical_services').all()
    serializer_class = PagerDutyTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter PagerDuty templates by various parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')

        return queryset.order_by('name')


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
                for t in cable.b_terminations:
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

    @action(detail=False, methods=['post'], url_path='gitlab')
    def gitlab_alert(self, request):
        """
        GitLab webhook endpoint.
        Transforms GitLab merge request and pipeline     events to standard format.
        """
        serializer = GitLabSerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(f"Invalid GitLab pipeline event: {serializer.errors}")
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filter out merge request pipelines
        object_kind = serializer.validated_data['object_kind']
        if object_kind == 'merge_request':
            logger.info("Detected merge request pipeline event")
            standard_payload = self._transform_gitlab_merge_request(
                serializer.validated_data
            )
        elif object_kind == 'pipeline':
            logger.info(f"Processing pipeline event: {object_kind}")
            standard_payload = self._transform_gitlab_pipeline(
                serializer.validated_data
            )
        else:
            logger.error(f"Invalid GitLab event: {object_kind}")
            return Response(
                {"errors": "Invalid GitLab event"},
                status=status.HTTP_400_BAD_REQUEST
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

            # Re-check target validity for existing events
            if not existing_event.has_valid_target:
                target_obj, content_type = self._resolve_target(alert_data.get('target', {}))
                if target_obj and content_type:
                    # Target is now available - make event valid
                    existing_event.object_id = target_obj.id
                    existing_event.content_type = content_type
                    existing_event.is_valid = True
                    logger.info(f"Event {existing_event.id} target resolved, marked as valid")

            existing_event.save()
            logger.info(f"Updated existing event {existing_event.id}")
            return existing_event
        else:
            current_time = timezone.now()

            target_obj, content_type = self._resolve_target(alert_data.get('target', {}))

            # Prepare base event data
            event_data = {
                'dedup_id': alert_data['dedup_id'],
                'message': alert_data['message'],
                'status': alert_data['status'],
                'criticallity': self._map_severity_to_criticality(alert_data['severity']),
                'raw': alert_data.get('raw_data', {}),
                'last_seen_at': current_time,
                'event_source': self._get_or_create_event_source(alert_data['source']),
            }

            # Handle target resolution
            if target_obj and content_type:
                # Valid target found
                event_data.update({
                    'object_id': target_obj.id,
                    'content_type': content_type,
                    'is_valid': True,
                })
                logger.info(f"Creating event with valid target: {target_obj}")
            else:
                # No valid target found - create invalid event
                event_data.update({
                    'object_id': None,
                    'content_type': None,
                    'is_valid': False,
                })
                logger.warning(f"Creating invalid event - could not resolve target: {alert_data.get('target', {})}")

            event = Event.objects.create(**event_data)
            target_info = target_obj if target_obj else "no valid target"
            logger.info(f"Created new event {event.id} for {target_info}")
            return event

    def _resolve_target(self, target_data):
        """
        Resolve target object from target data.
        Returns (target_object, content_type) tuple.
        """
        if not target_data or not target_data.get('type') or not target_data.get('identifier'):
            logger.warning(f"Invalid target data: {target_data}")
            return None, None

        target_type = target_data['type']
        identifier = target_data['identifier']

        try:
            from django.contrib.contenttypes.models import ContentType

            if target_type == 'device':
                from dcim.models import Device
                target_obj = Device.objects.filter(name=identifier).first()
                if target_obj:
                    return target_obj, ContentType.objects.get_for_model(Device)

            elif target_type == 'vm':
                from virtualization.models import VirtualMachine
                target_obj = VirtualMachine.objects.filter(name=identifier).first()
                if target_obj:
                    return target_obj, ContentType.objects.get_for_model(VirtualMachine)

            elif target_type == 'service':
                # Handle GitLab service naming convention: "gitlab: <path_with_namespace>"
                target_obj = TechnicalService.objects.filter(name=identifier).first()
                if not target_obj and identifier.startswith('gitlab:'):
                    # Only auto-create GitLab services
                    logger.info(f"Creating GitLab service {identifier} for alert processing")
                    target_obj = self._create_test_service(identifier)
                if target_obj:
                    return target_obj, ContentType.objects.get_for_model(TechnicalService)

            else:
                logger.warning(f"Unknown target type: {target_type}")

        except Exception as e:
            logger.error(f"Error resolving target {target_type}:{identifier}: {e}")

        logger.warning(f"Could not resolve target {target_type}:{identifier}, will create invalid event")
        return None, None

    def _create_test_service(self, service_name):
        """
        Create a minimal test technical service for alert processing.
        This is used when a service referenced in an alert doesn't exist.
        """
        try:
            # Check if service already exists
            existing_service = TechnicalService.objects.filter(name=service_name).first()
            if existing_service:
                return existing_service

            # Create the service
            service = TechnicalService.objects.create(
                name=service_name,
                service_type='technical'
            )

            logger.info(f"Created test service: {service_name}")
            return service

        except Exception as e:
            logger.error(f"Error creating test service {service_name}: {e}")
            return None

    def _process_standard_alert(self, standard_payload):
        """
        Common processing for all standardized alerts.
        Bypasses serializer validation since data is already transformed.
        """
        try:
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

    def _transform_gitlab_merge_request(self, gitlab_data):
        """
        Transform GitLab merge request webhook format to standard format.
        """
        object_attributes = gitlab_data.get('object_attributes', {})
        project = gitlab_data.get('project', {})
        user = gitlab_data.get('user', {})
        assignees = gitlab_data.get('assignees', [])

        # Map GitLab merge request action and state to event status and severity
        mr_action = object_attributes.get('action', 'unknown')
        mr_state = object_attributes.get('state', 'unknown')
        event_status, event_severity = self._map_gitlab_merge_request_status(mr_action, mr_state)

        # Generate comprehensive message with merge request information
        mr_iid = object_attributes.get('iid', 'unknown')
        mr_title = object_attributes.get('title', 'No title')
        project_path = project.get('path_with_namespace', 'unknown/project')
        author_name = user.get('name', 'Unknown')
        source_branch = object_attributes.get('source_branch', 'unknown')
        target_branch = object_attributes.get('target_branch', 'unknown')

        # Build detailed message
        message = f"GitLab MR !{mr_iid} {mr_action} in {project_path}: {mr_title}"
        if source_branch and target_branch:
            message += f" ({source_branch} → {target_branch})"
        if author_name and author_name != 'Unknown':
            message += f" by {author_name}"

        # Add assignee information if available
        if assignees:
            assignee_names = [assignee.get('name', 'Unknown') for assignee in assignees]
            message += f" - Assigned to: {', '.join(assignee_names)}"

        # Create timestamp from merge request data
        timestamp = self._parse_gitlab_timestamp(
            object_attributes.get('created_at') or
            object_attributes.get('updated_at')
        )

        return {
            "source": "gitlab",
            "timestamp": timestamp,
            "severity": event_severity,
            "status": event_status,
            "message": message,
            "dedup_id": f"gitlab-merge-request-{object_attributes.get('id', '')}",
            "target": {
                "type": "service",
                "identifier": f"gitlab: {project_path}"
            },
            "raw_data": self._clean_raw_data(gitlab_data)
        }

    def _transform_gitlab_pipeline(self, gitlab_data):
        """
        Transform GitLab pipeline webhook format to standard format.
        """
        object_attributes = gitlab_data['object_attributes']
        project = gitlab_data['project']
        commit = gitlab_data.get('commit', {})
        user = gitlab_data.get('user', {})

        # Map GitLab pipeline status to event status and severity
        pipeline_status = object_attributes['status']
        event_status, event_severity = self._map_gitlab_pipeline_status(pipeline_status)

        # Generate message with pipeline information
        pipeline_id = object_attributes['id']
        project_path = project['path_with_namespace']
        commit_message = commit.get('message', 'No commit message')
        commit_author = commit.get('author_name', 'Unknown')

        message = f"GitLab pipeline {pipeline_status} for {project_path}"
        if commit_message and commit_message != 'No commit message':
            message += f" - {commit_message[:100]}"
        if commit_author and commit_author != 'Unknown':
            message += f" by {commit_author}"

        return {
            "source": "gitlab",
            "timestamp": timezone.now(),  # GitLab webhook doesn't always include finished_at
            "severity": event_severity,
            "status": event_status,
            "message": message,
            "dedup_id": f"gitlab-pipeline-{pipeline_id}",
            "target": {
                "type": "service",
                "identifier": f"gitlab: {project_path}"
            },
            "raw_data": self._clean_raw_data(gitlab_data)
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
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low'
        }
        return mapping.get(severity.lower(), 'medium')

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

    def _map_gitlab_pipeline_status(self, pipeline_status):
        """
        Map GitLab pipeline status to event status and severity.
        Returns tuple of (event_status, event_severity).
        """
        # GitLab pipeline statuses: created, waiting_for_resource, preparing, pending, running,
        # success, failed, canceled, skipped, manual, scheduled

        status_mapping = {
            'success': ('ok', 'low'),
            'failed': ('triggered', 'critical'),
            'canceled': ('suppressed', 'low'),
            'skipped': ('suppressed', 'low'),
            'running': ('triggered', 'low'),
            'pending': ('triggered', 'low'),
            'created': ('triggered', 'low'),
            'waiting_for_resource': ('triggered', 'low'),
            'preparing': ('triggered', 'low'),
            'manual': ('triggered', 'low'),
            'scheduled': ('triggered', 'low'),
        }

        # Default for any unknown status
        return status_mapping.get(pipeline_status, ('triggered', 'low'))

    def _map_gitlab_merge_request_status(self, mr_action, mr_state):
        """
        Map GitLab merge request action and state to event status and severity.
        Returns tuple of (event_status, event_severity).
        """

        # Priority mapping: action takes precedence over state for determining severity
        action_mapping = {
            'open': ('triggered', 'low'),
            'reopen': ('triggered', 'medium'),
            'close': ('ok', 'low'),
            'merge': ('ok', 'low'),
            'update': ('triggered', 'low'),
            'approved': ('ok', 'low'),
            'unapproved': ('triggered', 'medium'),
            'approval': ('ok', 'low'),
            'unapproval': ('triggered', 'medium'),
        }

        # State-based mapping as fallback
        state_mapping = {
            'opened': ('triggered', 'low'),
            'closed': ('ok', 'low'),
            'merged': ('ok', 'low'),
            'locked': ('suppressed', 'low'),
        }

        # Check action first, then state, then default
        if mr_action in action_mapping:
            return action_mapping[mr_action]
        elif mr_state in state_mapping:
            return state_mapping[mr_state]
        else:
            # Default for unknown action/state
            return ('triggered', 'low')

    def _parse_gitlab_timestamp(self, timestamp_str):
        """
        Parse GitLab timestamp string to Django timezone-aware datetime.
        Falls back to current time if parsing fails.
        """
        if not timestamp_str:
            return timezone.now()

        try:
            # GitLab timestamps are typically in ISO format with Z suffix
            # Example: "2025-11-27T08:32:43.809Z"
            if dateutil_parser:
                parsed_dt = dateutil_parser.parse(timestamp_str)
            else:
                # Fallback to basic datetime parsing if dateutil not available
                # Handle common GitLab timestamp format: 2025-11-27T08:32:43.809Z
                timestamp_str = timestamp_str.replace('Z', '+00:00')
                parsed_dt = datetime.fromisoformat(timestamp_str)

            # Ensure timezone awareness
            if parsed_dt.tzinfo is None:
                # Assume UTC if no timezone info - use Django's timezone.now() timezone
                parsed_dt = timezone.make_aware(parsed_dt, timezone.get_current_timezone())

            return parsed_dt

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse GitLab timestamp '{timestamp_str}': {e}")
            return timezone.now()

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