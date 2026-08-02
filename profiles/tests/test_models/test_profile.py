import pytest
from django.utils import timezone
from datetime import timedelta

pytestmark = pytest.mark.django_db

class TestOnionProfile:
    def test_profile_creation(self):
        from profiles.models import OnionProfile, Category
        cat = Category.objects.create(name='Other', slug='other')
        profile = OnionProfile.objects.create(
            slug='test-site',
            current_domain='testsite1234567890abcdef1234567890abcdef1234567890abcdefgh.onion',
            name='Test Site',
            description='A test onion site',
            category=cat
        )
        assert profile.slug == 'test-site'
        assert profile.is_verified is False
        assert profile.status == 'active'
        assert str(profile) == 'Test Site'

    def test_profile_domain_unique(self):
        from profiles.models import OnionProfile, Category
        from django.db import IntegrityError
        cat = Category.objects.create(name='Other', slug='other')
        domain = 'unique12345678901234567890123456789012345678901234567890ab.onion'
        OnionProfile.objects.create(slug='site-1', current_domain=domain, name='Site 1', category=cat)
        with pytest.raises(IntegrityError):
            OnionProfile.objects.create(slug='site-2', current_domain=domain, name='Site 2', category=cat)

    def test_profile_verification_token_generation(self):
        from profiles.models import OnionProfile, Category
        cat = Category.objects.create(name='Other', slug='other')
        profile = OnionProfile.objects.create(
            slug='verify-test',
            current_domain='verifytest234567890abcdef1234567890abcdef1234567890abcd.onion',
            name='Verify Test',
            category=cat
        )
        token = profile.generate_verification_token()
        assert len(token) == 64
        assert profile.verification_token == token
        assert profile.verification_token_expires > timezone.now()


class TestDomainHistory:
    def test_domain_history_creation(self):
        from profiles.models import OnionProfile, DomainHistory, Category
        cat = Category.objects.create(name='Other', slug='other')
        profile = OnionProfile.objects.create(
            slug='history-test',
            current_domain='historytest34567890abcdef1234567890abcdef1234567890abc.onion',
            name='History Test',
            category=cat
        )
        history = DomainHistory.objects.create(
            profile=profile,
            domain='oldhistory234567890abcdef1234567890abcdef1234567890abcde.onion',
            was_active_from=timezone.now() - timedelta(days=365),
            was_active_to=timezone.now() - timedelta(days=30),
            migration_type='community'
        )
        assert history.profile == profile
        assert history.migration_type == 'community'
