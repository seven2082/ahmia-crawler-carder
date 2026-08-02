import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from unittest.mock import patch, MagicMock

from profiles.constants import TrustLevel
from profiles.tests.factories import (
    OnionProfileFactory,
    DomainHistoryFactory,
    ContributorFactory,
    ProfileEditFactory,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls('profiles.tests.test_views.test_urlconf')]

User = get_user_model()


class TestProfileListView:
    def test_list_view_renders(self):
        OnionProfileFactory()
        OnionProfileFactory()

        client = Client()

        with patch('profiles.views.profile_views.get_service') as mock_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = MagicMock()
            mock_get.return_value = mock_trust

            response = client.get('/site/')

            assert response.status_code == 200

    def test_list_view_uses_active_profiles(self):
        active = OnionProfileFactory(status='active')

        client = Client()

        with patch('profiles.views.profile_views.get_service'):
            response = client.get('/site/')

            assert response.status_code == 200
            assert active in response.context['profiles']


class TestProfileDetailView:
    def test_detail_view_renders(self):
        profile = OnionProfileFactory(slug='test-profile')

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

    def test_detail_view_uses_live_stats(self):
        profile = OnionProfileFactory(slug='stats-profile', page_count=1)

        client = Client()

        with patch('profiles.views.profile_views.get_service') as mock_get:
            mock_service = MagicMock()
            mock_service.get_profile_with_stats.return_value = {
                'profile': profile,
                'page_count': 99,
                'last_seen': None,
                'top_pages': [
                    {'url': 'http://stats-profile.onion/a', 'title': 'Page A'},
                    {'url': 'http://stats-profile.onion/b', 'title': 'Page B'},
                ]
            }
            mock_get.return_value = mock_service

            response = client.get(f'/site/{profile.slug}/')

            assert response.context['page_count'] == 99
            assert response.context['top_pages'] == [
                {'url': 'http://stats-profile.onion/a', 'title': 'Page A'},
                {'url': 'http://stats-profile.onion/b', 'title': 'Page B'},
            ]

    def test_detail_view_falls_back_when_service_errors(self):
        profile = OnionProfileFactory(slug='fallback-profile', page_count=5)

        client = Client()

        with patch('profiles.views.profile_views.get_service') as mock_get:
            mock_service = MagicMock()
            mock_service.get_profile_with_stats.side_effect = Exception('ES down')
            mock_get.return_value = mock_service

            response = client.get(f'/site/{profile.slug}/')

            assert response.status_code == 200
            assert response.context['page_count'] == 5
            assert response.context['top_pages'] == []

    def test_detail_view_includes_domain_history(self):
        profile = OnionProfileFactory(slug='history-profile')
        DomainHistoryFactory(profile=profile)

        client = Client()

        with patch('profiles.views.profile_views.get_service') as mock_get:
            mock_service = MagicMock()
            mock_service.get_profile_with_stats.return_value = {
                'profile': profile,
                'page_count': 0,
                'last_seen': None,
                'top_pages': []
            }
            mock_get.return_value = mock_service

            response = client.get(f'/site/{profile.slug}/')

            assert response.context['domain_history'].count() == 1


