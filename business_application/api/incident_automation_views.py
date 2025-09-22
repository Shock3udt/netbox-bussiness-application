from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from django.utils import timezone
from datetime import timedelta
import logging

from business_application.models import Event, Incident, EventStatus
from business_application.services.incident_service import (
    IncidentAutoCreationService, process_unprocessed_events, process_event_for_incident
)

logger = logging.getLogger(__name__)


class IncidentAutomationViewSet(ViewSet):
    """
    API endpoints for controlling incident automation features.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def process_event(self, request):
        """
        Manually trigger incident processing for a specific event.

        POST /api/plugins/business-application/incident-automation/process-event/
        Body: {"event_id": 123}
        """
        event_id = request.data.get('event_id')
        if not event_id:
            return Response(
                {'error': 'event_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response(
                {'error': f'Event {event_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            service = IncidentAutoCreationService()
            incident = service.process_incoming_event(event)

            if incident:
                return Response({
                    'success': True,
                    'message': f'Event {event_id} processed successfully',
                    'incident_id': incident.id,
                    'incident_title': incident.title,
                    'action': 'created' if incident.events.count() == 1 else 'updated'
                })
            else:
                return Response({
                    'success': True,
                    'message': f'Event {event_id} processed but no incident action taken',
                    'incident_id': None,
                    'action': 'none'
                })

        except Exception as e:
            logger.error(f"API error processing event {event_id}: {e}", exc_info=True)
            return Response(
                {'error': f'Error processing event: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def process_unprocessed(self, request):
        """
        Process all unprocessed events for incident creation.

        POST /api/plugins/business-application/incident-automation/process-unprocessed/
        Body: {"hours": 24} (optional, defaults to 24)
        """
        hours = request.data.get('hours', 24)

        try:
            hours = int(hours)
            if hours < 1 or hours > 168:  # Max 1 week
                return Response(
                    {'error': 'hours must be between 1 and 168'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'hours must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get count before processing
            cutoff_time = timezone.now() - timedelta(hours=hours)
            unprocessed_count = Event.objects.filter(
                incidents__isnull=True,
                status=EventStatus.TRIGGERED,
                created_at__gte=cutoff_time
            ).count()

            processed_count = process_unprocessed_events()

            return Response({
                'success': True,
                'message': f'Processed {processed_count} of {unprocessed_count} unprocessed events',
                'unprocessed_events_found': unprocessed_count,
                'events_processed': processed_count,
                'time_window_hours': hours
            })

        except Exception as e:
            logger.error(f"API error processing unprocessed events: {e}", exc_info=True)
            return Response(
                {'error': f'Error processing events: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get status information about incident automation.

        GET /api/plugins/business-application/incident-automation/status/
        """
        try:
            # Get recent statistics
            now = timezone.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            stats = {
                'automation_enabled': True,  # You can add a setting for this
                'events_last_24h': Event.objects.filter(created_at__gte=last_24h).count(),
                'incidents_last_24h': Incident.objects.filter(created_at__gte=last_24h).count(),
                'unprocessed_events': Event.objects.filter(
                    incidents__isnull=True,
                    status=EventStatus.TRIGGERED,
                    created_at__gte=last_24h
                ).count(),
                'open_incidents': Incident.objects.filter(
                    status__in=['new', 'investigating', 'identified']
                ).count(),
                'recent_incident_trend': {
                    'last_24h': Incident.objects.filter(created_at__gte=last_24h).count(),
                    'previous_24h': Incident.objects.filter(
                        created_at__gte=last_24h - timedelta(hours=24),
                        created_at__lt=last_24h
                    ).count(),
                }
            }

            return Response(stats)

        except Exception as e:
            logger.error(f"API error getting status: {e}", exc_info=True)
            return Response(
                {'error': f'Error getting status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def force_correlate(self, request):
        """
        Force re-correlation of incidents by reprocessing events.

        POST /api/plugins/business-application/incident-automation/force-correlate/
        Body: {"hours": 24, "incident_ids": [1, 2, 3]} (optional filters)
        """
        hours = request.data.get('hours', 24)
        incident_ids = request.data.get('incident_ids', [])

        try:
            hours = int(hours)
            if hours < 1 or hours > 168:
                return Response(
                    {'error': 'hours must be between 1 and 168'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'hours must be a valid integer'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cutoff_time = timezone.now() - timedelta(hours=hours)

            # Get events to reprocess
            events_query = Event.objects.filter(
                status=EventStatus.TRIGGERED,
                created_at__gte=cutoff_time
            )

            if incident_ids:
                # Only reprocess events from specific incidents
                events_query = events_query.filter(incidents__id__in=incident_ids)

            events = events_query.distinct().order_by('created_at')
            total_events = events.count()

            # Clear existing incident associations for these events
            for event in events:
                event.incidents.clear()

            # Reprocess all events
            service = IncidentAutoCreationService()
            processed_count = 0

            for event in events:
                try:
                    incident = service.process_incoming_event(event)
                    if incident:
                        processed_count += 1
                except Exception as e:
                    logger.warning(f"Error reprocessing event {event.id}: {e}")

            return Response({
                'success': True,
                'message': f'Force correlation completed',
                'total_events_reprocessed': total_events,
                'events_successfully_processed': processed_count,
                'time_window_hours': hours
            })

        except Exception as e:
            logger.error(f"API error in force correlate: {e}", exc_info=True)
            return Response(
                {'error': f'Error in force correlation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def correlation_analysis(self, request):
        """
        Analyze correlation patterns for debugging and optimization.

        GET /api/plugins/business-application/incident-automation/correlation-analysis/
        """
        try:
            hours = int(request.query_params.get('hours', 24))
            cutoff_time = timezone.now() - timedelta(hours=hours)

            # Get recent incidents with their events
            recent_incidents = Incident.objects.filter(
                created_at__gte=cutoff_time
            ).prefetch_related('events', 'affected_services')

            analysis = {
                'total_incidents': recent_incidents.count(),
                'incidents_by_service_count': {},
                'events_per_incident': {},
                'correlation_patterns': [],
                'unprocessed_events': Event.objects.filter(
                    incidents__isnull=True,
                    status=EventStatus.TRIGGERED,
                    created_at__gte=cutoff_time
                ).count()
            }

            for incident in recent_incidents:
                service_count = incident.affected_services.count()
                event_count = incident.events.count()

                # Count incidents by number of affected services
                if service_count in analysis['incidents_by_service_count']:
                    analysis['incidents_by_service_count'][service_count] += 1
                else:
                    analysis['incidents_by_service_count'][service_count] = 1

                # Count events per incident
                if event_count in analysis['events_per_incident']:
                    analysis['events_per_incident'][event_count] += 1
                else:
                    analysis['events_per_incident'][event_count] = 1

                # Analyze correlation patterns
                if event_count > 1:
                    analysis['correlation_patterns'].append({
                        'incident_id': incident.id,
                        'title': incident.title,
                        'event_count': event_count,
                        'service_count': service_count,
                        'duration_minutes': (
                                                    (incident.resolved_at or timezone.now()) - incident.created_at
                                            ).total_seconds() / 60
                    })

            return Response(analysis)

        except Exception as e:
            logger.error(f"API error in correlation analysis: {e}", exc_info=True)
            return Response(
                {'error': f'Error in correlation analysis: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )