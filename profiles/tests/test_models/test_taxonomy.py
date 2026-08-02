import pytest
from django.db import IntegrityError

pytestmark = pytest.mark.django_db

class TestCategory:
    def test_category_creation(self):
        from profiles.models import Category
        cat = Category.objects.create(
            name='Marketplace',
            slug='marketplace',
            description='Buy and sell goods',
            icon='🛒'
        )
        assert cat.name == 'Marketplace'
        assert cat.slug == 'marketplace'
        assert str(cat) == 'Marketplace'

    def test_category_slug_unique(self):
        from profiles.models import Category
        Category.objects.create(name='Forum', slug='forum')
        with pytest.raises(IntegrityError):
            Category.objects.create(name='Forum 2', slug='forum')

    def test_category_annotate_profile_count(self):
        from profiles.models import Category
        from profiles.tests.factories import OnionProfileFactory

        forum = Category.objects.create(name='Forum', slug='forum')
        market = Category.objects.create(name='Market', slug='market')
        OnionProfileFactory(category=forum)
        OnionProfileFactory(category=forum)

        counts = {
            c.slug: c.profile_count
            for c in Category.objects.annotate_profile_count()
        }
        assert counts['forum'] == 2
        assert counts['market'] == 0


class TestTag:
    def test_tag_creation(self):
        from profiles.models import Tag
        tag = Tag.objects.create(name='crypto', slug='crypto')
        assert tag.name == 'crypto'
        assert tag.is_approved is False
        assert str(tag) == 'crypto'

    def test_tag_approval(self):
        from profiles.models import Tag
        tag = Tag.objects.create(name='escrow', slug='escrow', is_approved=True)
        assert tag.is_approved is True

    def test_tag_annotate_profile_count(self):
        from profiles.models import Tag
        from profiles.tests.factories import OnionProfileFactory

        privacy = Tag.objects.create(name='privacy', slug='privacy')
        unused = Tag.objects.create(name='unused', slug='unused')
        profile = OnionProfileFactory()
        profile.tags.add(privacy)

        counts = {
            t.slug: t.profile_count
            for t in Tag.objects.annotate_profile_count()
        }
        assert counts['privacy'] == 1
        assert counts['unused'] == 0
