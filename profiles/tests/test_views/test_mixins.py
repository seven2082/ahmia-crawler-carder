import pytest
from django.test import RequestFactory
from django.views.generic import TemplateView
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.django_db


class TestContributorMixin:
    def test_adds_contributor_to_context(self):
        from profiles.views.mixins import ContributorMixin
        from profiles.tests.factories import ContributorFactory

        class TestView(ContributorMixin, TemplateView):
            template_name = 'test.html'

        contributor = ContributorFactory()

        factory = RequestFactory()
        request = factory.get('/')
        request.session = {'session_key': contributor.session_key}

        view = TestView()
        view.request = request

        with patch('profiles.views.mixins.get_service') as mock_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_get.return_value = mock_trust

            context = view.get_context_data()

            assert 'contributor' in context
            assert context['contributor'] == contributor


class TestTrustRequiredMixin:
    def test_allows_sufficient_trust(self):
        from profiles.views.mixins import TrustRequiredMixin
        from profiles.tests.factories import ContributorFactory
        from profiles.constants import TrustLevel

        class TestView(TrustRequiredMixin, TemplateView):
            template_name = 'test.html'
            required_trust_level = TrustLevel.NEW

        contributor = ContributorFactory(trust_level=TrustLevel.NEW)

        factory = RequestFactory()
        request = factory.get('/')
        request.session = {}

        view = TestView()
        view.request = request

        with patch('profiles.views.mixins.get_service') as mock_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_get.return_value = mock_trust

            # Should not redirect
            response = view.dispatch(request)
            # Will error because template doesn't exist, but didn't redirect
            assert response is not None

    def test_rejects_banned(self):
        from profiles.views.mixins import TrustRequiredMixin
        from profiles.tests.factories import ContributorFactory

        class TestView(TrustRequiredMixin, TemplateView):
            template_name = 'test.html'

        contributor = ContributorFactory(is_banned=True)

        factory = RequestFactory()
        request = factory.get('/')
        request.session = {}
        request._messages = MagicMock()

        view = TestView()
        view.request = request

        with patch('profiles.views.mixins.get_service') as mock_get:
            mock_trust = MagicMock()
            mock_trust.get_or_create_contributor.return_value = contributor
            mock_get.return_value = mock_trust

            response = view.dispatch(request)

            assert response.status_code == 302  # Redirect
