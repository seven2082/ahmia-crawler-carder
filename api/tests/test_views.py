from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from profiles.models import OnionProfile, Category


@override_settings(AHMIA_API_KEY='test-api-key')
class ProfileListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Test', slug='test')

    def test_list_requires_api_key(self):
        response = self.client.get('/api/v1/profiles/')
        self.assertIn(response.status_code, [401, 403])

    def test_list_returns_profiles_with_valid_key(self):
        OnionProfile.objects.create(
            slug='site-one',
            current_domain='one.onion',
            name='Site One',
            category=self.category
        )
        OnionProfile.objects.create(
            slug='site-two',
            current_domain='two.onion',
            name='Site Two',
            category=self.category
        )

        response = self.client.get(
            '/api/v1/profiles/',
            HTTP_X_API_KEY='test-api-key'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_filters_by_updated_since(self):
        from django.utils import timezone
        from datetime import timedelta
        from urllib.parse import quote

        old_time = timezone.now() - timedelta(days=10)
        old_profile = OnionProfile.objects.create(
            slug='old-site',
            current_domain='old.onion',
            name='Old Site',
            category=self.category
        )
        OnionProfile.objects.filter(id=old_profile.id).update(updated_at=old_time)
        old_profile.refresh_from_db()

        OnionProfile.objects.create(
            slug='new-site',
            current_domain='new.onion',
            name='New Site',
            category=self.category
        )

        since = (timezone.now() - timedelta(days=5)).isoformat()
        since_encoded = quote(since, safe='')

        response = self.client.get(
            f'/api/v1/profiles/?updated_since={since_encoded}',
            HTTP_X_API_KEY='test-api-key'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['slug'], 'new-site')


@override_settings(AHMIA_API_KEY='test-api-key')
class ProfileDetailViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Test', slug='test')
        self.profile = OnionProfile.objects.create(
            slug='my-site',
            current_domain='mysite.onion',
            name='My Site',
            category=self.category
        )

    def test_detail_by_slug(self):
        response = self.client.get(
            '/api/v1/profiles/my-site/',
            HTTP_X_API_KEY='test-api-key'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['slug'], 'my-site')
        self.assertEqual(response.data['current_domain'], 'mysite.onion')

    def test_detail_returns_404_for_unknown_slug(self):
        response = self.client.get(
            '/api/v1/profiles/unknown-site/',
            HTTP_X_API_KEY='test-api-key'
        )

        self.assertEqual(response.status_code, 404)


@override_settings(AHMIA_API_KEY='test-api-key')
class ProfileByDomainViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name='Test', slug='test')
        self.profile = OnionProfile.objects.create(
            slug='domain-site',
            current_domain='abc123xyz.onion',
            name='Domain Site',
            category=self.category
        )

    def test_lookup_by_domain(self):
        response = self.client.get(
            '/api/v1/profiles/by-domain/abc123xyz.onion/',
            HTTP_X_API_KEY='test-api-key'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['slug'], 'domain-site')

    def test_domain_lookup_returns_404_for_unknown(self):
        response = self.client.get(
            '/api/v1/profiles/by-domain/unknown.onion/',
            HTTP_X_API_KEY='test-api-key'
        )

        self.assertEqual(response.status_code, 404)
