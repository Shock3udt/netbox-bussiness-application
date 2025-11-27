# business_application/api/pagerduty_views.py
"""
PagerDuty API views for manually triggering PagerDuty events.
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
import logging

from business_application.models import Event, Incident
from business_application.utils.pagerduty import (
    PagerDutyClient,
    PagerDutyError,
    pagerduty_config,
    send_event_to_pagerduty,
    send_incident_to_pagerduty,
    PagerDutyEventAction,
)

logger = logging.getLogger(__name__)


class PagerDutyViewSet(ViewSet):
    """
    API endpoints for PagerDuty integration.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get PagerDuty integration status.

        GET /api/plugins/business-application/pagerduty/status/
        """
        return Response({
            'enabled': pagerduty_config.enabled,
            'configured': bool(pagerduty_config.routing_key),
            'send_on_event_create': pagerduty_config.send_on_event_create,
            'send_on_incident_create': pagerduty_config.send_on_incident_create,
            'send_on_incident_update': pagerduty_config.send_on_incident_update,
            'auto_resolve': pagerduty_config.auto_resolve,
            'source': pagerduty_config.source,
            'component': pagerduty_config.component,
            'group': pagerduty_config.group,
        })

    @action(detail=False, methods=['post'], url_path='test')
    def test_connection(self, request):
        """
        Test PagerDuty connection by sending a test event.

        POST /api/plugins/business-application/pagerduty/test/
        """
        if not pagerduty_config.enabled:
            return Response(
                {'error': 'PagerDuty integration is not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        client = PagerDutyClient()

        if not client.is_configured:
            return Response(
                {'error': 'PagerDuty is not properly configured (missing routing key)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = client.trigger(
                summary="NetBox PagerDuty Integration Test",
                severity='info',
                dedup_key='netbox-test-event',
                component='netbox-integration-test',
                event_class='test',
                custom_details={
                    'test': True,
                    'triggered_by': request.user.username,
                    'message': 'This is a test event from NetBox'
                }
            )

            resolve_result = client.resolve(dedup_key='netbox-test-event')

            return Response({
                'success': True,
                'message': 'Test event sent and resolved successfully',
                'trigger_result': result,
                'resolve_result': resolve_result,
            })

        except PagerDutyError as e:
            return Response(
                {'error': f'PagerDuty API error: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.exception(f"Error testing PagerDuty connection: {e}")
            return Response(
                {'error': f'Unexpected error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='send-event')
    def send_event(self, request):
        """
        Manually send a NetBox Event to PagerDuty.

        POST /api/plugins/business-application/pagerduty/send-event/
        Body: {"event_id": 123}
        """
        event_id = request.data.get('event_id')

        if not event_id:
            return Response(
                {'error': 'event_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not pagerduty_config.enabled:
            return Response(
                {'error': 'PagerDuty integration is not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response(
                {'error': f'Event {event_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            result = send_event_to_pagerduty(event)

            if result:
                return Response({
                    'success': True,
                    'message': f'Event {event_id} sent to PagerDuty',
                    'result': result,
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Event was not sent (check configuration)',
                })

        except PagerDutyError as e:
            return Response(
                {'error': f'PagerDuty API error: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.exception(f"Error sending event to PagerDuty: {e}")
            return Response(
                {'error': f'Unexpected error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='send-incident')
    def send_incident(self, request):
        """
        Manually send a NetBox Incident to PagerDuty.

        POST /api/plugins/business-application/pagerduty/send-incident/
        Body: {"incident_id": 123, "action": "trigger|acknowledge|resolve"}
        """
        incident_id = request.data.get('incident_id')
        action = request.data.get('action', PagerDutyEventAction.TRIGGER)

        if not incident_id:
            return Response(
                {'error': 'incident_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action not in [PagerDutyEventAction.TRIGGER,
                          PagerDutyEventAction.ACKNOWLEDGE,
                          PagerDutyEventAction.RESOLVE]:
            return Response(
                {'error': f'Invalid action: {action}. Must be trigger, acknowledge, or resolve'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not pagerduty_config.enabled:
            return Response(
                {'error': 'PagerDuty integration is not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            incident = Incident.objects.get(pk=incident_id)
        except Incident.DoesNotExist:
            return Response(
                {'error': f'Incident {incident_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            result = send_incident_to_pagerduty(incident, action=action)

            if result:
                return Response({
                    'success': True,
                    'message': f'Incident {incident_id} sent to PagerDuty (action: {action})',
                    'result': result,
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Incident was not sent (check configuration)',
                })

        except PagerDutyError as e:
            return Response(
                {'error': f'PagerDuty API error: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.exception(f"Error sending incident to PagerDuty: {e}")
            return Response(
                {'error': f'Unexpected error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='resolve-event')
    def resolve_event(self, request):
        """
        Resolve a PagerDuty event by dedup_key.

        POST /api/plugins/business-application/pagerduty/resolve-event/
        Body: {"dedup_key": "netbox-event-xxx"} or {"event_id": 123}
        """
        dedup_key = request.data.get('dedup_key')
        event_id = request.data.get('event_id')

        if not dedup_key and not event_id:
            return Response(
                {'error': 'Either dedup_key or event_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not pagerduty_config.enabled:
            return Response(
                {'error': 'PagerDuty integration is not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if event_id:
            try:
                event = Event.objects.get(pk=event_id)
                dedup_key = f"netbox-event-{event.dedup_id}"
            except Event.DoesNotExist:
                return Response(
                    {'error': f'Event {event_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        try:
            client = PagerDutyClient()
            result = client.resolve(dedup_key=dedup_key)

            return Response({
                'success': True,
                'message': f'PagerDuty event resolved',
                'dedup_key': dedup_key,
                'result': result,
            })

        except PagerDutyError as e:
            return Response(
                {'error': f'PagerDuty API error: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.exception(f"Error resolving PagerDuty event: {e}")
            return Response(
                {'error': f'Unexpected error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='trigger-custom')
    def trigger_custom(self, request):
        """
        Trigger a custom PagerDuty event.

        POST /api/plugins/business-application/pagerduty/trigger-custom/
        Body: {
            "summary": "Event summary",
            "severity": "critical|error|warning|info",
            "source": "optional source",
            "dedup_key": "optional dedup key",
            "component": "optional component",
            "group": "optional group",
            "custom_details": {}
        }
        """
        if not pagerduty_config.enabled:
            return Response(
                {'error': 'PagerDuty integration is not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        summary = request.data.get('summary')
        if not summary:
            return Response(
                {'error': 'summary is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        severity = request.data.get('severity', 'warning')
        valid_severities = ['critical', 'error', 'warning', 'info']
        if severity not in valid_severities:
            return Response(
                {'error': f'Invalid severity. Must be one of: {valid_severities}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = PagerDutyClient()

            result = client.trigger(
                summary=summary,
                severity=severity,
                source=request.data.get('source'),
                dedup_key=request.data.get('dedup_key'),
                component=request.data.get('component'),
                group=request.data.get('group'),
                event_class=request.data.get('event_class', 'custom'),
                custom_details=request.data.get('custom_details', {}),
            )

            return Response({
                'success': True,
                'message': 'Custom PagerDuty event triggered',
                'result': result,
            })

        except PagerDutyError as e:
            return Response(
                {'error': f'PagerDuty API error: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.exception(f"Error triggering custom PagerDuty event: {e}")
            return Response(
                {'error': f'Unexpected error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='bulk-send-events')
    def bulk_send_events(self, request):
        """
        Send multiple NetBox Events to PagerDuty.

        POST /api/plugins/business-application/pagerduty/bulk-send-events/
        Body: {"event_ids": [1, 2, 3]}
        """
        event_ids = request.data.get('event_ids', [])

        if not event_ids:
            return Response(
                {'error': 'event_ids is required and must be a non-empty list'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not pagerduty_config.enabled:
            return Response(
                {'error': 'PagerDuty integration is not enabled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = {
            'success': [],
            'failed': [],
            'not_found': [],
        }

        for event_id in event_ids:
            try:
                event = Event.objects.get(pk=event_id)
                result = send_event_to_pagerduty(event)

                if result:
                    results['success'].append({
                        'event_id': event_id,
                        'status': result.get('status', 'unknown')
                    })
                else:
                    results['failed'].append({
                        'event_id': event_id,
                        'reason': 'Not sent (check configuration)'
                    })

            except Event.DoesNotExist:
                results['not_found'].append(event_id)
            except Exception as e:
                results['failed'].append({
                    'event_id': event_id,
                    'reason': str(e)
                })

        return Response({
            'total_requested': len(event_ids),
            'success_count': len(results['success']),
            'failed_count': len(results['failed']),
            'not_found_count': len(results['not_found']),
            'results': results,
        })