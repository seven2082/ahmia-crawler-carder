from typing import Dict, Any
from django.utils import timezone
from datetime import timedelta

from .registry import register_service, get_service
from ..models import OnionProfile, Category
from ..constants import ProfileStatus


@register_service('sync_service')
class SyncService:
    """Service for ES to DB synchronization."""

    @property
    def es_service(self):
        return get_service('elasticsearch_service')

    @property
    def slug_service(self):
        return get_service('slug_service')

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

        default_category = Category.objects.filter(slug='other').first()
        if not default_category:
            default_category = Category.objects.first()

        for domain_info in domains:
            domain = domain_info['domain']

            if domain in existing_domains:
                skipped += 1
                continue

            # Get metadata from ES
            metadata = self.es_service.get_domain_metadata(domain)

            # Generate slug
            slug = self.slug_service.generate_slug(
                name=metadata.get('title', ''),
                domain=domain
            )

            # Create profile
            OnionProfile.objects.create(
                slug=slug,
                current_domain=domain,
                name=metadata.get('title', domain[:50]),
                description=metadata.get('description', ''),
                category=default_category,
                page_count=domain_info.get('page_count', 0),
                last_seen=timezone.now()
            )
            created += 1

        return {
            'created': created,
            'skipped': skipped,
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
