from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import logging

from business_application.models import Event, Incident, EventStatus
from business_application.services.incident_service import (
    IncidentAutoCreationService, process_unprocessed_events
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process events for automatic incident creation and management'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['process', 'reprocess', 'cleanup'],
            default='process',
            help='Processing mode: process unprocessed events, reprocess all recent events, or cleanup old incidents'
        )

        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Number of hours to look back for events (default: 24)'
        )

        parser.add_argument(
            '--event-id',
            type=int,
            help='Process a specific event by ID'
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes'
        )

        parser.add_argument(
            '--force-correlate',
            action='store_true',
            help='Force re-correlation of existing incidents'
        )

    def handle(self, *args, **options):
        mode = options['mode']
        hours = options['hours']
        event_id = options['event_id']
        dry_run = options['dry_run']
        force_correlate = options['force_correlate']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        try:
            if event_id:
                self._process_specific_event(event_id, dry_run)
            elif mode == 'process':
                self._process_unprocessed_events(hours, dry_run)
            elif mode == 'reprocess':
                self._reprocess_events(hours, dry_run, force_correlate)
            elif mode == 'cleanup':
                self._cleanup_incidents(hours, dry_run)

        except Exception as e:
            raise CommandError(f'Error during processing: {e}')

    def _process_specific_event(self, event_id, dry_run):
        """Process a specific event for incident creation."""
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            raise CommandError(f'Event {event_id} not found')

        self.stdout.write(f'Processing event {event_id}: {event.message}')

        if dry_run:
            self.stdout.write('Would process this event for incident creation')
            return

        service = IncidentAutoCreationService()
        incident = service.process_incoming_event(event)

        if incident:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Event {event_id} processed - Incident {incident.id}: {incident.title}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'No incident action taken for event {event_id}')
            )

    def _process_unprocessed_events(self, hours, dry_run):
        """Process events that haven't been assigned to incidents."""
        cutoff_time = timezone.now() - timedelta(hours=hours)

        unprocessed_events = Event.objects.filter(
            incidents__isnull=True,
            status=EventStatus.TRIGGERED,
            created_at__gte=cutoff_time
        ).order_by('created_at')

        total_events = unprocessed_events.count()
        self.stdout.write(f'Found {total_events} unprocessed events in the last {hours} hours')

        if dry_run:
            for event in unprocessed_events[:10]:  # Show first 10
                self.stdout.write(f'Would process: {event.id} - {event.message[:50]}...')
            if total_events > 10:
                self.stdout.write(f'... and {total_events - 10} more events')
            return

        processed_count = process_unprocessed_events()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully processed {processed_count} events')
        )

    def _reprocess_events(self, hours, dry_run, force_correlate):
        """Reprocess all events in the time window, potentially updating correlations."""
        cutoff_time = timezone.now() - timedelta(hours=hours)

        events = Event.objects.filter(
            status=EventStatus.TRIGGERED,
            created_at__gte=cutoff_time
        ).order_by('created_at')

        total_events = events.count()
        self.stdout.write(f'Found {total_events} events to reprocess in the last {hours} hours')

        if dry_run:
            self.stdout.write('Would reprocess all these events for better correlation')
            return

        service = IncidentAutoCreationService()
        processed_count = 0
        updated_count = 0

        for event in events:
            try:
                # If force correlate, remove from existing incidents first
                if force_correlate:
                    event.incidents.clear()

                # Skip if already properly correlated (unless forcing)
                if not force_correlate and event.incidents.exists():
                    continue

                incident = service.process_incoming_event(event)
                if incident:
                    processed_count += 1
                    if event.incidents.count() > 1:  # Event moved to different incident
                        updated_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing event {event.id}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Reprocessed {processed_count} events, updated correlation for {updated_count} events'
            )
        )

    def _cleanup_incidents(self, hours, dry_run):
        """Clean up old resolved incidents and consolidate similar ones."""
        cutoff_time = timezone.now() - timedelta(hours=hours)

        # Find resolved incidents older than the cutoff
        old_resolved_incidents = Incident.objects.filter(
            status__in=['resolved', 'closed'],
            resolved_at__lt=cutoff_time
        )

        # Find incidents with no events (orphaned)
        orphaned_incidents = Incident.objects.filter(
            events__isnull=True
        )

        self.stdout.write(
            f'Found {old_resolved_incidents.count()} old resolved incidents '
            f'and {orphaned_incidents.count()} orphaned incidents'
        )

        if dry_run:
            self.stdout.write('Would clean up these incidents')
            return

        # Archive old incidents (you might want to move to archive table instead of delete)
        deleted_old = old_resolved_incidents.count()
        if deleted_old > 0:
            old_resolved_incidents.delete()
            self.stdout.write(f'Archived {deleted_old} old resolved incidents')

        # Remove orphaned incidents
        deleted_orphaned = orphaned_incidents.count()
        if deleted_orphaned > 0:
            orphaned_incidents.delete()
            self.stdout.write(f'Removed {deleted_orphaned} orphaned incidents')

        self.stdout.write(
            self.style.SUCCESS(f'Cleanup completed: {deleted_old + deleted_orphaned} incidents processed')
        )