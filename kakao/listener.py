from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator

from pywinauto import Desktop


@dataclass(frozen=True)
class KakaoMessage:
    text: str
    detected_at: float


@dataclass(frozen=True)
class KakaoDiagnostic:
    desktop_windows: int
    title_matched_windows: int
    notification_matched_windows: int
    text_blocks: int
    access_errors: int
    candidates: tuple["KakaoWindowDiagnostic", ...]


@dataclass(frozen=True)
class KakaoWindowDiagnostic:
    class_name: str
    text_blocks: int
    kakao_title_match: bool
    notification_title_match: bool
    kakao_app_marker: bool
    otp_keyword_marker: bool
    digit_candidate_marker: bool
    otp_and_digit_marker: bool


class KakaoUiListener:
    """Read text exposed by KakaoTalk through Windows UI Automation.

    This listener does not access KakaoTalk databases, inject into the process,
    or use undocumented Kakao APIs. It only observes UIA text exposed by Windows.
    """

    def __init__(
        self,
        title_keywords: Iterable[str],
        notification_app_keywords: Iterable[str] = ("kakao", "카카오톡"),
        notification_window_title_keywords: Iterable[str] = ("notification", "알림"),
        notification_window_class_names: Iterable[str] = ("Chrome_WidgetWin_1",),
        notification_max_text_blocks: int = 12,
        notification_max_width: int = 700,
        notification_max_height: int = 500,
        otp_keywords: Iterable[str] = ("인증번호", "인증코드", "otp", "verification code"),
        listen_kakao_windows: bool = False,
        listen_kakao_notifications: bool = False,
        kakao_window_digit_only_otp_length: int = 6,
        poll_interval: float = 0.5,
        dedupe_ttl_seconds: float = 600,
    ):
        self.title_keywords = tuple(k.lower() for k in title_keywords)
        self.notification_app_keywords = tuple(k.lower() for k in notification_app_keywords)
        self.notification_window_title_keywords = tuple(
            k.lower() for k in notification_window_title_keywords
        )
        self.notification_window_class_names = tuple(
            name.lower() for name in notification_window_class_names
        )
        self.notification_max_text_blocks = int(notification_max_text_blocks)
        self.notification_max_width = int(notification_max_width)
        self.notification_max_height = int(notification_max_height)
        self.otp_keywords = tuple(k.lower() for k in otp_keywords)
        self.listen_kakao_windows = bool(listen_kakao_windows)
        self.listen_kakao_notifications = bool(listen_kakao_notifications)
        self.kakao_window_digit_only_otp_length = int(kakao_window_digit_only_otp_length)
        self.poll_interval = max(0.1, float(poll_interval))
        self.dedupe_ttl_seconds = max(30.0, float(dedupe_ttl_seconds))
        self._seen: dict[str, float] = {}

    def _is_kakao_window(self, title: str) -> bool:
        lowered = (title or "").lower()
        return any(k in lowered for k in self.title_keywords)

    def _is_notification_window(self, title: str) -> bool:
        lowered = (title or "").lower()
        return any(k in lowered for k in self.notification_window_title_keywords)

    @staticmethod
    def _fingerprint(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def _scan(
        self,
        include_kakao_windows: bool | None = None,
        exhaustive: bool = False,
    ) -> tuple[list[str], KakaoDiagnostic]:
        if include_kakao_windows is None:
            include_kakao_windows = self.listen_kakao_windows
        texts: list[str] = []
        try:
            desktop = Desktop(backend="uia")
            windows = desktop.windows()
        except Exception:
            return texts, KakaoDiagnostic(
                desktop_windows=0,
                title_matched_windows=0,
                notification_matched_windows=0,
                text_blocks=0,
                access_errors=1,
                candidates=(),
            )
        title_matches = 0
        notification_matches = 0
        access_errors = 0
        candidates: list[KakaoWindowDiagnostic] = []
        for window in windows:
            try:
                window_title = window.window_text()
                window_is_kakao = self._is_kakao_window(window_title)
                window_is_notification = self._is_notification_window(window_title)
                element_info = getattr(window, "element_info", None)
                window_class = str(getattr(element_info, "class_name", "") or "")
                window_has_notification_class = (
                    window_class.lower() in self.notification_window_class_names
                )
                window_is_desktop_host = window_class.lower() == "progman"
                try:
                    rectangle = window.rectangle()
                    window_is_small = bool(
                        rectangle.width() <= self.notification_max_width
                        and rectangle.height() <= self.notification_max_height
                    )
                except Exception:
                    window_is_small = True
                window_is_structural_host = bool(
                    window_has_notification_class
                    and (window_is_small or window_is_desktop_host)
                )
                if (
                    not exhaustive
                    and not (
                        self.listen_kakao_notifications
                        and (window_is_notification or window_is_structural_host)
                    )
                    and not (include_kakao_windows and window_is_kakao)
                ):
                    if window_is_kakao:
                        title_matches += 1
                    continue
                window_texts: list[str] = []
                window_pane_otp_candidates: list[str] = []
                for ctrl in window.descendants():
                    control_type = str(
                        getattr(ctrl.element_info, "control_type", "") or ""
                    )
                    control_texts: list[str] = []
                    try:
                        text = ctrl.window_text().strip()
                    except Exception:
                        text = ""
                    if text:
                        control_texts.append(text)
                    try:
                        accessible_name = str(
                            getattr(ctrl.element_info, "name", "") or ""
                        ).strip()
                    except Exception:
                        accessible_name = ""
                    if accessible_name and accessible_name not in control_texts:
                        control_texts.append(accessible_name)
                    for candidate_text in control_texts:
                        if len(candidate_text) >= 4 and candidate_text not in window_texts:
                            window_texts.append(candidate_text)
                        if window_is_kakao and control_type == "Pane":
                            digit_matches = re.findall(
                                rf"(?<![0-9])[0-9]{{{self.kakao_window_digit_only_otp_length}}}(?![0-9])",
                                candidate_text,
                            )
                            if len(digit_matches) == 1:
                                synthetic_candidate = f"인증번호 {digit_matches[0]}"
                                if synthetic_candidate not in window_pane_otp_candidates:
                                    window_pane_otp_candidates.append(synthetic_candidate)
                # Windows notification toasts are not necessarily titled
                # "KakaoTalk". Accept them only when the UIA subtree exposes an
                # exact Kakao application label; OTP parsing remains a second gate.
                has_kakao_app_label = any(
                    keyword in text.lower()
                    for text in window_texts
                    for keyword in self.notification_app_keywords
                )
                has_otp_keyword = any(
                    keyword in text.lower()
                    for text in window_texts
                    for keyword in self.otp_keywords
                )
                has_digit_candidate = any(
                    re.search(r"(?<![0-9])[0-9]{4,8}(?![0-9])", text)
                    for text in window_texts
                )
                is_structural_notification = bool(
                    has_kakao_app_label
                    and has_otp_keyword
                    and has_digit_candidate
                    and window_is_structural_host
                    and 0 < len(window_texts) <= self.notification_max_text_blocks
                )
                is_kakao_notification = bool(
                    self.listen_kakao_notifications
                    and (
                        (window_is_notification and has_kakao_app_label)
                        or is_structural_notification
                    )
                )
                if is_kakao_notification:
                    notification_matches += 1
                if window_is_kakao:
                    title_matches += 1
                if is_kakao_notification:
                    texts.extend(window_texts)
                    combined_text = " ".join(window_texts)
                    if combined_text and combined_text not in window_texts:
                        # Notification UIs often expose the OTP keyword and the
                        # digits in separate controls. Combine them in memory so
                        # the parser can evaluate the complete notification.
                        texts.append(combined_text)
                elif include_kakao_windows and window_is_kakao:
                    texts.extend(window_texts)
                    texts.extend(window_pane_otp_candidates)

                if exhaustive and (
                    window_is_kakao
                    or window_is_notification
                    or has_kakao_app_label
                    or has_otp_keyword
                ):
                    candidates.append(
                        KakaoWindowDiagnostic(
                            class_name=window_class,
                            text_blocks=len(window_texts),
                            kakao_title_match=window_is_kakao,
                            notification_title_match=window_is_notification,
                            kakao_app_marker=has_kakao_app_label,
                            otp_keyword_marker=has_otp_keyword,
                            digit_candidate_marker=has_digit_candidate,
                            otp_and_digit_marker=bool(
                                has_otp_keyword and has_digit_candidate
                            ),
                        )
                    )
            except Exception:
                access_errors += 1
        return texts, KakaoDiagnostic(
            desktop_windows=len(windows),
            title_matched_windows=title_matches,
            notification_matched_windows=notification_matches,
            text_blocks=len(texts),
            access_errors=access_errors,
            candidates=tuple(candidates),
        )

    def _collect_visible_texts(self, include_kakao_windows: bool | None = None) -> list[str]:
        texts, _ = self._scan(include_kakao_windows=include_kakao_windows)
        return texts

    def snapshot(self, include_kakao_windows: bool | None = None) -> list[str]:
        """Return a one-time UIA snapshot, useful for diagnostics."""
        return self._collect_visible_texts(include_kakao_windows=include_kakao_windows)

    def diagnose(self) -> KakaoDiagnostic:
        """Return counts only; message and OTP contents are never included."""
        _, diagnostic = self._scan(include_kakao_windows=True, exhaustive=True)
        return diagnostic

    def messages(
        self,
        on_idle: Callable[[], None] | None = None,
        on_ready: Callable[[], None] | None = None,
        idle_interval_seconds: float = 30.0,
    ) -> Iterator[KakaoMessage]:
        # Treat everything visible at startup as history. UIA exposes no reliable
        # message timestamp, so this prevents old codes from being entered later.
        started_at = time.time()
        for text in self._collect_visible_texts():
            self._seen[self._fingerprint(text)] = started_at
        last_activity_at = started_at
        if on_ready:
            on_ready()

        while True:
            now = time.time()
            self._seen = {
                fp: seen_at
                for fp, seen_at in self._seen.items()
                if now - seen_at < self.dedupe_ttl_seconds
            }

            found_new_text = False
            for text in self._collect_visible_texts():
                fp = self._fingerprint(text)
                if fp in self._seen:
                    self._seen[fp] = now
                    continue
                self._seen[fp] = now
                found_new_text = True
                yield KakaoMessage(text=text, detected_at=now)

            if found_new_text:
                last_activity_at = now
            elif on_idle and now - last_activity_at >= idle_interval_seconds:
                on_idle()
                last_activity_at = now

            time.sleep(self.poll_interval)
