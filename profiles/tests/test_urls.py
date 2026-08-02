import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestURLConfiguration:
    def test_list_url_resolves(self):
        url = reverse('profiles:list')
        assert url == '/site/'

    def test_detail_url_resolves(self):
        url = reverse('profiles:detail', kwargs={'slug': 'test-site'})
        assert url == '/site/test-site/'

    def test_edit_url_resolves(self):
        url = reverse('profiles:edit', kwargs={'slug': 'test-site'})
        assert url == '/site/test-site/edit/'

    def test_claim_url_resolves(self):
        url = reverse('profiles:claim', kwargs={'slug': 'test-site'})
        assert url == '/site/test-site/claim/'

    def test_history_url_resolves(self):
        url = reverse('profiles:history', kwargs={'slug': 'test-site'})
        assert url == '/site/test-site/history/'

    def test_category_list_url_resolves(self):
        url = reverse('profiles:category_list')
        assert url == '/site/categories/'

    def test_category_detail_url_resolves(self):
        url = reverse('profiles:category_detail', kwargs={'slug': 'forum'})
        assert url == '/site/category/forum/'

    def test_tag_list_url_resolves(self):
        url = reverse('profiles:tag_list')
        assert url == '/site/tags/'

    def test_tag_detail_url_resolves(self):
        url = reverse('profiles:tag_detail', kwargs={'slug': 'security'})
        assert url == '/site/tag/security/'

    def test_moderation_queue_url_resolves(self):
        url = reverse('profiles:moderation_queue')
        assert url == '/site/moderate/'

    def test_edit_review_url_resolves(self):
        url = reverse('profiles:edit_review', kwargs={'edit_id': 42})
        assert url == '/site/moderate/edit/42/'

    def test_migration_review_url_resolves(self):
        url = reverse('profiles:migration_review', kwargs={'migration_id': 42})
        assert url == '/site/moderate/migration/42/'
