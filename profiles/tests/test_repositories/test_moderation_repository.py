import pytest

pytestmark = pytest.mark.django_db

class TestModerationRepository:
    def test_get_pending_edits(self):
        from profiles.tests.factories import ProfileEditFactory
        from profiles.repositories import ModerationRepository
        from profiles.constants import EditStatus

        ProfileEditFactory(status=EditStatus.PENDING)
        ProfileEditFactory(status=EditStatus.PENDING)
        ProfileEditFactory(status=EditStatus.APPROVED)

        repo = ModerationRepository()
        pending = repo.get_pending_edits()

        assert pending.count() == 2

    def test_get_pending_migrations(self):
        from profiles.tests.factories import MigrationReportFactory
        from profiles.repositories import ModerationRepository
        from profiles.constants import EditStatus

        MigrationReportFactory(status=EditStatus.PENDING)
        MigrationReportFactory(status=EditStatus.REJECTED)

        repo = ModerationRepository()
        pending = repo.get_pending_migrations()

        assert pending.count() == 1

    def test_get_edits_for_profile(self):
        from profiles.tests.factories import ProfileEditFactory, OnionProfileFactory
        from profiles.repositories import ModerationRepository

        profile = OnionProfileFactory()
        ProfileEditFactory(profile=profile)
        ProfileEditFactory(profile=profile)
        ProfileEditFactory()  # Different profile

        repo = ModerationRepository()
        edits = repo.get_edits_for_profile(profile.id)

        assert edits.count() == 2

    def test_get_edit_by_id(self):
        from profiles.tests.factories import ProfileEditFactory
        from profiles.repositories import ModerationRepository

        edit = ProfileEditFactory()

        repo = ModerationRepository()
        result = repo.get_edit_by_id(edit.id)

        assert result == edit

    def test_get_migration_by_id(self):
        from profiles.tests.factories import MigrationReportFactory
        from profiles.repositories import ModerationRepository

        migration = MigrationReportFactory()

        repo = ModerationRepository()
        result = repo.get_migration_by_id(migration.id)

        assert result == migration

    def test_count_pending(self):
        from profiles.tests.factories import ProfileEditFactory, MigrationReportFactory
        from profiles.repositories import ModerationRepository
        from profiles.constants import EditStatus

        ProfileEditFactory(status=EditStatus.PENDING)
        ProfileEditFactory(status=EditStatus.PENDING)
        ProfileEditFactory(status=EditStatus.APPROVED)
        MigrationReportFactory(status=EditStatus.PENDING)
        MigrationReportFactory(status=EditStatus.REJECTED)

        repo = ModerationRepository()
        counts = repo.count_pending()

        assert counts == {'edits': 2, 'migrations': 1}
