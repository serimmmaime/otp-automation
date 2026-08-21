from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Iterator


@dataclass(frozen=True)
class OutlookMessage:
    """A redaction-safe message passed to the existing OTP parser."""

    text: str
    detected_at: float


@dataclass(frozen=True)
class OutlookDiagnostic:
    com_available: bool
    session_available: bool
    stores: int
    inbox_available: bool
    recent_messages_checked: int
    metadata_matches: int
    received_within_30_minutes: int
    subject_matches: int
    sender_matches: int
    body_pattern_matches: int
    newest_message_age_seconds: int | None
    access_errors: int


class OutlookComSource:
    """Poll Classic Outlook through its supported local COM object model.

    Messages are never modified. Existing items are baselined at startup, and
    message bodies are read only after sender, subject, and age checks pass.
    """

    OL_FOLDER_INBOX = 6

    def __init__(
        self,
        subject_keywords: Iterable[str],
        sender_display_names: Iterable[str],
        allowed_sender_addresses: Iterable[str],
        otp_pattern: str,
        max_age_seconds: float = 90,
        poll_interval: float = 2,
        max_items: int = 50,
        session_factory: Callable[[], object] | None = None,
        time_fn: Callable[[], float] = time.time,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.subject_keywords = tuple(k.casefold() for k in subject_keywords)
        self.sender_display_names = tuple(k.casefold() for k in sender_display_names)
        self.allowed_sender_addresses = tuple(k.casefold() for k in allowed_sender_addresses)
        self.otp_pattern = re.compile(otp_pattern, re.IGNORECASE)
        if self.otp_pattern.groups != 1:
            raise ValueError("Email OTP pattern must contain exactly one capture group")
        self.max_age_seconds = float(max_age_seconds)
        self.poll_interval = float(poll_interval)
        self.max_items = int(max_items)
        self._session_factory = session_factory
        self._time = time_fn
        self._sleep = sleep_fn

    @staticmethod
    def _fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()

    def _open_session(self) -> object:
        if self._session_factory:
            return self._session_factory()
        import win32com.client

        application = win32com.client.Dispatch("Outlook.Application")
        return application.GetNamespace("MAPI")

    @staticmethod
    def _timestamp(value: object) -> float:
        if isinstance(value, datetime):
            # Outlook Object Model's ReceivedTime is a local wall-clock value.
            # Some pywin32/Outlook combinations attach a UTC tzinfo without
            # converting those fields, which shifts Korean local time by +9h.
            return value.replace(tzinfo=None).timestamp()
        timestamp = getattr(value, "timestamp", None)
        if callable(timestamp):
            return float(timestamp())
        raise ValueError("Unsupported Outlook ReceivedTime value")

    @staticmethod
    def _sender_address(item: object) -> str:
        try:
            address = str(getattr(item, "SenderEmailAddress", "") or "")
            if str(getattr(item, "SenderEmailType", "") or "").upper() != "EX":
                return address
            sender = getattr(item, "Sender", None)
            exchange_user = sender.GetExchangeUser() if sender else None
            primary = str(getattr(exchange_user, "PrimarySmtpAddress", "") or "")
            return primary or address
        except Exception:
            return ""

    def _metadata_checks(
        self, item: object, now: float, max_age_seconds: float
    ) -> tuple[bool, bool, bool, float]:
        try:
            if str(getattr(item, "MessageClass", "") or "") != "IPM.Note":
                return False, False, False, 0
            received_at = self._timestamp(getattr(item, "ReceivedTime"))
            age = now - received_at
            age_match = -30 <= age <= max_age_seconds
            subject = str(getattr(item, "Subject", "") or "").casefold()
            subject_match = any(keyword in subject for keyword in self.subject_keywords)
            if self.allowed_sender_addresses:
                sender = self._sender_address(item).casefold()
                sender_match = sender in self.allowed_sender_addresses
            else:
                display_name = str(getattr(item, "SenderName", "") or "").casefold()
                sender_match = display_name in self.sender_display_names
            return age_match, subject_match, sender_match, received_at
        except Exception:
            return False, False, False, 0

    def _metadata_matches(self, item: object, now: float) -> tuple[bool, float]:
        age, subject, sender, received_at = self._metadata_checks(
            item, now, self.max_age_seconds
        )
        return age and subject and sender, received_at

    def _recent_items(self, inbox: object) -> list[object]:
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)
        count = min(int(items.Count), self.max_items)
        return [items.Item(index) for index in range(1, count + 1)]

    def _item_key(self, item: object) -> str:
        entry_id = str(getattr(item, "EntryID", "") or "")
        if entry_id:
            return self._fingerprint(entry_id)
        fallback = "|".join(
            str(getattr(item, name, "") or "")
            for name in ("ReceivedTime", "Subject", "SenderName")
        )
        return self._fingerprint(fallback)

    def diagnose(self) -> OutlookDiagnostic:
        try:
            session = self._open_session()
        except Exception:
            return OutlookDiagnostic(False, False, 0, False, 0, 0, 0, 0, 0, 0, None, 1)
        try:
            stores = int(getattr(session.Stores, "Count", 0))
            inbox = session.GetDefaultFolder(self.OL_FOLDER_INBOX)
            items = self._recent_items(inbox)
            now = self._time()
            matches = sum(self._metadata_matches(item, now)[0] for item in items)
            age_matches = 0
            subject_matches = 0
            sender_matches = 0
            body_matches = 0
            received_times: list[float] = []
            for item in items:
                age, subject, sender, received_at = self._metadata_checks(item, now, 1800)
                if received_at:
                    received_times.append(received_at)
                age_matches += int(age)
                subject_matches += int(subject)
                sender_matches += int(subject and sender)
                if subject and sender:
                    body = str(getattr(item, "Body", "") or "")
                    body_matches += int(bool(self.otp_pattern.search(body)))
            newest_age = int(now - max(received_times)) if received_times else None
            return OutlookDiagnostic(
                True, True, stores, True, len(items), matches,
                age_matches, subject_matches, sender_matches, body_matches, newest_age, 0,
            )
        except Exception:
            return OutlookDiagnostic(True, True, 0, False, 0, 0, 0, 0, 0, 0, None, 1)

    def messages(
        self,
        on_idle: Callable[[], None] | None = None,
        on_ready: Callable[[], None] | None = None,
    ) -> Iterator[OutlookMessage]:
        import pythoncom

        pythoncom.CoInitialize()
        try:
            session = self._open_session()
            inbox = session.GetDefaultFolder(self.OL_FOLDER_INBOX)
            # 재부팅 실패 원인: 이전 구현은 시작 시 보이는 메일을 전부 baseline에
            # 넣어서, Windows/Outlook 초기화 중 먼저 도착한 새 OTP까지 영구히
            # 무시했다. 오래됐거나 무관한 메일만 baseline에 넣고, 아직 유효한
            # OTP는 첫 poll에서 처리한다. 만료 검사와 deduplicator가 재사용을 막는다.
            now = self._time()
            baseline = {
                self._item_key(item)
                for item in self._recent_items(inbox)
                if not self._metadata_matches(item, now)[0]
            }
            if on_ready:
                on_ready()
            last_idle = self._time()
            while True:
                now = self._time()
                for item in self._recent_items(inbox):
                    key = self._item_key(item)
                    if key in baseline:
                        continue
                    baseline.add(key)
                    matches, received_at = self._metadata_matches(item, now)
                    if not matches:
                        continue
                    body = str(getattr(item, "Body", "") or "")
                    match = self.otp_pattern.search(body)
                    if not match:
                        continue
                    code = match.group(1)
                    # Only a minimal synthetic string leaves this source.
                    yield OutlookMessage(text=f"otp {code}", detected_at=received_at)
                if on_idle and now - last_idle >= 30:
                    on_idle()
                    last_idle = now
                self._sleep(self.poll_interval)
        finally:
            pythoncom.CoUninitialize()
