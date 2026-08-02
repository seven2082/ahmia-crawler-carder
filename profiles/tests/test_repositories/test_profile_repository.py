import pytest

pytestmark = pytest.mark.django_db


class TestProfileRepository:
    def test_get_by_slug(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.repositories import ProfileRepository

        profile = OnionProfileFactory(slug='test-repo-slug')
        repo = ProfileRepository()

        found = repo.get_by_slug('test-repo-slug')
        assert found.id == profile.id

    def test_get_by_slug_not_found(self):
        from profiles.repositories import ProfileRepository
        from profiles.exceptions import ProfileNotFoundError

        repo = ProfileRepository()
        with pytest.raises(ProfileNotFoundError):
            repo.get_by_slug('nonexistent')

    def test_get_by_domain(self):
        from profiles.tests.factories import OnionProfileFactory
        from profiles.repositories import ProfileRepository

        domain = 'repodomain567890abcdef1234567890abcdef1234567890abcdefgh.onion'
        profile = OnionProfileFactory(current_domain=domain)
        repo = ProfileRepository()

        found = repo.get_by_domain(domain)
        assert found.id == profile.id

    def test_list_by_category(self):
        from profiles.tests.factories import OnionProfileFactory, CategoryFactory
        from profiles.repositories import ProfileRepository

        cat = CategoryFactory(slug='test-cat')
        OnionProfileFactory(category=cat)
        OnionProfileFactory(category=cat)
        OnionProfileFactory()  # Different category

        repo = ProfileRepository()
        results = repo.list_by_category('test-cat')

        assert len(results) == 2
