from django.core.management.base import BaseCommand

from profiles.services import get_service


class Command(BaseCommand):
    help = 'Update cached stats for all profiles from Elasticsearch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--profile',
            type=str,
            help='Update only a specific profile by slug'
        )

    def handle(self, *args, **options):
        sync_service = get_service('sync_service')

        if options['profile']:
            from profiles.models import OnionProfile
            try:
                profile = OnionProfile.objects.get(slug=options['profile'])
                sync_service.update_profile_stats(profile)
                self.stdout.write(
                    self.style.SUCCESS(f"Updated stats for {profile.slug}")
                )
            except OnionProfile.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Profile not found: {options['profile']}")
                )
                return
        else:
            self.stdout.write('Updating stats for all profiles...')
            count = sync_service.update_all_stats()
            self.stdout.write(
                self.style.SUCCESS(f"Updated {count} profiles")
            )
