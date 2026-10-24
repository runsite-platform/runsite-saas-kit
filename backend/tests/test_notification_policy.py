from app.constants.enums import NotificationKind
from app.services.notification_policy import NOTIFICATION_POLICIES, is_email_enabled, user_configurable_kinds

MANDATORY_KINDS = (NotificationKind.MEMBER_REMOVED, NotificationKind.OWNERSHIP_TRANSFERRED, NotificationKind.SYSTEM)


def test_every_kind_has_a_policy() -> None:
    assert set(NOTIFICATION_POLICIES) == set(NotificationKind)


def test_default_is_used_when_nothing_is_stored() -> None:
    assert is_email_enabled(NotificationKind.WELCOME, None) is False
    assert is_email_enabled(NotificationKind.MEMBER_JOINED, None) is True


def test_stored_value_wins_for_configurable_kinds() -> None:
    assert is_email_enabled(NotificationKind.WELCOME, True) is True
    assert is_email_enabled(NotificationKind.MEMBER_JOINED, False) is False


def test_mandatory_kinds_ignore_the_stored_value() -> None:
    for kind in MANDATORY_KINDS:
        assert is_email_enabled(kind, False) is True


def test_user_configurable_kinds_leave_out_mandatory_ones() -> None:
    assert user_configurable_kinds() == [
        NotificationKind.WELCOME,
        NotificationKind.MEMBER_JOINED,
        NotificationKind.MEMBER_ROLE_CHANGED,
    ]
