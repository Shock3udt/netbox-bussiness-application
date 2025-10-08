from django.core.management.base import BaseCommand
from django.db import transaction
from business_application.models import Incident, Event
from business_application.utils.correlation import AlertCorrelationEngine
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Recalculate affected_services for existing incidents using downstream dependency logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually changing it',
        )
        parser.add_argument(
            '--incident-id',
            type=int,
            help='Process only specific incident ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        incident_id = options.get('incident_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        if incident_id:
            incidents = Incident.objects.filter(id=incident_id)
            if not incidents.exists():
                self.stdout.write(self.style.ERROR(f'Incident {incident_id} not found'))
                return
        else:
            incidents = Incident.objects.all()

        total = incidents.count()
        self.stdout.write(f'Processing {total} incident(s)...\n')

        correlation_engine = AlertCorrelationEngine()
        updated_count = 0
        unchanged_count = 0
        error_count = 0

        for incident in incidents:
            try:
                current_services = set(incident.affected_services.all())

                new_services = set()

                for event in incident.events.all():
                    if not event.obj:
                        continue

                    services = correlation_engine._find_technical_services(event.obj)
                    new_services.update(services)

                added_services = new_services - current_services
                removed_services = current_services - new_services

                if added_services or removed_services:
                    self.stdout.write(
                        self.style.WARNING(f'\nIncident {incident.id}: {incident.title}')
                    )
                    self.stdout.write(f'  Current services: {len(current_services)}')

                    if added_services:
                        self.stdout.write(
                            self.style.SUCCESS(f'  + Adding {len(added_services)} services:')
                        )
                        for service in added_services:
                            self.stdout.write(f'    + {service.name}')

                    if removed_services:
                        self.stdout.write(
                            self.style.ERROR(f'  - Removing {len(removed_services)} services:')
                        )
                        for service in removed_services:
                            self.stdout.write(f'    - {service.name}')

                    self.stdout.write(f'  New total: {len(new_services)}')

                    if not dry_run:
                        with transaction.atomic():
                            incident.affected_services.set(new_services)
                            self.stdout.write(
                                self.style.SUCCESS(f'  ✓ Updated incident {incident.id}')
                            )

                    updated_count += 1
                else:
                    unchanged_count += 1
                    if options['verbosity'] >= 2:
                        self.stdout.write(f'Incident {incident.id}: No changes needed')

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing incident {incident.id}: {str(e)}')
                )
                logger.exception(f'Error recalculating services for incident {incident.id}')

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\nSummary:'))
        self.stdout.write(f'  Total incidents processed: {total}')
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Unchanged: {unchanged_count}')
        if error_count:
            self.stdout.write(self.style.ERROR(f'  Errors: {error_count}'))

        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nThis was a DRY RUN. Run without --dry-run to apply changes.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✓ All changes have been applied!')
            )