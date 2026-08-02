import pytest
from django.utils import timezone
from datetime import timedelta

pytestmark = pytest.mark.django_db

class TestContributor:
    def test_contributor_creation_anonymous(self):
        from profiles.models import Contributor
        from profiles.constants import TrustLevel
        contrib = Contributor.objects.create(
            session_key='abc123session',
            ip_hash='hashedipabc123'
        )
        assert contrib.trust_level == TrustLevel.ANONYMOUS
        assert contrib.user is None
        assert contrib.can_auto_approve is False

    def test_contributor_trust_upgrade(self):
        from profiles.models import Contributor
        from profiles.constants import TrustLevel, TRUST_LEVEL_THRESHOLD
        contrib = Contributor.objects.create(
            session_key='upgrade123',
            ip_hash='hashedip456',
            approved_edits=TRUST_LEVEL_THRESHOLD
        )
        contrib.recalculate_trust_level()
        assert contrib.trust_level == TrustLevel.TRUSTED
        assert contrib.can_auto_approve is True

    def test_contributor_cooldown(self):
        from profiles.models import Contributor
        contrib = Contributor.objects.create(
            session_key='cooldown123',
            ip_hash='hashedip789',
            cooldown_until=timezone.now() + timedelta(hours=12)
        )
        assert contrib.is_on_cooldown is True

    def test_contributor_not_on_cooldown(self):
        from profiles.models import Contributor
        contrib = Contributor.objects.create(
            session_key='nocooldown',
            ip_hash='hashedip000'
        )
        assert contrib.is_on_cooldown is False
