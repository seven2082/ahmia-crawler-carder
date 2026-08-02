import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta

pytestmark = pytest.mark.django_db


class TestVerificationService:
    def test_start_verification_generates_token(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.verification_service import VerificationService

        profile = OnionProfileFactory()
        service = VerificationService()

        token = service.start_verification(profile)

        assert len(token) == 64
        assert profile.verification_token == token
        assert profile.verification_token_expires is not None

    def test_check_verification_success(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.verification_service import VerificationService

        profile = OnionProfileFactory()
        token = profile.generate_verification_token()

        service = VerificationService()

        with patch.object(service, '_fetch_verification_file') as mock_fetch:
            mock_fetch.return_value = f'ahmia-token={token}'

            result = service.check_verification(profile)

            assert result is True
            profile.refresh_from_db()
            assert profile.is_verified is True

    def test_check_verification_wrong_token(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.verification_service import VerificationService

        profile = OnionProfileFactory()
        profile.generate_verification_token()

        service = VerificationService()

        with patch.object(service, '_fetch_verification_file') as mock_fetch:
            mock_fetch.return_value = 'ahmia-token=wrongtoken'

            result = service.check_verification(profile)

            assert result is False
            profile.refresh_from_db()
            assert profile.verification_fail_count == 1

    def test_revoke_verification(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.services.verification_service import VerificationService

        profile = OnionProfileFactory(is_verified=True)
        profile.generate_verification_token()

        service = VerificationService()
        service.revoke_verification(profile)

        profile.refresh_from_db()
        assert profile.is_verified is False
        assert profile.verification_token == ''
