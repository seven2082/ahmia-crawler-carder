import pytest
from io import StringIO
from django.core.management import call_command

from profiles.models import Category

pytestmark = pytest.mark.django_db


class TestSeedCategoriesCommand:
    def test_seed_creates_categories(self):
        out = StringIO()

        call_command('seed_categories', stdout=out)

        output = out.getvalue()
        assert 'created' in output
        assert Category.objects.filter(slug='forum').exists()
        assert Category.objects.filter(slug='other').exists()

    def test_seed_idempotent(self):
        call_command('seed_categories')
        initial_count = Category.objects.count()

        call_command('seed_categories')
        final_count = Category.objects.count()

        assert initial_count == final_count

    def test_seed_with_force_updates(self):
        Category.objects.create(slug='forum', name='Old Name', description='Old')

        out = StringIO()
        call_command('seed_categories', '--force', stdout=out)

        forum = Category.objects.get(slug='forum')
        assert forum.name == 'Forum'
        assert 'updated' in out.getvalue()
