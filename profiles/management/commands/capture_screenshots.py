from django.core.management.base import BaseCommand
from django.utils import timezone

from profiles.models import OnionProfile
from profiles.services import get_service


class Command(BaseCommand):
    help = 'Capture screenshots of online .onion sites'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum profiles to screenshot (default: 50)'
        )
        parser.add_argument(
            '--only-missing',
            action='store_true',
            help='Only screenshot profiles without existing screenshots'
        )
        parser.add_argument(
            '--only-online',
            action='store_true',
            default=True,
            help='Only screenshot profiles marked as online (default: True)'
        )

    def handle(self, *args, **options):
        screenshot_svc = get_service('screenshot_service')
        limit = options['limit']
        only_missing = options['only_missing']
        only_online = options['only_online']

        profiles = OnionProfile.objects.filter(status='active')

        if only_online:
            profiles = profiles.filter(is_online=True)

        if only_missing:
            profiles = profiles.filter(screenshot='')

        profiles = profiles.order_by('-last_checked')[:limit]
        profiles = list(profiles)

        self.stdout.write(f'Capturing screenshots for {len(profiles)} profiles...')

        captured = 0
        failed = 0

        for i, profile in enumerate(profiles):
            self.stdout.write(f'  [{i+1}/{len(profiles)}] {profile.current_domain[:30]}...', ending='')

            try:
                screenshot = screenshot_svc.capture(profile.current_domain)

                if screenshot:
                    profile.screenshot = screenshot
                    profile.save(update_fields=['screenshot', 'updated_at'])
                    captured += 1
                    self.stdout.write(self.style.SUCCESS(' OK'))
                else:
                    failed += 1
                    self.stdout.write(self.style.WARNING(' FAILED'))

            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f' ERROR: {e}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Screenshot capture complete: {captured} captured, {failed} failed'
            )
        )
