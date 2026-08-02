"""
End-to-end integration tests for the onion profile system (Task 32).

These tests exercise complete flows across services, models, views and
URLs together, rather than any single unit in isolation.

Note: tests that issue HTTP requests via Django's test ``Client`` use
``pytest.mark.urls('profiles.tests.test_views.test_urlconf')`` -- the
same workaround already used by ``test_profile_views.py``,
``test_directory_views.py`` and ``test_moderation_views.py`` -- because
the local dev environment's (untracked) ``ahmia/settings_local.py``
overrides ``ROOT_URLCONF`` to ``ahmia.urls_mock``, which does not mount
the profiles app. That override is pre-existing and outside the scope
of this project.
"""
import pytest
from django.test import Client
from unittest.mock import patch, MagicMock

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.urls('profiles.tests.test_views.test_urlconf'),
]


class TestProfileCreationFlow:
    """Test the full profile creation flow from ES sync."""

    def test_sync_creates_browsable_profile(self):
        from profiles.models import OnionProfile, Category
        from profiles.services import get_service

        Category.objects.create(name='Other', slug='other')

        sync_service = get_service('sync_service')

        mock_es = MagicMock()
        mock_slug = MagicMock()
        mock_es.get_all_domains.return_value = [
            {'domain': 'newsite.onion', 'page_count': 10}
        ]
        mock_es.get_domain_metadata.return_value = {
            'title': 'New Site',
            'description': 'A new onion site'
        }
        mock_slug.generate_slug.return_value = 'new-site'

        # es_service/slug_service are read-only properties on SyncService
        # that resolve collaborators via the module-level get_service()
        # call, so patch that call site rather than the instance
        # attributes (same pattern used in test_sync_service.py).
        services = {'elasticsearch_service': mock_es, 'slug_service': mock_slug}
        with patch(
            'profiles.services.sync_service.get_service',
            side_effect=lambda name: services[name]
        ):
            result = sync_service.sync_all_profiles()

            assert result['created'] == 1

        profile = OnionProfile.objects.get(slug='new-site')
        assert profile.name == 'New Site'

        client = Client()

        with patch('profiles.views.profile_views.get_service') as mock_get:
            mock_service = MagicMock()
            mock_service.get_profile_with_stats.return_value = {
                'profile': profile,
                'page_count': 10,
                'last_seen': None,
                'top_pages': []
            }
            mock_get.return_value = mock_service

            response = client.get(f'/site/{profile.slug}/')
            assert response.status_code == 200


class TestEditSubmissionFlow:
    """Test the edit submission and approval flow."""

    def test_submit_and_approve_edit(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.services import get_service
        from profiles.constants import TrustLevel, EditStatus

        profile = OnionProfileFactory(description='Old description')
        contributor = ContributorFactory(trust_level=TrustLevel.NEW)
        moderator = ContributorFactory(trust_level=TrustLevel.MODERATOR)

        moderation_service = get_service('moderation_service')

        edit = moderation_service.submit_edit(
            profile=profile,
            field_name='description',
            new_value='New description',
            contributor=contributor
        )

        assert edit.status == EditStatus.PENDING

        moderation_service.approve_edit(edit, moderator, 'Looks good')

        edit.refresh_from_db()
        profile.refresh_from_db()

        assert edit.status == EditStatus.APPROVED
        assert profile.description == 'New description'


class TestVerificationFlow:
    """Test the site verification flow."""

    def test_verification_token_generation(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services import get_service

        # verification_token has `default=''` and no NULL constraint on
        # the model, so an unverified profile is represented by an empty
        # string rather than None.
        profile = OnionProfileFactory(verification_token='')

        verification_service = get_service('verification_service')
        token = verification_service.start_verification(profile)

        profile.refresh_from_db()

        assert token is not None
        assert profile.verification_token == token
        assert len(token) == 64


class TestTrustLevelProgression:
    """Test contributor trust level progression."""

    def test_trust_upgrades_after_approved_edits(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.services import get_service
        from profiles.constants import TrustLevel, TRUST_LEVEL_THRESHOLD
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user('tester', 'test@example.com', 'password')

        contributor = ContributorFactory(
            user=user,
            trust_level=TrustLevel.NEW,
            approved_edits=TRUST_LEVEL_THRESHOLD - 1
        )
        moderator = ContributorFactory(trust_level=TrustLevel.MODERATOR)
        profile = OnionProfileFactory()

        moderation_service = get_service('moderation_service')

        edit = moderation_service.submit_edit(
            profile=profile,
            field_name='description',
            new_value='Final edit',
            contributor=contributor
        )
        moderation_service.approve_edit(edit, moderator, '')

        contributor.refresh_from_db()
        assert contributor.trust_level == TrustLevel.TRUSTED


class TestDirectoryBrowsing:
    """Test directory browsing functionality."""

    def test_category_filtering(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.models import Category

        forum = Category.objects.create(name='Forum', slug='forum')
        market = Category.objects.create(name='Market', slug='market')

        OnionProfileFactory(category=forum)
        OnionProfileFactory(category=forum)
        OnionProfileFactory(category=market)

        client = Client()

        with patch('profiles.views.directory_views.ContributorMixin.get_contributor') as mock:
            mock.return_value = MagicMock()

            response = client.get('/site/category/forum/')

            assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting on edit submissions."""

    def test_rate_limit_exceeded(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.services import get_service
        from profiles.constants import RATE_LIMIT_EDITS_PER_HOUR
        from profiles.exceptions import RateLimitExceededError

        profile = OnionProfileFactory()
        contributor = ContributorFactory()

        moderation_service = get_service('moderation_service')

        for i in range(RATE_LIMIT_EDITS_PER_HOUR):
            moderation_service.submit_edit(
                profile=profile,
                field_name='description',
                new_value=f'Edit {i}',
                contributor=contributor
            )

        with pytest.raises(RateLimitExceededError):
            moderation_service.submit_edit(
                profile=profile,
                field_name='description',
                new_value='One too many',
                contributor=contributor
            )
