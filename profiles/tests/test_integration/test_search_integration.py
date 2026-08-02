from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.django_db


class TestProfileRepositoryDomainLookup:
    """ProfileRepository.get_profiles_for_domains used by search results integration."""

    def test_profiles_for_domains(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.repositories import ProfileRepository

        profile1 = OnionProfileFactory(current_domain='site1.onion')
        profile2 = OnionProfileFactory(current_domain='site2.onion')

        repo = ProfileRepository()
        result = repo.get_profiles_for_domains(['site1.onion', 'site2.onion', 'unknown.onion'])

        assert 'site1.onion' in result
        assert 'site2.onion' in result
        assert 'unknown.onion' not in result
        assert result['site1.onion'].slug == profile1.slug
        assert result['site2.onion'].slug == profile2.slug

    def test_empty_domains_list(self):
        from profiles.repositories import ProfileRepository

        repo = ProfileRepository()
        result = repo.get_profiles_for_domains([])

        assert result == {}


class TestProfileTagsTemplateFilter:
    """profiles.templatetags.profile_tags.get_item"""

    def test_get_item_returns_value_for_existing_key(self):
        from profiles.templatetags.profile_tags import get_item

        data = {'site1.onion': 'profile-object'}
        assert get_item(data, 'site1.onion') == 'profile-object'

    def test_get_item_returns_none_for_missing_key(self):
        from profiles.templatetags.profile_tags import get_item

        data = {'site1.onion': 'profile-object'}
        assert get_item(data, 'unknown.onion') is None

    def test_get_item_handles_none_dictionary(self):
        from profiles.templatetags.profile_tags import get_item

        assert get_item(None, 'site1.onion') is None


class TestTorResultsViewProfileIntegration:
    """TorResultsView.get_context_data attaches domain_profiles for search results."""

    def _make_view(self, hits):
        from ahmia.views import TorResultsView

        view = TorResultsView()
        view.object_list = SimpleNamespace(total=len(hits), hits=hits, suggest=None)
        return view

    def test_context_includes_domain_profiles_for_matching_results(self):
        from profiles.tests.factories import OnionProfileFactory

        profile = OnionProfileFactory(current_domain='matched1234567890abcdef1234567890abcdef1234567890abc.onion')
        hits = [
            {
                'url': f'http://{profile.current_domain}/page',
                'title': 'Matched result',
                'meta': '',
                'domain': profile.current_domain,
                'updated_on': None,
            },
            {
                'url': 'http://unknown1234567890abcdef1234567890abcdef1234567890a.onion/',
                'title': 'Unmatched result',
                'meta': '',
                'domain': 'unknown1234567890abcdef1234567890abcdef1234567890a.onion',
                'updated_on': None,
            },
        ]
        view = self._make_view(hits)

        context = view.get_context_data(q='test', page=0, time=0.1)

        assert 'domain_profiles' in context
        assert profile.current_domain in context['domain_profiles']
        assert context['domain_profiles'][profile.current_domain].slug == profile.slug
        assert 'unknown1234567890abcdef1234567890abcdef1234567890a.onion' not in context['domain_profiles']

    def test_context_domain_profiles_empty_when_no_results(self):
        view = self._make_view([])

        context = view.get_context_data(q='test', page=0, time=0.1)

        assert context['domain_profiles'] == {}

    def test_extract_domain_from_url(self):
        from ahmia.views import TorResultsView

        view = TorResultsView()
        domain = view._extract_domain('http://exampleabc1234567890abcdef1234567890abcdef1234567.onion/page?x=1')

        assert domain == 'exampleabc1234567890abcdef1234567890abcdef1234567.onion'