class TestProfileEditView:
    def test_edit_view_get_renders_with_initial_data(self):
        profile = OnionProfileFactory(slug='edit-profile', name='Original Name')
        contributor = ContributorFactory(trust_level=TrustLevel.NEW)

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            response = client.get(f'/site/{profile.slug}/edit/')

            assert response.status_code == 200
            assert response.context['form'].initial['name'] == 'Original Name'

    def test_edit_view_rejects_insufficient_trust(self):
        profile = OnionProfileFactory(slug='edit-blocked')
        contributor = ContributorFactory(trust_level=TrustLevel.ANONYMOUS)

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            response = client.get(f'/site/{profile.slug}/edit/')

            assert response.status_code == 302

    def test_edit_view_post_submits_changed_fields(self):
        profile = OnionProfileFactory(
            slug='edit-post', name='Old Name', description='Old description'
        )
        contributor = ContributorFactory(trust_level=TrustLevel.NEW)

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.profile_views.get_service') as mock_views_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_moderation = MagicMock()
            mock_views_get.return_value = mock_moderation

            response = client.post(
                f'/site/{profile.slug}/edit/',
                data={'name': 'New Name', 'description': 'Old description'}
            )

            assert response.status_code == 302
            assert response.url == reverse('profiles:detail', kwargs={'slug': profile.slug})
            mock_moderation.submit_edit.assert_called_once_with(
                profile, 'name', 'New Name', contributor
            )

    def test_edit_view_post_no_changes(self):
        profile = OnionProfileFactory(
            slug='edit-nochange', name='Same Name', description='Same description'
        )
        contributor = ContributorFactory(trust_level=TrustLevel.NEW)

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.profile_views.get_service') as mock_views_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_moderation = MagicMock()
            mock_views_get.return_value = mock_moderation

            response = client.post(
                f'/site/{profile.slug}/edit/',
                data={'name': 'Same Name', 'description': 'Same description'}
            )

            assert response.status_code == 302
            mock_moderation.submit_edit.assert_not_called()


class TestProfileClaimView:
    def test_claim_view_generates_token_when_missing(self):
        profile = OnionProfileFactory(slug='claim-new', verification_token='')

        client = Client()

        with patch('profiles.views.profile_views.get_service') as mock_views_get:
            mock_verification = MagicMock()
            mock_verification.start_verification.return_value = 'generated-token'
            mock_views_get.return_value = mock_verification

            response = client.get(f'/site/{profile.slug}/claim/')

            assert response.status_code == 200
            mock_verification.start_verification.assert_called_once_with(profile)
            assert response.context['verification_token'] == 'generated-token'

    def test_claim_view_reuses_existing_token(self):
        profile = OnionProfileFactory(slug='claim-existing', verification_token='existing-token')

        client = Client()

        with patch('profiles.views.profile_views.get_service') as mock_views_get:
            mock_verification = MagicMock()
            mock_views_get.return_value = mock_verification

            response = client.get(f'/site/{profile.slug}/claim/')

            assert response.status_code == 200
            mock_verification.start_verification.assert_not_called()
            assert response.context['verification_token'] == 'existing-token'

    def test_claim_view_post_success_links_owner(self):
        profile = OnionProfileFactory(slug='claim-success', owner=None)
        user = User.objects.create_user(username='siteowner', password='pw')
        contributor = ContributorFactory(user=user, trust_level=TrustLevel.NEW)

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.profile_views.get_service') as mock_views_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_verification = MagicMock()
            mock_verification.check_verification.return_value = True
            mock_views_get.return_value = mock_verification

            response = client.post(
                f'/site/{profile.slug}/claim/', data={'confirm': 'on'}
            )

            assert response.status_code == 302
            profile.refresh_from_db()
            assert profile.owner_id == user.id

    def test_claim_view_post_failure_does_not_link_owner(self):
        profile = OnionProfileFactory(slug='claim-fail', owner=None)

        client = Client()

        with patch('profiles.views.profile_views.get_service') as mock_views_get:
            mock_verification = MagicMock()
            mock_verification.check_verification.return_value = False
            mock_views_get.return_value = mock_verification

            response = client.post(
                f'/site/{profile.slug}/claim/', data={'confirm': 'on'}
            )

            assert response.status_code == 302
            profile.refresh_from_db()
            assert profile.owner is None


class TestProfileHistoryView:
    def test_history_view_renders(self):
        profile = OnionProfileFactory(slug='history-view')

        client = Client()

        with patch('profiles.views.profile_views.get_service'):
            response = client.get(f'/site/{profile.slug}/history/')

            assert response.status_code == 200

    def test_history_view_context_includes_domain_history_and_edits(self):
        profile = OnionProfileFactory(slug='history-context')
        DomainHistoryFactory(profile=profile)
        ProfileEditFactory(profile=profile)

        client = Client()

        with patch('profiles.views.profile_views.get_service'):
            response = client.get(f'/site/{profile.slug}/history/')

            assert response.context['domain_history'].count() == 1
            assert response.context['recent_edits'].count() == 1
