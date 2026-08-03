from typing import Dict, Any
from django.utils import timezone
from datetime import timedelta

from .registry import register_service, get_service
from ..models import OnionProfile, Category, DomainHistory
from ..constants import ProfileStatus, MigrationSource


@register_service('sync_service')
class SyncService:
    """Service for ES to DB synchronization."""

    # Category keyword mapping
    CATEGORY_KEYWORDS = {
        'market': ['market', 'shop', 'store', 'buy', 'sell', 'vendor', 'escrow', 'cards', 'credit card', 'dumps', 'cvv'],
        'forum': ['forum', 'board', 'community', 'discuss', 'thread', 'topic', 'member'],
        'crypto': ['bitcoin', 'btc', 'crypto', 'wallet', 'exchange', 'monero', 'xmr', 'ethereum', 'mixer', 'tumbler'],
        'email': ['email', 'mail', 'inbox', 'webmail', 'smtp', 'protonmail'],
        'hosting': ['hosting', 'server', 'vps', 'cloud', 'onion service', 'hidden service'],
        'search': ['search', 'engine', 'index', 'directory', 'find', 'lookup'],
        'social': ['social', 'chat', 'messenger', 'network', 'connect', 'friends'],
        'news': ['news', 'article', 'journal', 'media', 'press', 'report'],
        'wiki': ['wiki', 'encyclopedia', 'knowledge', 'documentation', 'guide'],
        'blog': ['blog', 'post', 'personal', 'diary', 'write'],
        'tools': ['tool', 'utility', 'generator', 'converter', 'checker', 'scan'],
    }

    @property
    def es_service(self):
        return get_service('elasticsearch_service')

    @property
    def slug_service(self):
        return get_service('slug_service')

    @property
    def crawler_service(self):
        return get_service('crawler_service')

    def detect_category(self, title: str, description: str) -> str:
        """Detect category based on title and description keywords."""
        text = f"{title} {description}".lower()

        for cat_slug, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return cat_slug

        return 'other'

    def sync_all_profiles(self) -> Dict[str, Any]:
        """
        Sync all domains from ES to DB.
        Creates profiles for new domains.
        Returns stats dict with created/existing counts.
        """
        domains = self.es_service.get_all_domains()
        existing_domains = set(
            OnionProfile.objects.values_list('current_domain', flat=True)
        )

        created = 0
        skipped = 0

        # Cache categories
        categories = {c.slug: c for c in Category.objects.all()}
        default_category = categories.get('other') or Category.objects.first()

        merged = 0

        for domain_info in domains:
            domain = domain_info['domain']

            if domain in existing_domains:
                skipped += 1
                continue

            # Get metadata from ES
            metadata = self.es_service.get_domain_metadata(domain)
            title = metadata.get('title', '')
            description = metadata.get('description', '')

            # If ES has no good title (just domain prefix), try live crawl
            is_domain_prefix = len(title) <= 16 and title == domain.replace('.onion', '')[:16]
            if is_domain_prefix or not title:
                try:
                    crawl_data = self.crawler_service.crawl_domain(domain)
                    if crawl_data.get('reachable') and crawl_data.get('title'):
                        title = crawl_data['title']
                        if crawl_data.get('description'):
                            description = crawl_data['description']
                except Exception:
                    pass

            # Fallback to domain prefix if still no title
            if not title:
                title = domain[:50]

            # Check if profile with same title exists (mirror detection)
            # Only merge if title is not a domain prefix (16 chars or less)
            if len(title) > 16:
                existing = OnionProfile.objects.filter(name=title).first()
                if existing:
                    # Check if domain already in history
                    already_exists = DomainHistory.objects.filter(
                        profile=existing, domain=domain
                    ).exists()
                    if not already_exists and domain != existing.current_domain:
                        # Add domain to history
                        DomainHistory.objects.create(
                            profile=existing,
                            domain=domain,
                            was_active_from=timezone.now(),
                            was_active_to=timezone.now(),
                            migration_type=MigrationSource.CRAWLER
                        )
                        merged += 1
                    skipped += 1
                    continue

            # Generate slug
            slug = self.slug_service.generate_slug(
                name=title,
                domain=domain
            )

            # Detect category
            cat_slug = self.detect_category(title, description)
            category = categories.get(cat_slug, default_category)

            # Create profile
            OnionProfile.objects.create(
                slug=slug,
                current_domain=domain,
                name=title,
                description=description,
                category=category,
                page_count=domain_info.get('page_count', 0),
                last_seen=timezone.now()
            )
            created += 1

        return {
            'created': created,
            'skipped': skipped,
            'merged': merged,
            'total_domains': len(domains)
        }

    def update_profile_stats(self, profile: OnionProfile) -> None:
        """Update cached stats for a single profile."""
        stats = self.es_service.get_domain_stats(profile.current_domain)

        profile.page_count = stats.get('page_count', 0)
        profile.last_seen = stats.get('last_seen')

        # Update status based on last_seen
        if profile.last_seen:
            days_since = (timezone.now() - profile.last_seen).days
            if days_since > 30:
                profile.status = ProfileStatus.OFFLINE
            elif days_since <= 7:
                profile.status = ProfileStatus.ACTIVE

        profile.save(update_fields=['page_count', 'last_seen', 'status', 'updated_at'])

    def update_all_stats(self) -> int:
        """Update stats for all active profiles. Returns count updated."""
        profiles = OnionProfile.objects.exclude(status=ProfileStatus.BANNED)
        count = 0

        for profile in profiles:
            try:
                self.update_profile_stats(profile)
                count += 1
            except Exception:
                continue

        return count
