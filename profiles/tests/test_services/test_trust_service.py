import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from datetime import timedelta
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _session_request():
    request = RequestFactory().get('/')
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request.user = AnonymousUser()
    return request


class TestTrustService:
    def test_get_or_create_contributor(self):
        from profiles.services.trust_service import TrustService

        request = _session_request()
        service = TrustService()

        contributor = service.get_or_create_contributor(request)

        assert contributor.pk is not None
        assert contributor.session_key == request.session.session_key

    def test_can_edit_normal_contributor(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService

        contributor = ContributorFactory()
        service = TrustService()

        assert service.can_edit(contributor) is True

    def test_can_edit_banned_contributor(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService

        contributor = ContributorFactory(is_banned=True)
        service = TrustService()

        assert service.can_edit(contributor) is False

    def test_can_edit_on_cooldown(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService

        contributor = ContributorFactory(cooldown_until=timezone.now() + timedelta(hours=1))
        service = TrustService()

        assert service.can_edit(contributor) is False

    def test_can_review_trusted_contributor(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService
        from profiles.constants import TrustLevel

        contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
        service = TrustService()

        assert service.can_review(contributor) is True

    def test_can_review_new_contributor(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService
        from profiles.constants import TrustLevel

        contributor = ContributorFactory(trust_level=TrustLevel.NEW)
        service = TrustService()

        assert service.can_review(contributor) is False

    def test_can_review_banned_contributor(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService
        from profiles.constants import TrustLevel

        contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED, is_banned=True)
        service = TrustService()

        assert service.can_review(contributor) is False

    def test_can_moderate(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService
        from profiles.constants import TrustLevel

        contributor = ContributorFactory(trust_level=TrustLevel.MODERATOR)
        service = TrustService()

        assert service.can_moderate(contributor) is True

    def test_can_moderate_non_moderator(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService
        from profiles.constants import TrustLevel

        contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
        service = TrustService()

        assert service.can_moderate(contributor) is False

    def test_can_moderate_banned_moderator(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService
        from profiles.constants import TrustLevel

        contributor = ContributorFactory(trust_level=TrustLevel.MODERATOR, is_banned=True)
        service = TrustService()

        assert service.can_moderate(contributor) is False

    def test_promote_to_moderator(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService
        from profiles.constants import TrustLevel

        contributor = ContributorFactory(trust_level=TrustLevel.TRUSTED)
        service = TrustService()

        service.promote_to_moderator(contributor)

        contributor.refresh_from_db()
        assert contributor.trust_level == TrustLevel.MODERATOR

    def test_ban_contributor(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService

        contributor = ContributorFactory(is_banned=False)
        service = TrustService()

        service.ban_contributor(contributor)

        contributor.refresh_from_db()
        assert contributor.is_banned is True

    def test_unban_contributor(self):
        from profiles.tests.factories import ContributorFactory
        from profiles.services.trust_service import TrustService

        contributor = ContributorFactory(is_banned=True)
        service = TrustService()

        service.unban_contributor(contributor)

        contributor.refresh_from_db()
        assert contributor.is_banned is False
