import pytest
from io import StringIO
from django.core.management import call_command
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.django_db


class TestSyncProfilesCommand:
    def test_sync_profiles_success(self):
        out = StringIO()

        with patch('profiles.management.commands.sync_profiles.get_service') as mock_get:
            mock_sync = MagicMock()
            mock_sync.sync_all_profiles.return_value = {
                'created': 5,
                'skipped': 10,
                'total_domains': 15
            }
            mock_get.return_value = mock_sync

            call_command('sync_profiles', stdout=out)

            output = out.getvalue()
            assert '5 created' in output
            assert '10 skipped' in output

    def test_sync_profiles_dry_run(self):
        out = StringIO()

        with patch('profiles.management.commands.sync_profiles.get_service') as mock_get:
            mock_sync = MagicMock()
            mock_sync.sync_all_profiles.return_value = {
                'created': 0,
                'skipped': 0,
                'total_domains': 0
            }
            mock_get.return_value = mock_sync

            call_command('sync_profiles', '--dry-run', stdout=out)

            output = out.getvalue()
            assert 'DRY RUN' in output
