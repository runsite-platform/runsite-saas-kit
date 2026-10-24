from dataclasses import dataclass

from app.constants.enums import NotificationKind


@dataclass(frozen=True)
class NotificationKindPolicy:
    email_default: bool
    user_configurable: bool = True


# Add new kinds here and in NotificationKind.
NOTIFICATION_POLICIES: dict[NotificationKind, NotificationKindPolicy] = {
    NotificationKind.WELCOME: NotificationKindPolicy(email_default=False),
    NotificationKind.MEMBER_JOINED: NotificationKindPolicy(email_default=True),
    NotificationKind.MEMBER_ROLE_CHANGED: NotificationKindPolicy(email_default=True),
    NotificationKind.MEMBER_REMOVED: NotificationKindPolicy(email_default=True, user_configurable=False),
    NotificationKind.OWNERSHIP_TRANSFERRED: NotificationKindPolicy(email_default=True, user_configurable=False),
    NotificationKind.SYSTEM: NotificationKindPolicy(email_default=True, user_configurable=False),
}


def is_email_enabled(kind: NotificationKind, stored_value: bool | None) -> bool:
    """Return whether a notification of this kind is emailed, given the user's stored setting."""
    policy = NOTIFICATION_POLICIES[kind]
    if not policy.user_configurable or stored_value is None:
        return policy.email_default
    return stored_value


def user_configurable_kinds() -> list[NotificationKind]:
    """Return the kinds a user can turn on or off, in declaration order."""
    return [kind for kind, policy in NOTIFICATION_POLICIES.items() if policy.user_configurable]
