import re
from django.utils.text import slugify

from .registry import register_service
from ..models import OnionProfile


@register_service('slug_service')
class SlugService:
    """Service for generating unique profile slugs."""

    def generate_slug(self, name: str, domain: str) -> str:
        """
        Generate a slug from name or domain.

        Priority:
        1. Slugified name if provided
        2. First 12 chars of domain (without .onion)
        """
        if name and name.strip():
            base_slug = slugify(name.strip())
            if base_slug:
                return self.ensure_unique(base_slug[:100])

        # Extract domain name without .onion
        domain_name = domain.replace('.onion', '')
        base_slug = domain_name[:12].lower()
        # Ensure only valid slug characters
        base_slug = re.sub(r'[^a-z0-9-]', '', base_slug)

        return self.ensure_unique(base_slug)

    def ensure_unique(self, base_slug: str) -> str:
        """
        Ensure slug is unique by appending suffix if needed.

        Examples:
            'my-site' -> 'my-site' (if unique)
            'my-site' -> 'my-site-2' (if 'my-site' exists)
            'my-site' -> 'my-site-3' (if 'my-site' and 'my-site-2' exist)
        """
        if not OnionProfile.objects.filter(slug=base_slug).exists():
            return base_slug

        counter = 2
        while True:
            candidate = f"{base_slug}-{counter}"
            if not OnionProfile.objects.filter(slug=candidate).exists():
                return candidate
            counter += 1
            if counter > 1000:  # Safety limit
                raise ValueError(f"Could not generate unique slug for '{base_slug}'")
