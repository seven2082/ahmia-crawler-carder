from typing import Optional, List, Dict
from django.db.models import QuerySet, Q

from .base import BaseRepository
from ..models import OnionProfile, Category
from ..exceptions import ProfileNotFoundError
from ..constants import ProfileStatus


class ProfileRepository(BaseRepository[OnionProfile]):
    """Repository for OnionProfile operations."""

    model = OnionProfile

    def get_queryset(self) -> QuerySet[OnionProfile]:
        """Default queryset excludes banned profiles."""
        return super().get_queryset().exclude(status=ProfileStatus.BANNED)

    def get_by_slug(self, slug: str) -> OnionProfile:
        """Get profile by slug or raise ProfileNotFoundError."""
        try:
            return self.get_queryset().get(slug=slug)
        except OnionProfile.DoesNotExist:
            raise ProfileNotFoundError(f"Profile with slug '{slug}' not found")

    def get_by_slug_or_none(self, slug: str) -> Optional[OnionProfile]:
        """Get profile by slug or return None."""
        try:
            return self.get_by_slug(slug)
        except ProfileNotFoundError:
            return None

    def get_by_domain(self, domain: str) -> OnionProfile:
        """Get profile by current domain or raise ProfileNotFoundError."""
        try:
            return self.get_queryset().get(current_domain=domain)
        except OnionProfile.DoesNotExist:
            raise ProfileNotFoundError(f"Profile with domain '{domain}' not found")

    def get_by_domain_or_none(self, domain: str) -> Optional[OnionProfile]:
        """Get profile by domain or return None."""
        try:
            return self.get_by_domain(domain)
        except ProfileNotFoundError:
            return None

    def list_by_category(self, category_slug: str) -> QuerySet[OnionProfile]:
        """List profiles in a category."""
        return self.get_queryset().filter(category__slug=category_slug)

    def list_by_tag(self, tag_slug: str) -> QuerySet[OnionProfile]:
        """List profiles with a specific tag."""
        return self.get_queryset().filter(tags__slug=tag_slug)

    def list_verified(self) -> QuerySet[OnionProfile]:
        """List verified profiles."""
        return self.get_queryset().filter(is_verified=True)

    def list_active(self) -> QuerySet[OnionProfile]:
        """List active profiles."""
        return self.get_queryset().filter(status=ProfileStatus.ACTIVE)

    def search(self, query: str) -> QuerySet[OnionProfile]:
        """Search profiles by name or description."""
        return self.get_queryset().filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    def get_domain_to_slug_map(self, domains: List[str]) -> dict:
        """Get mapping of domain -> slug for multiple domains."""
        profiles = self.model.objects.filter(
            current_domain__in=domains
        ).values('current_domain', 'slug')
        return {p['current_domain']: p['slug'] for p in profiles}

    def get_profiles_for_domains(self, domains: List[str]) -> Dict[str, OnionProfile]:
        """Get profiles keyed by domain for a list of domains."""
        if not domains:
            return {}
        profiles = self.model.objects.filter(current_domain__in=domains)
        return {p.current_domain: p for p in profiles}
