import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _get_service_side_effect(mock_es=None, mock_slug=None):
    """Build a side_effect for the module-level get_service() lookup.

    SyncService resolves its collaborators lazily via `get_service(name)`
    through read-only properties (es_service/slug_service). Those
    properties cannot be patched with `patch.object(instance, name)`
    because they are non-data-settable properties defined on the class,
    so we patch the `get_service` call site instead (same pattern used
    in test_profile_service.py).
    """
    services = {}
    if mock_es is not None:
        services['elasticsearch_service'] = mock_es
    if mock_slug is not None:
        services['slug_service'] = mock_slug

    def side_effect(name):
        return services[name]

    return side_effect


class TestSyncService:
    def test_sync_all_profiles_creates_new(self):
        from profiles.services.sync_service import SyncService
        from profiles.models import OnionProfile, Category

        Category.objects.create(name='Other', slug='other')

        service = SyncService()

        mock_es = MagicMock()
        mock_slug = MagicMock()
        mock_es.get_all_domains.return_value = [
            {'domain': 'newsite567890abcdef1234567890abcdef1234567890abcdefgh.onion', 'page_count': 10}
        ]
        mock_es.get_domain_metadata.return_value = {'title': 'New Site', 'description': 'A new site'}
        mock_slug.generate_slug.return_value = 'new-site'

        with patch(
            'profiles.services.sync_service.get_service',
            side_effect=_get_service_side_effect(mock_es=mock_es, mock_slug=mock_slug)
        ):
            result = service.sync_all_profiles()

            assert result['created'] == 1
            assert OnionProfile.objects.filter(slug='new-site').exists()

    def test_sync_all_profiles_skips_existing(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.sync_service import SyncService
        from profiles.models import Category

        Category.objects.create(name='Other', slug='other')
        profile = OnionProfileFactory()

        service = SyncService()

        mock_es = MagicMock()
        mock_es.get_all_domains.return_value = [
            {'domain': profile.current_domain, 'page_count': 10}
        ]

        with patch(
            'profiles.services.sync_service.get_service',
            side_effect=_get_service_side_effect(mock_es=mock_es)
        ):
            result = service.sync_all_profiles()

            assert result['created'] == 0
            assert result['skipped'] == 1

    def test_update_profile_stats(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.sync_service import SyncService

        profile = OnionProfileFactory(page_count=0)

        service = SyncService()

        mock_es = MagicMock()
        mock_es.get_domain_stats.return_value = {
            'page_count': 50,
            'last_seen': timezone.now()
        }

        with patch(
            'profiles.services.sync_service.get_service',
            side_effect=_get_service_side_effect(mock_es=mock_es)
        ):
            service.update_profile_stats(profile)

            profile.refresh_from_db()
            assert profile.page_count == 50

    def test_update_all_stats(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.sync_service import SyncService

        OnionProfileFactory()
        OnionProfileFactory()

        service = SyncService()

        mock_es = MagicMock()
        mock_es.get_domain_stats.return_value = {'page_count': 10, 'last_seen': timezone.now()}

        with patch(
            'profiles.services.sync_service.get_service',
            side_effect=_get_service_side_effect(mock_es=mock_es)
        ):
            count = service.update_all_stats()

            assert count == 2
