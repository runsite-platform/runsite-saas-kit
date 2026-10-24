import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.constants.enums import NotificationKind, OrgRole
from app.models.notification import Notification
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.schemas.notifications import NotificationEmailSettingItem
from app.services.notification_service import NotificationEmail, NotificationService
from tests.factories import add_member, auth_headers, create_invitation, create_organization, create_user
from tests.fakes import InMemoryEmailSender

NOTIFICATIONS_URL = "/api/me/notifications"


class ListEmailQueue:
    def __init__(self) -> None:
        self.emails: list[NotificationEmail] = []

    def enqueue(self, email: NotificationEmail) -> None:
        self.emails.append(email)


async def notify(session: AsyncSession, user: User, title: str = "Hello") -> Notification:
    notifications = await NotificationService(session).notify(
        [user], kind=NotificationKind.SYSTEM, title=title, body="Body text", link="/app"
    )
    return notifications[0]


async def notifications_for(session: AsyncSession, user: User) -> list[Notification]:
    return list(await session.scalars(select(Notification).where(Notification.user_id == user.id)))


async def test_lists_only_own_notifications_newest_first(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    other_user = await create_user(db_session)
    await notify(db_session, user, "First")
    await notify(db_session, user, "Second")
    await notify(db_session, other_user, "Not mine")

    response = await client.get(NOTIFICATIONS_URL, headers=await auth_headers(user, settings=settings))

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["unread_count"] == 2
    assert {item["title"] for item in payload["items"]} == {"First", "Second"}
    assert payload["items"][0]["body"] == "Body text"
    assert payload["items"][0]["read_at"] is None


async def test_filters_and_marks_read_and_unread(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    first_notification = await notify(db_session, user, "First")
    await notify(db_session, user, "Second")
    headers = await auth_headers(user, settings=settings)

    read_response = await client.patch(
        f"{NOTIFICATIONS_URL}/{first_notification.id}", json={"is_read": True}, headers=headers
    )
    assert read_response.status_code == 200
    assert read_response.json()["read_at"] is not None

    read_list = (await client.get(NOTIFICATIONS_URL, params={"filter": "read"}, headers=headers)).json()
    unread_list = (await client.get(NOTIFICATIONS_URL, params={"filter": "unread"}, headers=headers)).json()
    assert [item["title"] for item in read_list["items"]] == ["First"]
    assert [item["title"] for item in unread_list["items"]] == ["Second"]
    assert unread_list["unread_count"] == 1

    unread_response = await client.patch(
        f"{NOTIFICATIONS_URL}/{first_notification.id}", json={"is_read": False}, headers=headers
    )
    assert unread_response.json()["read_at"] is None
    count_response = await client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=headers)
    assert count_response.json() == {"unread_count": 2}


async def test_mark_all_read_and_delete_read(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    await notify(db_session, user)
    await notify(db_session, user)
    headers = await auth_headers(user, settings=settings)

    assert (await client.post(f"{NOTIFICATIONS_URL}/read-all", headers=headers)).status_code == 204
    assert (await client.get(f"{NOTIFICATIONS_URL}/unread-count", headers=headers)).json() == {"unread_count": 0}

    await notify(db_session, user, "Fresh")
    assert (await client.delete(f"{NOTIFICATIONS_URL}/read", headers=headers)).status_code == 204
    remaining = await notifications_for(db_session, user)
    assert [notification.title for notification in remaining] == ["Fresh"]


async def test_cannot_touch_someone_elses_notification(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    stranger = await create_user(db_session)
    notification = await notify(db_session, owner)
    headers = await auth_headers(stranger, settings=settings)

    notification_url = f"{NOTIFICATIONS_URL}/{notification.id}"
    patch_response = await client.patch(notification_url, json={"is_read": True}, headers=headers)
    delete_response = await client.delete(f"{NOTIFICATIONS_URL}/{notification.id}", headers=headers)

    assert patch_response.status_code == 404
    assert delete_response.status_code == 404
    assert len(await notifications_for(db_session, owner)) == 1


async def test_deletes_own_notification(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    notification = await notify(db_session, user)

    response = await client.delete(
        f"{NOTIFICATIONS_URL}/{notification.id}", headers=await auth_headers(user, settings=settings)
    )

    assert response.status_code == 204
    assert await notifications_for(db_session, user) == []


async def test_requires_authentication(client: httpx.AsyncClient) -> None:
    response = await client.get(NOTIFICATIONS_URL)
    assert response.status_code == 401


async def test_email_settings_default_and_update(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    headers = await auth_headers(user, settings=settings)

    default_response = await client.get(f"{NOTIFICATIONS_URL}/settings", headers=headers)
    assert default_response.status_code == 200
    default_settings = {item["kind"]: item["email_enabled"] for item in default_response.json()["settings"]}
    assert default_settings["welcome"] is False
    assert default_settings["member_joined"] is True
    assert default_response.json()["email_delivery_available"] is False

    update_response = await client.put(
        f"{NOTIFICATIONS_URL}/settings",
        json={
            "settings": [
                {"kind": "member_joined", "email_enabled": False},
                {"kind": "welcome", "email_enabled": True},
            ]
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated_settings = {item["kind"]: item["email_enabled"] for item in update_response.json()["settings"]}
    assert updated_settings["member_joined"] is False
    assert updated_settings["welcome"] is True

    second_update = await client.put(
        f"{NOTIFICATIONS_URL}/settings",
        json={"settings": [{"kind": "member_joined", "email_enabled": True}]},
        headers=headers,
    )
    assert {item["kind"]: item["email_enabled"] for item in second_update.json()["settings"]}["member_joined"] is True


async def test_rejects_unknown_notification_kind(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session)
    response = await client.put(
        f"{NOTIFICATIONS_URL}/settings",
        json={"settings": [{"kind": "nope", "email_enabled": True}]},
        headers=await auth_headers(user, settings=settings),
    )
    assert response.status_code == 422


async def test_notify_queues_email_only_when_enabled(db_session: AsyncSession) -> None:
    subscribed_user = await create_user(db_session)
    opted_out_user = await create_user(db_session)
    blocked_user = await create_user(db_session, is_blocked=True)
    email_queue = ListEmailQueue()
    service = NotificationService(db_session, email_queue)
    await service.update_email_settings(
        opted_out_user.id,
        [NotificationEmailSettingItem(kind=NotificationKind.MEMBER_JOINED, email_enabled=False)],
    )

    created = await service.notify(
        [subscribed_user, opted_out_user, blocked_user, subscribed_user],
        kind=NotificationKind.MEMBER_JOINED,
        title="Someone joined",
    )

    assert {notification.user_id for notification in created} == {subscribed_user.id, opted_out_user.id}
    assert [email.to for email in email_queue.emails] == [subscribed_user.email]


async def test_welcome_kind_is_not_emailed_by_default(db_session: AsyncSession) -> None:
    user = await create_user(db_session)
    email_queue = ListEmailQueue()

    await NotificationService(db_session, email_queue).notify([user], kind=NotificationKind.WELCOME, title="Hi")

    assert email_queue.emails == []


async def test_signup_creates_welcome_notification(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"email": "welcome@example.com", "password": "password123", "full_name": "New Person"},
    )
    assert response.status_code in (200, 201)

    user = await db_session.scalar(select(User).where(User.email == "welcome@example.com"))
    assert user is not None
    kinds = [notification.kind for notification in await notifications_for(db_session, user)]
    assert kinds == [NotificationKind.WELCOME]


async def test_accepting_invitation_notifies_managers_and_emails_them(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings, email_outbox: InMemoryEmailSender
) -> None:
    owner = await create_user(db_session)
    admin = await create_user(db_session)
    plain_member = await create_user(db_session)
    invitee = await create_user(db_session, email="joiner@example.com", full_name="Jo Joiner")
    organization = await create_organization(db_session, owner=owner, plan_id="pro")
    await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)
    await add_member(db_session, organization=organization, user=plain_member)
    _invitation, token = await create_invitation(
        db_session, organization=organization, invited_by=owner, email="joiner@example.com"
    )

    response = await client.post(
        f"/api/invitations/{token}/accept", headers=await auth_headers(invitee, settings=settings)
    )

    assert response.status_code == 200
    for manager in (owner, admin):
        manager_notifications = await notifications_for(db_session, manager)
        assert [notification.kind for notification in manager_notifications] == [NotificationKind.MEMBER_JOINED]
        assert manager_notifications[0].title == f"Jo Joiner joined {organization.name}"
        assert manager_notifications[0].link == f"/app/{organization.slug}/members"
    assert await notifications_for(db_session, plain_member) == []
    assert sorted(message.to for message in email_outbox.sent) == sorted([owner.email, admin.email])
    assert email_outbox.sent[0].subject == f"Jo Joiner joined {organization.name}"
    assert f"http://testserver/app/{organization.slug}/members" in email_outbox.sent[0].text
    assert "http://testserver/notifications" in email_outbox.sent[0].text


async def test_role_change_and_removal_notify_the_member(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    member = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, plan_id="pro")
    membership = await add_member(db_session, organization=organization, user=member)
    headers = await auth_headers(owner, settings=settings)
    members_url = f"/api/orgs/{organization.id}/members/{membership.id}"

    assert (await client.patch(members_url, json={"role": "admin"}, headers=headers)).status_code == 200
    assert (await client.delete(members_url, headers=headers)).status_code == 204

    kinds = sorted(notification.kind for notification in await notifications_for(db_session, member))
    assert kinds == sorted([NotificationKind.MEMBER_ROLE_CHANGED, NotificationKind.MEMBER_REMOVED])


async def test_leaving_does_not_notify_yourself(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    member = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner)
    membership = await add_member(db_session, organization=organization, user=member)

    response = await client.delete(
        f"/api/orgs/{organization.id}/members/{membership.id}", headers=await auth_headers(member, settings=settings)
    )

    assert response.status_code == 204
    assert await notifications_for(db_session, member) == []


async def test_ownership_transfer_notifies_new_owner(
    client: httpx.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    owner = await create_user(db_session)
    admin = await create_user(db_session)
    organization = await create_organization(db_session, owner=owner, plan_id="pro")
    admin_membership = await add_member(db_session, organization=organization, user=admin, role=OrgRole.ADMIN)

    response = await client.post(
        f"/api/orgs/{organization.id}/transfer-ownership",
        json={"membership_id": str(admin_membership.id)},
        headers=await auth_headers(owner, settings=settings),
    )

    assert response.status_code == 204
    notifications = await notifications_for(db_session, admin)
    assert [notification.kind for notification in notifications] == [NotificationKind.OWNERSHIP_TRANSFERRED]
    assert await MembershipRepository(db_session).get_for_user(organization.id, admin.id) is not None
