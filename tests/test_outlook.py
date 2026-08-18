from datetime import datetime, timezone
from types import SimpleNamespace

from email_source.outlook import OutlookComSource


NOW = datetime(2026, 8, 18, 14, 0, 0).timestamp()


class FakeItems:
    def __init__(self, items):
        self._items = items

    @property
    def Count(self):
        return len(self._items)

    def Sort(self, field, descending):
        assert field == "[ReceivedTime]"
        assert descending is True

    def Item(self, index):
        return self._items[index - 1]


def fake_item(**overrides):
    values = {
        "EntryID": "entry-1",
        "MessageClass": "IPM.Note",
        "ReceivedTime": datetime.fromtimestamp(NOW - 10),
        "Subject": "[SSO] 통합로그인 인증코드",
        "SenderName": "INNOCEAN Single Sign-On",
        "SenderEmailType": "SMTP",
        "SenderEmailAddress": "sso@example.invalid",
        "Body": "인증코드 [123456]",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def source(**overrides):
    values = {
        "subject_keywords": ["[SSO] 통합로그인 인증코드"],
        "sender_display_names": ["INNOCEAN Single Sign-On"],
        "allowed_sender_addresses": [],
        "otp_pattern": r"인증코드\s*\[\s*([0-9]{6})\s*\]",
        "max_age_seconds": 90,
        "time_fn": lambda: NOW,
    }
    values.update(overrides)
    return OutlookComSource(**values)


def test_expected_message_metadata_matches():
    assert source()._metadata_matches(fake_item(), NOW)[0] is True


def test_outlook_aware_datetime_is_interpreted_as_local_wall_clock():
    outlook_value = datetime(2026, 8, 18, 14, 0, 0, tzinfo=timezone.utc)
    local_value = datetime(2026, 8, 18, 14, 0, 0).timestamp()
    assert source()._timestamp(outlook_value) == local_value


def test_wrong_subject_is_rejected_before_body_access():
    assert source()._metadata_matches(fake_item(Subject="Weekly report"), NOW)[0] is False


def test_wrong_sender_display_name_is_rejected():
    assert source()._metadata_matches(fake_item(SenderName="Unknown"), NOW)[0] is False


def test_address_allowlist_takes_precedence_over_display_name():
    configured = source(allowed_sender_addresses=["trusted@example.invalid"])
    assert configured._metadata_matches(
        fake_item(SenderName="INNOCEAN Single Sign-On", SenderEmailAddress="other@example.invalid"), NOW
    )[0] is False


def test_expired_message_is_rejected():
    old = fake_item(ReceivedTime=datetime.fromtimestamp(NOW - 91))
    assert source()._metadata_matches(old, NOW)[0] is False


def test_future_message_beyond_clock_tolerance_is_rejected():
    future = fake_item(ReceivedTime=datetime.fromtimestamp(NOW + 31))
    assert source()._metadata_matches(future, NOW)[0] is False


def test_diagnostic_reports_counts_without_content():
    inbox = SimpleNamespace(Items=FakeItems([fake_item(), fake_item(EntryID="entry-2", Subject="Other")]))
    session = SimpleNamespace(
        Stores=SimpleNamespace(Count=1),
        GetDefaultFolder=lambda folder: inbox,
    )
    diagnostic = source(session_factory=lambda: session).diagnose()
    assert diagnostic.com_available is True
    assert diagnostic.inbox_available is True
    assert diagnostic.recent_messages_checked == 2
    assert diagnostic.metadata_matches == 1
    assert diagnostic.received_within_30_minutes == 2
    assert diagnostic.subject_matches == 1
    assert diagnostic.sender_matches == 1
    assert diagnostic.body_pattern_matches == 1
    assert diagnostic.newest_message_age_seconds == 10


def test_invalid_pattern_without_single_capture_group_is_rejected():
    try:
        source(otp_pattern=r"[0-9]{6}")
    except ValueError as exc:
        assert "one capture group" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_listener_baselines_existing_mail_and_yields_only_new_match():
    existing = fake_item(EntryID="existing", Body="인증코드 [111111]")
    items = FakeItems([existing])
    inbox = SimpleNamespace(Items=items)
    session = SimpleNamespace(GetDefaultFolder=lambda folder: inbox)
    added = False

    def add_new_mail(_seconds):
        nonlocal added
        if not added:
            items._items.insert(0, fake_item(EntryID="new", Body="인증코드 [222222]"))
            added = True

    listener = source(session_factory=lambda: session, sleep_fn=add_new_mail)
    messages = listener.messages()
    message = next(messages)
    messages.close()

    assert message.text == "otp 222222"
    assert "111111" not in message.text
