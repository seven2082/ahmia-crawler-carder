from django.core.management.base import BaseCommand

from profiles.models import OnionProfile
from profiles.services import get_service


class Command(BaseCommand):
    help = 'Check and refresh verification status for profiles with pending tokens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Check all verified profiles (re-verify)'
        )
        parser.add_argument(
            '--profile',
            type=str,
            help='Check a specific profile by slug'
        )

    def handle(self, *args, **options):
        verification_service = get_service('verification_service')

        if options['profile']:
            try:
                profile = OnionProfile.objects.get(slug=options['profile'])
                self._check_profile(profile, verification_service)
            except OnionProfile.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Profile not found: {options['profile']}")
                )
                return
        elif options['all']:
            profiles = OnionProfile.objects.filter(is_verified=True)
            self._check_profiles(profiles, verification_service)
        else:
            profiles = OnionProfile.objects.filter(
                verification_token__isnull=False
            ).exclude(is_verified=True)
            self._check_profiles(profiles, verification_service)

    def _check_profile(self, profile, verification_service):
        self.stdout.write(f'Checking {profile.slug}...')
        try:
            if verification_service.check_verification(profile):
                self.stdout.write(
                    self.style.SUCCESS(f'  {profile.slug}: VERIFIED')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  {profile.slug}: not verified')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  {profile.slug}: error - {e}')
            )

    def _check_profiles(self, profiles, verification_service):
        verified = 0
        failed = 0

        for profile in profiles:
            try:
                if verification_service.check_verification(profile):
                    verified += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  {profile.slug}: VERIFIED')
                    )
                else:
                    failed += 1
            except Exception:
                failed += 1

        self.stdout.write(
            f'\nResults: {verified} verified, {failed} failed/pending'
        )
