import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.django_db


class TestProfileService:
    def test_create_profile(self):
        from profiles.services.profile_service import ProfileService
        from profiles.models import Category

        Category.objects.create(name='Other', slug='other')

        service = ProfileService()
        profile = service.create_profile(
            domain='testsite567890abcdef1234567890abcdef1234567890abcdefgh.onion',
            name='Test Site',
            description='A test site'
        )

        assert profile.slug == 'test-site'
        assert profile.name == 'Test Site'
        assert profile.category.slug == 'other'

    def test_create_profile_generates_slug_from_domain(self):
        from profiles.services.profile_service import ProfileService
        from profiles.models import Category

        Category.objects.create(name='Other', slug='other')

        service = ProfileService()
        profile = service.create_profile(
            domain='abcdefghij67890abcdef1234567890abcdef1234567890abcdefgh.onion',
            name='',
            description=''
        )

        assert profile.slug == 'abcdefghij67'

    def test_update_profile(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.profile_service import ProfileService

        profile = OnionProfileFactory(name='Old Name')

        service = ProfileService()
        updated = service.update_profile(profile, name='New Name')

        assert updated.name == 'New Name'

    def test_get_profile_with_stats(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.profile_service import ProfileService

        profile = OnionProfileFactory()

        with patch('profiles.services.profile_service.get_service') as mock_get:
            mock_es = MagicMock()
            mock_es.get_domain_stats.return_value = {'page_count': 100, 'last_seen': None}
            mock_es.get_top_pages.return_value = [{'url': '/test', 'title': 'Test'}]
            mock_get.return_value = mock_es

            service = ProfileService()
            result = service.get_profile_with_stats(profile.slug)

            assert result['profile'] == profile
            assert result['page_count'] == 100
            assert len(result['top_pages']) == 1
