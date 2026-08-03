from django.core.management.base import BaseCommand

from profiles.models import OnionProfile
from profiles.services import get_service


class Command(BaseCommand):
    help = 'Crawl .onion sites to update profile metadata (title, description, keywords)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum profiles to crawl (default: 100)'
        )
        parser.add_argument(
            '--only-missing',
            action='store_true',
            help='Only crawl profiles with domain-prefix titles'
        )

    def handle(self, *args, **options):
        crawler = get_service('crawler_service')
        limit = options['limit']
        only_missing = options['only_missing']

        profiles = OnionProfile.objects.all()

        if only_missing:
            profiles = [
                p for p in profiles
                if len(p.name) <= 16 and p.name == p.current_domain.replace('.onion', '')[:16]
            ]
            self.stdout.write(f'Found {len(profiles)} profiles with missing titles')
        else:
            profiles = list(profiles[:limit])

        profiles = profiles[:limit]
        self.stdout.write(f'Crawling {len(profiles)} profiles...')

        updated = 0
        unreachable = 0
        unchanged = 0

        for i, profile in enumerate(profiles):
            if i % 10 == 0:
                self.stdout.write(f'  Progress: {i}/{len(profiles)}')

            try:
                data = crawler.crawl_domain(profile.current_domain)

                if not data.get('reachable'):
                    unreachable += 1
                    continue

                changed = False

                if data.get('title') and data['title'] != profile.name:
                    profile.name = data['title'][:200]
                    changed = True

                if data.get('description') and data['description'] != profile.description:
                    profile.description = data['description'][:500]
                    changed = True

                if changed:
                    profile.save(update_fields=['name', 'description', 'updated_at'])
                    updated += 1
                else:
                    unchanged += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error crawling {profile.current_domain}: {e}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Crawl complete: {updated} updated, {unreachable} unreachable, {unchanged} unchanged'
            )
        )
