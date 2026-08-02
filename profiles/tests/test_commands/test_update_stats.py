import pytest
from io import StringIO
from django.core.management import call_command
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.django_db


class TestUpdateStatsCommand:
    def test_update_all_stats(self):
        out = StringIO()

        with patch('profiles.management.commands.update_stats.get_service') as mock_get:
            mock_sync = MagicMock()
            mock_sync.update_all_stats.return_value = 10
            mock_get.return_value = mock_sync

            call_command('update_stats', stdout=out)

            output = out.getvalue()
            assert 'Updated 10 profiles' in output

    def test_update_single_profile(self):
        from profiles.tests.factories import OnionProfileFactory

        profile = OnionProfileFactory(slug='test-site')
        out = StringIO()

        with patch('profiles.management.commands.update_stats.get_service') as mock_get:
            mock_sync = MagicMock()
            mock_get.return_value = mock_sync

            call_command('update_stats', '--profile=test-site', stdout=out)

            output = out.getvalue()
            assert 'Updated stats for test-site' in output
            mock_sync.update_profile_stats.assert_called_once()

    def test_update_nonexistent_profile(self):
        out = StringIO()

        call_command('update_stats', '--profile=nonexistent', stdout=out)

        output = out.getvalue()
        assert 'Profile not found' in output
