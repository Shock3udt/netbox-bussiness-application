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
    Maintenance, ChangeType, Change, Incident, PagerDutyTemplate, ExternalWorkflow,
    WorkflowExecution, WorkflowExecutionStatus
)
from business_application.config import external_workflow_config
from django.contrib.contenttypes.models import ContentType
import requests as http_requests
from business_application.api.serializers import (
    BusinessApplicationSerializer, TechnicalServiceSerializer, ServiceDependencySerializer,
    EventSourceSerializer, EventSerializer, MaintenanceSerializer, ChangeTypeSerializer,
    ChangeSerializer, IncidentSerializer, GenericAlertSerializer,
    CapacitorAlertSerializer,
    SignalFXAlertSerializer,
    EmailAlertSerializer,
    GitLabSerializer,
    PagerDutyTemplateSerializer
    ExternalWorkflowSerializer,
    WorkflowExecutionSerializer
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


class ExternalWorkflowViewSet(ModelViewSet):
    """
    API endpoint for managing ExternalWorkflow objects.
    """
    queryset = ExternalWorkflow.objects.all()
    serializer_class = ExternalWorkflowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter external workflows by various parameters.
        """
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        workflow_type = self.request.query_params.get('workflow_type')
        object_type = self.request.query_params.get('object_type')
        enabled = self.request.query_params.get('enabled')

        if name:
            queryset = queryset.filter(name__icontains=name)
        if workflow_type:
            queryset = queryset.filter(workflow_type=workflow_type)
        if object_type:
            queryset = queryset.filter(object_type=object_type)
        if enabled is not None:
            queryset = queryset.filter(enabled=enabled.lower() == 'true')

        return queryset.order_by('name')

    @action(detail=True, methods=['post'], url_path='test')
    def test_workflow(self, request, pk=None):
        """
        Test a workflow configuration with sample data.
        """
        try:
            workflow = self.get_object()

            # Get test object based on workflow object_type
            test_obj = None
            if workflow.object_type == 'device':
                test_obj = Device.objects.first()
            elif workflow.object_type == 'incident':
                test_obj = Incident.objects.first()
            elif workflow.object_type == 'event':
                test_obj = Event.objects.first()

            if not test_obj:
                return Response({
                    'success': False,
                    'error': f'No {workflow.object_type} objects found to test with'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Generate mapped parameters
            mapped_params = workflow.get_mapped_parameters(test_obj)

            return Response({
                'success': True,
                'workflow_name': workflow.name,
                'workflow_type': workflow.workflow_type,
                'test_object_type': workflow.object_type,
                'test_object': str(test_obj),
                'mapped_parameters': mapped_params,
                'message': 'Workflow mapping test successful. These are the parameters that would be sent.'
            })

        except Exception as e:
            logger.exception(f'Error testing workflow: {str(e)}')
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='execute')
    def execute_workflow(self, request, pk=None):
        """
        Execute a workflow against a specific object.
        
        Expected payload:
        {
            "object_type": "device|incident|event",
            "object_id": 123
        }
        """
        try:
            workflow = self.get_object()

            # Check if workflow execution is enabled globally
            if not external_workflow_config.WORKFLOW_EXECUTION_ENABLED:
                return Response({
                    'success': False,
                    'error': 'Workflow execution is disabled in plugin configuration.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate workflow is enabled
            if not workflow.enabled:
                return Response({
                    'success': False,
                    'error': 'This workflow is disabled and cannot be executed.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get object type and ID from request
            object_type = request.data.get('object_type')
            object_id = request.data.get('object_id')

            if not object_type or not object_id:
                return Response({
                    'success': False,
                    'error': 'object_type and object_id are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate object type matches workflow configuration
            if object_type != workflow.object_type:
                return Response({
                    'success': False,
                    'error': f'This workflow is configured for {workflow.object_type} objects, not {object_type}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get the source object and its content type
            source_obj = None
            content_type = None
            if object_type == 'device':
                source_obj = Device.objects.filter(pk=object_id).first()
                content_type = ContentType.objects.get_for_model(Device)
            elif object_type == 'incident':
                source_obj = Incident.objects.filter(pk=object_id).first()
                content_type = ContentType.objects.get_for_model(Incident)
            elif object_type == 'event':
                source_obj = Event.objects.filter(pk=object_id).first()
                content_type = ContentType.objects.get_for_model(Event)

            if not source_obj:
                return Response({
                    'success': False,
                    'error': f'{object_type.title()} with ID {object_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Generate mapped parameters
            mapped_params = workflow.get_mapped_parameters(source_obj)

            # Create execution log entry
            execution_log = WorkflowExecution.objects.create(
                workflow=workflow,
                user=request.user,
                content_type=content_type,
                object_id=source_obj.pk,
                status=WorkflowExecutionStatus.RUNNING,
                parameters_sent=mapped_params
            )

            # Execute based on workflow type
            execution_result = None
            
            try:
                if workflow.workflow_type == 'aap':
                    # Execute AAP workflow/job
                    execution_result = self._execute_aap_workflow(workflow, mapped_params, source_obj)
                elif workflow.workflow_type == 'n8n':
                    # Execute N8N webhook
                    execution_result = self._execute_n8n_webhook(workflow, mapped_params, source_obj)
                else:
                    execution_log.status = WorkflowExecutionStatus.FAILED
                    execution_log.error_message = f'Unknown workflow type: {workflow.workflow_type}'
                    execution_log.completed_at = timezone.now()
                    execution_log.save()
                    return Response({
                        'success': False,
                        'error': f'Unknown workflow type: {workflow.workflow_type}'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Update execution log with result
                execution_log.status = WorkflowExecutionStatus.SUCCESS if execution_result.get('success') else WorkflowExecutionStatus.FAILED
                execution_log.execution_id = execution_result.get('execution_id')
                execution_log.response_data = execution_result.get('details', {})
                execution_log.error_message = execution_result.get('error_message') if not execution_result.get('success') else None
                execution_log.completed_at = timezone.now()
                execution_log.save()

            except Exception as exec_error:
                execution_log.status = WorkflowExecutionStatus.FAILED
                execution_log.error_message = str(exec_error)
                execution_log.completed_at = timezone.now()
                execution_log.save()
                raise

            logger.info(f'Executed workflow {workflow.name} for {object_type} {object_id} by user {request.user} - Execution ID: {execution_log.pk}')

            return Response({
                'success': execution_result.get('success', False),
                'message': execution_result.get('message', 'Workflow executed'),
                'execution_id': execution_result.get('execution_id'),
                'execution_log_id': execution_log.pk,
                'parameters_sent': mapped_params,
                'details': execution_result.get('details', {})
            }, status=status.HTTP_200_OK if execution_result.get('success') else status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.exception(f'Error executing workflow: {str(e)}')
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _execute_aap_workflow(self, workflow, params, source_obj):
        """Execute an AAP workflow or job template"""
        from requests.auth import HTTPBasicAuth
        
        try:
            # Get AAP configuration
            aap_auth_type = external_workflow_config.AAP_AUTH_TYPE
            aap_token = external_workflow_config.AAP_TOKEN
            aap_username = external_workflow_config.AAP_USERNAME
            aap_password = external_workflow_config.AAP_PASSWORD
            verify_ssl = external_workflow_config.AAP_VERIFY_SSL
            timeout = external_workflow_config.AAP_TIMEOUT

            # Use workflow-specific URL or fall back to default
            aap_url = workflow.aap_url or external_workflow_config.AAP_DEFAULT_URL
            
            if not aap_url:
                return {
                    'success': False,
                    'message': 'AAP URL not configured. Set aap_url on the workflow or aap_default_url in plugin config.',
                    'error_message': 'AAP URL not configured',
                    'details': {}
                }

            # Determine the API endpoint based on resource type
            if workflow.aap_resource_type == 'workflow':
                endpoint = f"{aap_url.rstrip('/')}/api/v2/workflow_job_templates/{workflow.aap_resource_id}/launch/"
            else:  # job_template
                endpoint = f"{aap_url.rstrip('/')}/api/v2/job_templates/{workflow.aap_resource_id}/launch/"

            # Build payload
            payload = {}
            
            # Add extra_vars if present in mapped params
            if 'extra_vars' in params:
                payload['extra_vars'] = params['extra_vars']
            elif params:
                # If no explicit extra_vars, use all params as extra_vars
                payload['extra_vars'] = params
            
            # Add limit if present
            if 'limit' in params:
                payload['limit'] = params['limit']

            # Log the execution attempt (without sensitive data)
            logger.info(f'Executing AAP {workflow.aap_resource_type} {workflow.aap_resource_id} at {aap_url} using {aap_auth_type} auth')

            # Determine authentication method
            auth = None
            headers = {'Content-Type': 'application/json'}
            
            if aap_auth_type == 'basic':
                # Basic authentication
                if not aap_username or not aap_password:
                    logger.warning('AAP basic auth credentials not configured - running in simulation mode')
                    return {
                        'success': True,
                        'message': f'AAP {workflow.get_aap_resource_type_display()} triggered successfully (simulation mode - no credentials configured)',
                        'execution_id': f'aap-sim-{workflow.aap_resource_id}-{source_obj.pk}',
                        'details': {
                            'note': 'AAP basic auth credentials not configured. Set aap_username and aap_password in plugin settings.',
                            'endpoint': endpoint,
                            'payload': payload,
                            'resource_type': workflow.aap_resource_type,
                            'resource_id': workflow.aap_resource_id,
                            'auth_type': 'basic'
                        }
                    }
                auth = HTTPBasicAuth(aap_username, aap_password)
            else:
                # Token authentication (default)
                if not aap_token:
                    logger.warning('AAP token not configured - running in simulation mode')
                    return {
                        'success': True,
                        'message': f'AAP {workflow.get_aap_resource_type_display()} triggered successfully (simulation mode - no token configured)',
                        'execution_id': f'aap-sim-{workflow.aap_resource_id}-{source_obj.pk}',
                        'details': {
                            'note': 'AAP token not configured in plugin settings. Set aap_token to enable actual execution.',
                            'endpoint': endpoint,
                            'payload': payload,
                            'resource_type': workflow.aap_resource_type,
                            'resource_id': workflow.aap_resource_id,
                            'auth_type': 'token'
                        }
                    }
                headers['Authorization'] = f'Bearer {aap_token}'

            # Make the actual API call
            response = http_requests.post(
                endpoint,
                json=payload,
                headers=headers,
                auth=auth,
                verify=verify_ssl,
                timeout=timeout
            )
            
            if response.status_code in [200, 201, 202]:
                data = response.json()
                job_id = data.get('id') or data.get('job') or data.get('workflow_job')
                return {
                    'success': True,
                    'message': f'AAP {workflow.get_aap_resource_type_display()} triggered successfully',
                    'execution_id': str(job_id) if job_id else None,
                    'details': {
                        'job_id': job_id,
                        'status': data.get('status'),
                        'url': data.get('url'),
                        'created': data.get('created'),
                        'response_status_code': response.status_code
                    }
                }
            else:
                error_detail = response.text[:500] if response.text else 'No error details'
                logger.error(f'AAP API error: {response.status_code} - {error_detail}')
                return {
                    'success': False,
                    'message': f'AAP API returned error: {response.status_code}',
                    'error_message': error_detail,
                    'details': {
                        'status_code': response.status_code,
                        'error': error_detail
                    }
                }

        except http_requests.exceptions.Timeout:
            logger.exception('AAP request timeout')
            return {
                'success': False,
                'message': f'AAP request timed out after {timeout} seconds',
                'error_message': 'Request timeout',
                'details': {'timeout': timeout}
            }
        except http_requests.exceptions.ConnectionError as e:
            logger.exception(f'AAP connection error: {str(e)}')
            return {
                'success': False,
                'message': f'Failed to connect to AAP: {str(e)}',
                'error_message': str(e),
                'details': {'error': str(e)}
            }
        except Exception as e:
            logger.exception(f'AAP execution error: {str(e)}')
            return {
                'success': False,
                'message': f'Failed to execute AAP workflow: {str(e)}',
                'error_message': str(e),
                'details': {'error': str(e)}
            }

    def _execute_n8n_webhook(self, workflow, params, source_obj):
        """Execute an N8N webhook"""
        try:
            # Get N8N configuration
            n8n_api_key = external_workflow_config.N8N_API_KEY
            verify_ssl = external_workflow_config.N8N_VERIFY_SSL
            timeout = external_workflow_config.N8N_TIMEOUT
            
            webhook_url = workflow.n8n_webhook_url
            
            if not webhook_url:
                return {
                    'success': False,
                    'message': 'N8N webhook URL not configured on the workflow.',
                    'error_message': 'Webhook URL not configured',
                    'details': {}
                }

            # Build payload with object information
            payload = {
                'source': 'netbox',
                'object_type': workflow.object_type,
                'object_id': source_obj.pk,
                'object_name': str(source_obj),
                'workflow_name': workflow.name,
                **params
            }

            # Log the execution attempt
            logger.info(f'Executing N8N webhook for workflow {workflow.name}')

            # Build headers
            headers = {'Content-Type': 'application/json'}
            
            # Add API key if configured (for authenticated webhooks)
            if n8n_api_key:
                headers['X-N8N-API-KEY'] = n8n_api_key

            # Make the actual API call
            response = http_requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                verify=verify_ssl,
                timeout=timeout
            )
            
            if response.status_code in [200, 201, 202]:
                # Try to parse response as JSON, fall back to text
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = {'response_text': response.text[:500] if response.text else 'No response body'}
                
                execution_id = response.headers.get('X-Execution-Id') or response.headers.get('X-N8N-Execution-Id')
                
                return {
                    'success': True,
                    'message': 'N8N webhook triggered successfully',
                    'execution_id': execution_id,
                    'details': {
                        'response_status_code': response.status_code,
                        'execution_id': execution_id,
                        'response': response_data
                    }
                }
            else:
                error_detail = response.text[:500] if response.text else 'No error details'
                logger.error(f'N8N webhook error: {response.status_code} - {error_detail}')
                return {
                    'success': False,
                    'message': f'N8N webhook returned error: {response.status_code}',
                    'error_message': error_detail,
                    'details': {
                        'status_code': response.status_code,
                        'error': error_detail
                    }
                }

        except http_requests.exceptions.Timeout:
            logger.exception('N8N request timeout')
            return {
                'success': False,
                'message': f'N8N request timed out after {timeout} seconds',
                'error_message': 'Request timeout',
                'details': {'timeout': timeout}
            }
        except http_requests.exceptions.ConnectionError as e:
            logger.exception(f'N8N connection error: {str(e)}')
            return {
                'success': False,
                'message': f'Failed to connect to N8N: {str(e)}',
                'error_message': str(e),
                'details': {'error': str(e)}
            }
        except Exception as e:
            logger.exception(f'N8N execution error: {str(e)}')
            return {
                'success': False,
                'message': f'Failed to execute N8N webhook: {str(e)}',
                'error_message': str(e),
                'details': {'error': str(e)}
            }


class WorkflowExecutionViewSet(ModelViewSet):
    """
    API endpoint for viewing WorkflowExecution history.
    Read-only - executions are created via the execute endpoint on ExternalWorkflowViewSet.
    """
    queryset = WorkflowExecution.objects.select_related(
        'workflow', 'user', 'content_type'
    ).all()
    serializer_class = WorkflowExecutionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'head', 'options']  # Read-only

    def get_queryset(self):
        """
        Filter workflow executions by various parameters.
        """
        queryset = super().get_queryset()
        workflow_id = self.request.query_params.get('workflow')
        user_id = self.request.query_params.get('user')
        status_filter = self.request.query_params.get('status')
        object_type = self.request.query_params.get('object_type')
        object_id = self.request.query_params.get('object_id')

        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if object_type:
            queryset = queryset.filter(content_type__model=object_type)
        if object_id:
            queryset = queryset.filter(object_id=object_id)

        return queryset.order_by('-started_at')

    @action(detail=False, methods=['get'], url_path='my-executions')
    def my_executions(self, request):
        """
        Get executions performed by the current user.
        """
        queryset = self.get_queryset().filter(user=request.user)[:50]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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