from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Optional

import win32gui
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper


@dataclass(frozen=True)
class InputCandidate:
    score: int
    control: UIAWrapper


class ChromeOtpAutofill:
    def __init__(self, browser_title_keywords: Iterable[str], input_keywords: Iterable[str]):
        self.browser_title_keywords = tuple(k.lower() for k in browser_title_keywords)
        self.input_keywords = tuple(k.lower() for k in input_keywords)

    @staticmethod
    def _foreground_handle() -> int:
        return win32gui.GetForegroundWindow()

    def _active_chrome_window(self) -> Optional[UIAWrapper]:
        hwnd = self._foreground_handle()
        if not hwnd:
            return None
        try:
            window = Desktop(backend="uia").window(handle=hwnd)
            title = window.window_text().lower()
            if not any(k in title for k in self.browser_title_keywords):
                return None
            return window.wrapper_object()
        except Exception:
            return None

    def _score_edit(self, ctrl: UIAWrapper) -> int:
        try:
            props = [
                ctrl.window_text(),
                getattr(ctrl.element_info, "name", ""),
                getattr(ctrl.element_info, "automation_id", ""),
                getattr(ctrl.element_info, "class_name", ""),
            ]
            haystack = " ".join(str(p or "") for p in props).lower()
            score = sum(10 for k in self.input_keywords if k in haystack)
            if any(
                token in haystack
                for token in (
                    "password", "비밀번호", "email", "이메일", "username", "사용자명",
                    "search", "검색", "address", "주소", "phone", "전화",
                )
            ):
                score -= 100
            try:
                if bool(ctrl.is_password()):
                    return -100
            except Exception:
                pass
            return score
        except Exception:
            return -100

    @staticmethod
    def _has_keyboard_focus(ctrl: UIAWrapper) -> bool:
        """Return whether Windows UI Automation reports this Edit as focused."""
        try:
            return bool(getattr(ctrl.element_info, "has_keyboard_focus", False))
        except Exception:
            return False

    def _find_best_input(self, window: UIAWrapper) -> Optional[UIAWrapper]:
        positive = self._positive_inputs(window)
        # Multiple fields need an OTP length before they can be handled safely.
        return max(positive, key=lambda item: item.score).control if len(positive) == 1 else None

    def _positive_inputs(self, window: UIAWrapper) -> list[InputCandidate]:
        candidates: list[InputCandidate] = []
        try:
            for ctrl in window.descendants(control_type="Edit"):
                try:
                    if not ctrl.is_visible() or not ctrl.is_enabled():
                        continue
                    score = self._score_edit(ctrl)
                    # Some SSO pages expose a plain Edit with no accessible OTP
                    # label. Accept it only when the user explicitly focused it;
                    # negative-scored sensitive/address fields remain excluded.
                    if score == 0 and self._has_keyboard_focus(ctrl):
                        score = 1
                    candidates.append(InputCandidate(score, ctrl))
                except Exception:
                    continue
        except Exception:
            return []

        if not candidates:
            return []
        return [candidate for candidate in candidates if candidate.score > 0]

    def diagnose(self) -> list[dict[str, str | int | bool]]:
        """Return redacted metadata for visible Edit controls in active Chrome."""
        window = self._active_chrome_window()
        if not window:
            return []
        result: list[dict[str, str | int | bool]] = []
        for ctrl in window.descendants(control_type="Edit"):
            try:
                result.append(
                    {
                        "has_name": bool(getattr(ctrl.element_info, "name", "") or ""),
                        "has_automation_id": bool(getattr(ctrl.element_info, "automation_id", "") or ""),
                        "class_name": str(getattr(ctrl.element_info, "class_name", "") or ""),
                        "score": self._score_edit(ctrl),
                        "focused": self._has_keyboard_focus(ctrl),
                        "visible": bool(ctrl.is_visible()),
                        "enabled": bool(ctrl.is_enabled()),
                    }
                )
            except Exception:
                continue
        return result

    def has_suitable_input(self) -> bool:
        """Check the active Chrome window without focusing or modifying a field."""
        window = self._active_chrome_window()
        if not window:
            return False
        count = len(self._positive_inputs(window))
        return count == 1 or 4 <= count <= 8

    def fill(self, otp: str, auto_submit: bool = False) -> bool:
        if not otp.isascii() or not otp.isdigit():
            return False

        initial_handle = self._foreground_handle()
        window = self._active_chrome_window()
        if not window:
            return False

        candidates = self._positive_inputs(window)
        if len(candidates) == 1:
            targets = [candidates[0].control]
        elif len(candidates) == len(otp) and 4 <= len(candidates) <= 8:
            # UIA descendants are returned in visual/tab order in Chrome.
            targets = [candidate.control for candidate in candidates]
        else:
            return False

        try:
            # Do not type if focus changed while the UIA tree was being searched.
            if self._foreground_handle() != initial_handle:
                return False
            for target in targets:
                score = self._score_edit(target)
                if score == 0 and self._has_keyboard_focus(target):
                    score = 1
                if not target.is_visible() or not target.is_enabled() or score <= 0:
                    return False
            if len(targets) == 1:
                target = targets[0]
                target.set_focus()
                target.type_keys("^a{BACKSPACE}", set_foreground=True)
                target.type_keys(otp, with_spaces=True, set_foreground=True)
            else:
                for target, digit in zip(targets, otp):
                    if self._foreground_handle() != initial_handle:
                        return False
                    target.set_focus()
                    target.type_keys("^a{BACKSPACE}", set_foreground=True)
                    target.type_keys(digit, set_foreground=True)
            if auto_submit:
                time.sleep(0.15)
                targets[-1].type_keys("{ENTER}", set_foreground=True)
            return True
        except Exception:
            return False
