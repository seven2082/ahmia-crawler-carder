import pytest
from django.test import Client
from unittest.mock import patch, MagicMock

pytestmark = [pytest.mark.django_db, pytest.mark.urls('profiles.tests.test_views.test_urlconf')]


class TestCategoryListView:
    def test_list_view_renders(self):
        from profiles.models import Category

        Category.objects.create(name='Forum', slug='forum')
        Category.objects.create(name='Market', slug='market')

        client = Client()

        with patch('profiles.views.directory_views.ContributorMixin.get_contributor') as mock:
            mock.return_value = MagicMock()
            response = client.get('/site/categories/')
            assert response.status_code == 200

    def test_list_view_orders_by_name(self):
        from profiles.models import Category

        Category.objects.create(name='Zebra', slug='zebra')
        Category.objects.create(name='Alpha', slug='alpha')

        client = Client()

        with patch('profiles.views.directory_views.ContributorMixin.get_contributor') as mock:
            mock.return_value = MagicMock()
            response = client.get('/site/categories/')
            names = [c.name for c in response.context['categories']]
            assert names == ['Alpha', 'Zebra']


class TestCategoryDetailView:
    def test_detail_view_renders(self):
        from profiles.models import Category
        from profiles.tests.factories import OnionProfileFactory

        category = Category.objects.create(name='Forum', slug='forum')
        OnionProfileFactory(category=category)

        client = Client()

        with patch('profiles.views.directory_views.ContributorMixin.get_contributor') as mock:
            mock.return_value = MagicMock()
            response = client.get('/site/category/forum/')
            assert response.status_code == 200

    def test_detail_view_lists_only_profiles_in_category(self):
        from profiles.models import Category
        from profiles.tests.factories import OnionProfileFactory

        forum = Category.objects.create(name='Forum', slug='forum')
        market = Category.objects.create(name='Market', slug='market')
        forum_profile = OnionProfileFactory(category=forum)
        OnionProfileFactory(category=market)

        client = Client()

        with patch('profiles.views.directory_views.ContributorMixin.get_contributor') as mock:
            mock.return_value = MagicMock()
            response = client.get('/site/category/forum/')
            assert list(response.context['profiles']) == [forum_profile]


class TestTagListView:
    def test_list_view_renders(self):
        from profiles.models import Tag

        Tag.objects.create(name='privacy', slug='privacy')

        client = Client()

        with patch('profiles.views.directory_views.ContributorMixin.get_contributor') as mock:
            mock.return_value = MagicMock()
            response = client.get('/site/tags/')
            assert response.status_code == 200

    def test_list_view_orders_by_profile_count_desc(self):
        from profiles.models import Tag
        from profiles.tests.factories import OnionProfileFactory

        popular = Tag.objects.create(name='popular', slug='popular')
        rare = Tag.objects.create(name='rare', slug='rare')
        p1 = OnionProfileFactory()
        p1.tags.add(popular)
        p2 = OnionProfileFactory()
        p2.tags.add(popular)
        p3 = OnionProfileFactory()
        p3.tags.add(rare)

        client = Client()

        with patch('profiles.views.directory_views.ContributorMixin.get_contributor') as mock:
            mock.return_value = MagicMock()
            response = client.get('/site/tags/')
            slugs = [t.slug for t in response.context['tags']]
            assert slugs == ['popular', 'rare']


class TestTagDetailView:
    def test_detail_view_renders(self):
        from profiles.models import Tag
        from profiles.tests.factories import OnionProfileFactory

        tag = Tag.objects.create(name='privacy', slug='privacy')
        profile = OnionProfileFactory()
        profile.tags.add(tag)

        client = Client()

        with patch('profiles.views.directory_views.ContributorMixin.get_contributor') as mock:
            mock.return_value = MagicMock()
            response = client.get('/site/tag/privacy/')
            assert response.status_code == 200
            assert profile in response.context['profiles']
