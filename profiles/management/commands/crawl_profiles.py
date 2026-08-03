import re
from django.core.management.base import BaseCommand

from profiles.models import OnionProfile
from profiles.services import get_service


GENERIC_TITLES = {
    'home', 'index', 'welcome', 'untitled', 'loading', 'error',
    '404', 'not found', 'page not found', 'access denied', 'forbidden',
    'coming soon', 'under construction', 'maintenance', 'offline',
    '301 moved', '302 found', '303 see other', '307 temporary',
    '400 bad request', '401 unauthorized', '403 forbidden',
    '404 not found', '500 internal', '502 bad gateway', '503 service',
    'moved permanently', 'moved temporarily', 'bad gateway',
    'internal server error', 'service unavailable',
}

SPAM_PATTERNS = [
    'child porn', 'child sex', 'pedo', 'loli', 'jailbait', 'underage',
    'preteen', 'cphub', 'shotacon', 'toddlercon', 'bestiality',
    'little angel', 'little girl', 'little boy', 'young nude',
]


def is_domain_prefix(name: str, domain: str) -> bool:
    """Check if name is just a domain prefix (not a real title)."""
    if not name or len(name) <= 16:
        prefix = domain.replace('.onion', '')[:16]
        return name == prefix or bool(re.match(r'^[a-z0-9]{8,16}$', name, re.I))
    return False


def title_quality_score(title: str) -> int:
    """Score title quality. Higher = better. Negative = bad."""
    if not title:
        return -100

    lower = title.lower().strip()

    # CSAM = reject
    for p in SPAM_PATTERNS:
        if p in lower:
            return -100

    # Generic/error = reject
    for g in GENERIC_TITLES:
        if g in lower:
            return -50

    # Just numbers/symbols = bad
    if re.match(r'^[\d\W]+$', title):
        return -10

    # Too short = weak
    if len(title) < 5:
        return 0

    # Base score by length (capped)
    score = min(len(title), 60)

    # Bonus for having multiple words
    words = len(title.split())
    if words >= 2:
        score += 10
    if words >= 3:
        score += 5

    # Bonus for having a separator (suggests structured title)
    if any(sep in title for sep in [' - ', ' | ', ' :: ', ' — ']):
        score += 10

    return score


def is_better_title(new_title: str, old_title: str, domain: str) -> bool:
    """Check if new title is better than old."""
    # If old is domain prefix, any real title is better
    if is_domain_prefix(old_title, domain):
        new_score = title_quality_score(new_title)
        return new_score > 0

    # Compare scores
    old_score = title_quality_score(old_title)
    new_score = title_quality_score(new_title)

    # New must be significantly better (avoid churn)
    return new_score > old_score + 10


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
                new_title = data.get('title', '').strip()
                new_desc = data.get('description', '').strip()

                # Only update title if new is better
                if new_title and is_better_title(new_title, profile.name, profile.current_domain):
                    profile.name = new_title[:200]
                    changed = True

                # Only update description if current is empty or very short
                if new_desc and (not profile.description or len(profile.description) < 20):
                    profile.description = new_desc[:500]
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
