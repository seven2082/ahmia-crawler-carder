from django.core.management.base import BaseCommand

from profiles.services import get_service


class Command(BaseCommand):
    help = 'Sync profiles from Elasticsearch crawl data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating'
        )

    def handle(self, *args, **options):
        sync_service = get_service('sync_service')

        if options['dry_run']:
            self.stdout.write('DRY RUN - no changes will be made')

        self.stdout.write('Syncing profiles from Elasticsearch...')

        try:
            result = sync_service.sync_all_profiles()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Sync complete: {result['created']} created, "
                    f"{result.get('merged', 0)} merged, "
                    f"{result['skipped']} skipped, "
                    f"{result['total_domains']} total domains"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Sync failed: {e}')
            )
            raise
