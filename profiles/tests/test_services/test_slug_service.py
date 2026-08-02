import pytest

pytestmark = pytest.mark.django_db


class TestSlugService:
    def test_generate_from_name(self):
        from profiles.services.slug_service import SlugService

        service = SlugService()
        slug = service.generate_slug(name='Dread Forum', domain='abc123.onion')

        assert slug == 'dread-forum'

    def test_generate_from_domain_when_no_name(self):
        from profiles.services.slug_service import SlugService

        service = SlugService()
        domain = 'dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion'
        slug = service.generate_slug(name='', domain=domain)

        assert slug == 'dreadytofatr'  # First 12 chars

    def test_ensure_unique_no_collision(self):
        from profiles.services.slug_service import SlugService

        service = SlugService()
        slug = service.ensure_unique('unique-slug')

        assert slug == 'unique-slug'

    def test_ensure_unique_with_collision(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.slug_service import SlugService

        OnionProfileFactory(slug='taken-slug')

        service = SlugService()
        slug = service.ensure_unique('taken-slug')

        assert slug == 'taken-slug-2'

    def test_ensure_unique_multiple_collisions(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.slug_service import SlugService

        OnionProfileFactory(slug='popular')
        OnionProfileFactory(slug='popular-2')
        OnionProfileFactory(slug='popular-3')

        service = SlugService()
        slug = service.ensure_unique('popular')

        assert slug == 'popular-4'
