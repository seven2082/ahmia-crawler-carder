import pytest
from io import StringIO
from django.core.management import call_command
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.django_db


class TestCheckVerificationsCommand:
    def test_check_pending_verifications(self):
        from profiles.tests.factories import OnionProfileFactory

        OnionProfileFactory(verification_token='abc123', is_verified=False)
        OnionProfileFactory(verification_token='def456', is_verified=False)

        out = StringIO()

        with patch('profiles.management.commands.check_verifications.get_service') as mock_get:
            mock_verify = MagicMock()
            mock_verify.check_verification.return_value = True
            mock_get.return_value = mock_verify

            call_command('check_verifications', stdout=out)

            output = out.getvalue()
            assert '2 verified' in output

    def test_check_specific_profile(self):
        from profiles.tests.factories import OnionProfileFactory

        profile = OnionProfileFactory(slug='my-site', verification_token='xyz')

        out = StringIO()

        with patch('profiles.management.commands.check_verifications.get_service') as mock_get:
            mock_verify = MagicMock()
            mock_verify.check_verification.return_value = True
            mock_get.return_value = mock_verify

            call_command('check_verifications', '--profile=my-site', stdout=out)

            output = out.getvalue()
            assert 'my-site: VERIFIED' in output
