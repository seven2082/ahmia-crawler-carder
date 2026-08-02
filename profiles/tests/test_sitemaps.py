import pytest
from django.urls import reverse

from profiles.sitemaps import ProfileSitemap, CategorySitemap, ProfileStaticSitemap

pytestmark = pytest.mark.django_db


class TestProfileSitemap:
    def test_sitemap_items(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.constants import ProfileStatus

        active = OnionProfileFactory(status=ProfileStatus.ACTIVE)
        offline = OnionProfileFactory(status=ProfileStatus.OFFLINE)

        sitemap = ProfileSitemap()
        items = list(sitemap.items())

        assert active in items
        assert offline not in items

    def test_sitemap_location(self):
        from profiles.tests.factories import OnionProfileFactory

        profile = OnionProfileFactory(slug='test-site')

        sitemap = ProfileSitemap()
        location = sitemap.location(profile)

        assert location == '/site/test-site/'


class TestCategorySitemap:
    def test_sitemap_items(self):
        from profiles.models import Category

        Category.objects.create(name='Forum', slug='forum')

        sitemap = CategorySitemap()
        items = list(sitemap.items())

        assert len(items) == 1

    def test_sitemap_location(self):
        from profiles.models import Category

        category = Category.objects.create(name='Forum', slug='forum')

        sitemap = CategorySitemap()
        location = sitemap.location(category)

        assert location == '/site/category/forum/'


class TestProfileStaticSitemap:
    def test_static_pages(self):
        sitemap = ProfileStaticSitemap()
        items = sitemap.items()

        assert 'profiles:list' in items
        assert 'profiles:category_list' in items
