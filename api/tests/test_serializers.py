from django.test import TestCase
from django.contrib.auth import get_user_model
from profiles.models import OnionProfile, Category, DomainHistory
from api.serializers import ProfileSerializer, DomainHistorySerializer

User = get_user_model()


class DomainHistorySerializerTest(TestCase):
    def test_serializes_domain_history(self):
        category = Category.objects.create(name='Test', slug='test')
        profile = OnionProfile.objects.create(
            slug='test-site',
            current_domain='test.onion',
            name='Test Site',
            category=category
        )
        history = DomainHistory.objects.create(
            profile=profile,
            domain='old.onion',
            was_active_from='2025-01-01',
            was_active_to='2026-01-01',
            migration_type='owner'
        )

        serializer = DomainHistorySerializer(history)
        data = serializer.data

        self.assertEqual(data['domain'], 'old.onion')
        self.assertEqual(data['migration_type'], 'owner')


class ProfileSerializerTest(TestCase):
    def test_serializes_profile_with_all_fields(self):
        category = Category.objects.create(name='Marketplace', slug='marketplace')
        user = User.objects.create_user(username='testowner', password='test')
        profile = OnionProfile.objects.create(
            slug='test-market',
            current_domain='market.onion',
            name='Test Market',
            description='A test marketplace',
            category=category,
            is_verified=True,
            owner=user,
            page_count=42,
            status='active'
        )

        serializer = ProfileSerializer(profile)
        data = serializer.data

        self.assertEqual(data['slug'], 'test-market')
        self.assertEqual(data['current_domain'], 'market.onion')
        self.assertEqual(data['name'], 'Test Market')
        self.assertEqual(data['category'], 'Marketplace')
        self.assertEqual(data['is_verified'], True)
        self.assertEqual(data['owner_username'], 'testowner')
        self.assertEqual(data['page_count'], 42)

    def test_verified_at_returns_none_when_not_verified(self):
        category = Category.objects.create(name='Test', slug='test')
        profile = OnionProfile.objects.create(
            slug='unverified',
            current_domain='unverified.onion',
            name='Unverified',
            category=category,
            is_verified=False
        )

        serializer = ProfileSerializer(profile)
        self.assertIsNone(serializer.data['verified_at'])
