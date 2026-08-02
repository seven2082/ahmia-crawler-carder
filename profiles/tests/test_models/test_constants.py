from profiles.constants import TrustLevel, ProfileStatus, EditStatus


def test_trust_level_ordering():
    assert TrustLevel.ANONYMOUS < TrustLevel.NEW
    assert TrustLevel.NEW < TrustLevel.TRUSTED
    assert TrustLevel.TRUSTED < TrustLevel.MODERATOR


def test_profile_status_choices():
    slugs = [c[0] for c in ProfileStatus.CHOICES]
    assert 'active' in slugs
    assert 'offline' in slugs
    assert 'banned' in slugs


def test_edit_status_choices():
    slugs = [c[0] for c in EditStatus.CHOICES]
    assert 'pending' in slugs
    assert 'approved' in slugs
    assert 'rejected' in slugs
