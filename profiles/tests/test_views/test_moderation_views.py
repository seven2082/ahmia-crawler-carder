import pytest
from django.test import Client
from django.urls import reverse
from unittest.mock import patch, MagicMock

from profiles.constants import TrustLevel, EditStatus
from profiles.tests.factories import (
    ContributorFactory,
    ProfileEditFactory,
    MigrationReportFactory,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls('profiles.tests.test_views.test_urlconf')]


class TestModerationQueueView:
    def test_queue_view_requires_trust(self):
        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get:
            contributor = ContributorFactory(trust_level=TrustLevel.ANONYMOUS)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            response = client.get('/site/moderate/')
            assert response.status_code == 302  # Redirected due to low trust

    def test_queue_view_renders_for_trusted(self):
        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.moderation_views.get_service') as mock_views_get:
            contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_service = MagicMock()
            mock_service.count_pending.return_value = 0
            mock_views_get.return_value = mock_service

            response = client.get('/site/moderate/')
            assert response.status_code == 200
            assert response.context['pending_count'] == 0

    def test_queue_view_lists_pending_edits_only(self):
        pending_edit = ProfileEditFactory(status=EditStatus.PENDING)
        ProfileEditFactory(status=EditStatus.APPROVED)

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.moderation_views.get_service') as mock_views_get:
            contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_service = MagicMock()
            mock_service.count_pending.return_value = 1
            mock_views_get.return_value = mock_service

            response = client.get('/site/moderate/')
            items = list(response.context['items'])
            assert items == [pending_edit]

    def test_queue_view_includes_pending_migrations(self):
        migration = MigrationReportFactory(status=EditStatus.PENDING)
        MigrationReportFactory(status=EditStatus.APPROVED)

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.moderation_views.get_service') as mock_views_get:
            contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_service = MagicMock()
            mock_service.count_pending.return_value = 0
            mock_views_get.return_value = mock_service

            response = client.get('/site/moderate/')
            assert list(response.context['pending_migrations']) == [migration]


class TestEditReviewView:
    def test_review_view_requires_trust(self):
        edit = ProfileEditFactory()

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get:
            contributor = ContributorFactory(trust_level=TrustLevel.ANONYMOUS)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            response = client.get(f'/site/moderate/edit/{edit.id}/')
            assert response.status_code == 302

    def test_review_view_renders(self):
        edit = ProfileEditFactory()

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get:
            contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            response = client.get(f'/site/moderate/edit/{edit.id}/')
            assert response.status_code == 200
            assert response.context['edit'] == edit
            assert response.context['profile'] == edit.profile

    def test_review_view_approve_calls_service_and_redirects(self):
        edit = ProfileEditFactory()

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.moderation_views.get_service') as mock_views_get:
            contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_service = MagicMock()
            mock_views_get.return_value = mock_service

            response = client.post(
                f'/site/moderate/edit/{edit.id}/',
                data={'action': 'approve', 'notes': 'Looks good'}
            )

            assert response.status_code == 302
            assert response.url == reverse('profiles:moderation_queue')
            mock_service.approve_edit.assert_called_once_with(edit, contributor, 'Looks good')

    def test_review_view_reject_calls_service_and_redirects(self):
        edit = ProfileEditFactory()

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.moderation_views.get_service') as mock_views_get:
            contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_service = MagicMock()
            mock_views_get.return_value = mock_service

            response = client.post(
                f'/site/moderate/edit/{edit.id}/',
                data={'action': 'reject', 'notes': 'Spam'}
            )

            assert response.status_code == 302
            assert response.url == reverse('profiles:moderation_queue')
            mock_service.reject_edit.assert_called_once_with(edit, contributor, 'Spam')


class TestMigrationReviewView:
    def test_review_view_requires_moderator(self):
        migration = MigrationReportFactory()

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get:
            contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            response = client.get(f'/site/moderate/migration/{migration.id}/')
            assert response.status_code == 302  # TRUSTED is not enough; requires MODERATOR

    def test_review_view_renders_for_moderator(self):
        migration = MigrationReportFactory()

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get:
            contributor = ContributorFactory(trust_level=TrustLevel.MODERATOR)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            response = client.get(f'/site/moderate/migration/{migration.id}/')
            assert response.status_code == 200
            assert response.context['migration'] == migration
            assert response.context['profile'] == migration.profile

    def test_review_view_approve_calls_service_and_redirects(self):
        migration = MigrationReportFactory()

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.moderation_views.get_service') as mock_views_get:
            contributor = ContributorFactory(trust_level=TrustLevel.MODERATOR)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_service = MagicMock()
            mock_views_get.return_value = mock_service

            response = client.post(
                f'/site/moderate/migration/{migration.id}/',
                data={'action': 'approve', 'notes': ''}
            )

            assert response.status_code == 302
            assert response.url == reverse('profiles:moderation_queue')
            mock_service.approve_migration.assert_called_once_with(migration, contributor, '')

    def test_review_view_reject_calls_service_and_redirects(self):
        migration = MigrationReportFactory()

        client = Client()

        with patch('profiles.views.mixins.get_service') as mock_mixin_get, \
                patch('profiles.views.moderation_views.get_service') as mock_views_get:
            contributor = ContributorFactory(trust_level=TrustLevel.MODERATOR)
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_mixin_get.return_value = mock_trust

            mock_service = MagicMock()
            mock_views_get.return_value = mock_service

            response = client.post(
                f'/site/moderate/migration/{migration.id}/',
                data={'action': 'reject', 'notes': 'Not enough evidence'}
            )

            assert response.status_code == 302
            assert response.url == reverse('profiles:moderation_queue')
            mock_service.reject_migration.assert_called_once_with(
                migration, contributor, 'Not enough evidence'
            )
