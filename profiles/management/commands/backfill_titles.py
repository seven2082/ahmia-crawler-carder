from django.core.management.base import BaseCommand
from profiles.models import OnionProfile
from profiles.services import get_service
import re


class Command(BaseCommand):
    help = 'Backfill empty profile names from ES page titles'

    def add_arguments(self, parser):
        parser.add_argument('--fix-pagination', action='store_true',
                            help='Also fix titles that look like pagination pages')

    def is_pagination_title(self, title):
        """Check if title looks like a pagination page."""
        if not title:
            return False
        patterns = [
            r'page\s+\d+\s+of\s+\d+',
            r'страница\s+\d+',
            r'seite\s+\d+',
        ]
        title_lower = title.lower()
        return any(re.search(p, title_lower) for p in patterns)

    def get_best_title(self, es_service, domain):
        """Get best title for domain - prefer homepage, skip pagination."""
        pages = es_service.get_top_pages(domain, 20)
        if not pages:
            return None

        for page in pages:
            url = page.get('url', '')
            title = page.get('title', '').strip()
            if url.endswith('/') or url.endswith('/index.html') or url.endswith('/index.php'):
                if title and len(title) > 3 and not self.is_pagination_title(title):
                    return title

        for page in pages:
            title = page.get('title', '').strip()
            if title and len(title) > 3 and not self.is_pagination_title(title):
                return title

        for page in pages:
            title = page.get('title', '').strip()
            if title and len(title) > 3:
                return title

        return None

    def handle(self, *args, **options):
        es_service = get_service('elasticsearch_service')
        fix_pagination = options.get('fix_pagination', False)

        if fix_pagination:
            profiles = OnionProfile.objects.all()
            self.stdout.write('Checking all profiles for empty or pagination titles...')
        else:
            profiles = OnionProfile.objects.filter(name='')
            self.stdout.write(f'Found {profiles.count()} profiles with empty names')

        updated = 0
        checked = 0

        for profile in profiles:
            checked += 1
            current_name = profile.name.strip()

            if current_name and not fix_pagination:
                continue

            needs_fix = (not current_name) or self.is_pagination_title(current_name)
            if not needs_fix:
                continue

            try:
                best_title = self.get_best_title(es_service, profile.current_domain)
                if best_title and best_title != current_name:
                    profile.name = best_title[:255]
                    profile.save(update_fields=['name', 'updated_at'])
                    updated += 1
                    if updated <= 50:
                        self.stdout.write(f'Updated: {profile.slug} -> {best_title[:50]}...')
            except Exception as e:
                self.stderr.write(f'Error for {profile.slug}: {e}')

        self.stdout.write(self.style.SUCCESS(f'Updated {updated}/{checked} profiles'))
