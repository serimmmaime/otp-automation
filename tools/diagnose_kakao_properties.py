"""Report which UIA property types expose Kakao message data.

This diagnostic intentionally prints only counts and Boolean-like metadata.
It never prints control text, OTP values, or message contents.
"""

from __future__ import annotations

import re
from collections import Counter

from pywinauto import Desktop


TITLE_KEYWORDS = ("kakaotalk", "카카오톡")
OTP_KEYWORDS = ("인증번호", "인증 번호", "인증코드", "인증 코드", "otp", "verification code")
ROOM_KEYWORDS = ("innocean_알림센터", "innocean 알림센터")
DIGIT_PATTERN = re.compile(r"(?<![0-9])[0-9]{4,8}(?![0-9])")


def markers(value: object) -> tuple[bool, bool]:
    text = str(value or "").strip().lower()
    return any(keyword in text for keyword in OTP_KEYWORDS), bool(DIGIT_PATTERN.search(text))


def main() -> None:
    windows = []
    for window in Desktop(backend="uia").windows():
        try:
            title = window.window_text().lower()
        except Exception:
            continue
        if any(keyword in title for keyword in TITLE_KEYWORDS):
            windows.append(window)

    print(f"KakaoTalk windows: {len(windows)}")
    for window_index, window in enumerate(windows, start=1):
        counters: Counter[tuple[str, str, str]] = Counter()
        controls = window.descendants()
        for control in controls:
            control_type = str(getattr(control.element_info, "control_type", "") or "unknown")
            properties: dict[str, object] = {}
            try:
                properties["window_text"] = control.window_text()
            except Exception:
                pass
            try:
                properties["accessible_name"] = getattr(control.element_info, "name", "")
            except Exception:
                pass
            try:
                properties["value_pattern"] = control.iface_value.CurrentValue
            except Exception:
                pass
            try:
                for key, value in control.legacy_properties().items():
                    properties[f"legacy_{key}"] = value
            except Exception:
                pass

            for source, value in properties.items():
                has_keyword, has_digits = markers(value)
                if has_keyword:
                    counters[(control_type, source, "otp_keyword")] += 1
                if has_digits:
                    counters[(control_type, source, "digit_candidate")] += 1
                    if source in {"window_text", "accessible_name", "value_pattern", "legacy_Name"}:
                        for match in DIGIT_PATTERN.finditer(str(value or "")):
                            counters[
                                (control_type, source, f"digit_length_{len(match.group(0))}")
                            ] += 1
                if any(keyword in str(value or "").strip().lower() for keyword in ROOM_KEYWORDS):
                    counters[(control_type, source, "target_room_marker")] += 1

        print(f"Window {window_index} controls: {len(controls)}")
        if not counters:
            print("No OTP keywords or 4-8 digit candidates exposed by inspected UIA properties.")
        else:
            for (control_type, source, marker), count in sorted(counters.items()):
                print(
                    {
                        "control_type": control_type,
                        "property_source": source,
                        "marker": marker,
                        "count": count,
                    }
                )


if __name__ == "__main__":
    main()
