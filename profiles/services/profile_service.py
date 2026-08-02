from typing import Optional, Dict, Any

from .registry import register_service, get_service
from ..repositories import ProfileRepository
from ..models import OnionProfile, Category
from ..exceptions import ProfileNotFoundError


@register_service('profile_service')
class ProfileService:
    """Service for profile business logic."""

    def __init__(self):
        self._repo = ProfileRepository()

    @property
    def es_service(self):
        return get_service('elasticsearch_service')

    @property
    def slug_service(self):
        return get_service('slug_service')

    def create_profile(
        self,
        domain: str,
        name: str = '',
        description: str = '',
        category_slug: str = 'other'
    ) -> OnionProfile:
        """Create a new profile for a domain."""
        # Generate unique slug
        slug = self.slug_service.generate_slug(name=name, domain=domain)

        # Get category
        try:
            category = Category.objects.get(slug=category_slug)
        except Category.DoesNotExist:
            category = Category.objects.get(slug='other')

        # Create profile
        profile = OnionProfile.objects.create(
            slug=slug,
            current_domain=domain,
            name=name or domain[:50],
            description=description,
            category=category
        )
        return profile

    def update_profile(self, profile: OnionProfile, **kwargs) -> OnionProfile:
        """Update profile fields."""
        allowed_fields = {'name', 'description', 'category', 'logo', 'status'}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(profile, key, value)
        profile.save()
        return profile

    def get_profile_with_stats(self, slug: str) -> Dict[str, Any]:
        """Get profile with live ES stats."""
        profile = self._repo.get_by_slug(slug)

        # Get live stats from ES
        stats = self.es_service.get_domain_stats(profile.current_domain)
        top_pages = self.es_service.get_top_pages(profile.current_domain, limit=5)

        return {
            'profile': profile,
            'page_count': stats.get('page_count', profile.page_count),
            'last_seen': stats.get('last_seen', profile.last_seen),
            'top_pages': top_pages,
        }

    def get_profile_by_domain(self, domain: str) -> Optional[OnionProfile]:
        """Get profile by domain or None."""
        return self._repo.get_by_domain_or_none(domain)
