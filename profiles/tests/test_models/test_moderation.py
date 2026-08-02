import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db

class TestProfileEdit:
    def test_edit_creation(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.models import ProfileEdit
        from profiles.constants import EditStatus

        profile = OnionProfileFactory()
        contrib = ContributorFactory()

        edit = ProfileEdit.objects.create(
            profile=profile,
            field_name='description',
            old_value='Old description',
            new_value='New description',
            submitted_by=contrib
        )
        assert edit.status == EditStatus.PENDING
        assert edit.reviewed_by is None

    def test_edit_apply(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.models import ProfileEdit
        from profiles.constants import EditStatus

        profile = OnionProfileFactory(description='Original')
        contrib = ContributorFactory()
        reviewer = ContributorFactory()

        edit = ProfileEdit.objects.create(
            profile=profile,
            field_name='description',
            old_value='Original',
            new_value='Updated description',
            submitted_by=contrib
        )
        edit.approve(reviewer)

        profile.refresh_from_db()
        assert profile.description == 'Updated description'
        assert edit.status == EditStatus.APPROVED
        assert edit.reviewed_by == reviewer


class TestMigrationReport:
    def test_migration_creation(self):
        from profiles.tests.factories import OnionProfileFactory, ContributorFactory
        from profiles.models import MigrationReport
        from profiles.constants import MigrationSource

        profile = OnionProfileFactory()
        contrib = ContributorFactory()

        report = MigrationReport.objects.create(
            profile=profile,
            old_domain=profile.current_domain,
            new_domain='newdomain567890abcdef1234567890abcdef1234567890abcdefgh.onion',
            source=MigrationSource.COMMUNITY,
            submitted_by=contrib
        )
        assert report.status == 'pending'
