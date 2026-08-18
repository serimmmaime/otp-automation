from types import SimpleNamespace

from kakao.listener import KakaoUiListener
from otp.parser import OtpParser


class FakeControl:
    def __init__(self, text, accessible_name="", control_type=""):
        self.text = text
        self.element_info = SimpleNamespace(name=accessible_name, control_type=control_type)

    def window_text(self):
        return self.text


class FakeWindow(FakeControl):
    def __init__(self, title, texts, class_name="", width=0, height=0):
        super().__init__(title)
        self.texts = texts
        self.element_info = SimpleNamespace(class_name=class_name, name="")
        self._rectangle = SimpleNamespace(width=lambda: width, height=lambda: height)

    def descendants(self):
        return [FakeControl(text) for text in self.texts]

    def rectangle(self):
        return self._rectangle


class FakeDesktop:
    def __init__(self, windows):
        self._windows = windows

    def windows(self):
        return self._windows


def make_listener():
    return KakaoUiListener(
        title_keywords=["KakaoTalk", "카카오톡"],
        notification_app_keywords=["kakao", "카카오톡"],
        notification_window_title_keywords=["notification", "알림"],
        notification_window_class_names=["Chrome_WidgetWin_1", "Progman"],
        notification_max_text_blocks=30,
        notification_max_width=700,
        notification_max_height=500,
        otp_keywords=["인증번호", "otp"],
        listen_kakao_notifications=True,
        kakao_window_digit_only_otp_length=6,
    )


def test_notification_is_detected_without_kakao_window_title(monkeypatch):
    desktop = FakeDesktop([FakeWindow("New notification", ["kakao", "인증번호 안내"] )])
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)

    texts, diagnostic = make_listener()._scan()

    assert "인증번호 안내" in texts
    assert diagnostic.notification_matched_windows == 1
    assert diagnostic.title_matched_windows == 0


def test_main_window_is_excluded_by_default(monkeypatch):
    desktop = FakeDesktop([FakeWindow("KakaoTalk", ["인증번호 안내"])])
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)

    texts, diagnostic = make_listener()._scan()

    assert texts == []
    assert diagnostic.title_matched_windows == 1


def test_diagnostic_can_include_main_window(monkeypatch):
    desktop = FakeDesktop([FakeWindow("KakaoTalk", ["인증번호 안내"])])
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)

    texts, _ = make_listener()._scan(include_kakao_windows=True)

    assert texts == ["인증번호 안내"]


def test_desktop_failure_is_reported_without_message_data(monkeypatch):
    def fail(backend):
        raise RuntimeError("UIA unavailable")

    monkeypatch.setattr("kakao.listener.Desktop", fail)
    texts, diagnostic = make_listener()._scan()

    assert texts == []
    assert diagnostic.access_errors == 1


def test_exhaustive_diagnostic_finds_unexpected_notification_structure(monkeypatch):
    desktop = FakeDesktop(
        [FakeWindow("Unexpected host", ["Message from kakao desktop", "인증번호 안내"])]
    )
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)

    texts, diagnostic = make_listener()._scan(exhaustive=True)

    assert texts == []
    assert len(diagnostic.candidates) == 1
    assert diagnostic.candidates[0].kakao_app_marker is True
    assert diagnostic.candidates[0].otp_keyword_marker is True


def test_actual_chrome_notification_structure_is_detected(monkeypatch):
    desktop = FakeDesktop(
        [
            FakeWindow(
                "Unexpected host",
                ["Message from kakao desktop", "인증번호 안내 [123456]"],
                class_name="Chrome_WidgetWin_1",
            )
        ]
    )
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)

    texts, diagnostic = make_listener()._scan()

    assert texts == [
        "Message from kakao desktop",
        "인증번호 안내 [123456]",
        "Message from kakao desktop 인증번호 안내 [123456]",
    ]
    assert diagnostic.notification_matched_windows == 1


def test_large_chrome_window_is_not_scanned_during_runtime(monkeypatch):
    window = FakeWindow(
        "Chrome",
        ["Message from kakao desktop", "인증번호 안내"],
        class_name="Chrome_WidgetWin_1",
        width=1900,
        height=1000,
    )
    desktop = FakeDesktop([window])
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)

    texts, diagnostic = make_listener()._scan()

    assert texts == []
    assert diagnostic.notification_matched_windows == 0


def test_progman_notification_structure_is_detected(monkeypatch):
    desktop = FakeDesktop(
        [
            FakeWindow(
                "Program Manager",
                ["kakao", "통합 로그인 인증번호는", "[123456] 입니다."],
                class_name="Progman",
                width=1900,
                height=1100,
            )
        ]
    )
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)

    texts, diagnostic = make_listener()._scan()

    assert diagnostic.notification_matched_windows == 1
    assert any("123456" in text for text in texts)


def test_split_notification_controls_can_be_parsed_as_one_message(monkeypatch):
    desktop = FakeDesktop(
        [
            FakeWindow(
                "Unexpected host",
                ["kakao", "통합 로그인 인증번호는", "[123456] 입니다."],
                class_name="Chrome_WidgetWin_1",
            )
        ]
    )
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)
    parser = OtpParser(keywords=["인증번호"], min_length=4, max_length=8)

    texts, _ = make_listener()._scan()
    parsed_codes = [result.code for text in texts if (result := parser.parse(text))]

    assert parsed_codes == ["123456"]


def test_accessible_name_is_used_when_window_text_hides_the_code(monkeypatch):
    window = FakeWindow(
        "Unexpected host",
        ["kakao", "통합 로그인 인증번호는"],
        class_name="Chrome_WidgetWin_1",
    )
    window.descendants = lambda: [
        FakeControl("kakao"),
        FakeControl("통합 로그인 인증번호는"),
        FakeControl("", accessible_name="[123456] 입니다."),
    ]
    desktop = FakeDesktop([window])
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)
    parser = OtpParser(keywords=["인증번호"], min_length=4, max_length=8)

    texts, _ = make_listener()._scan()

    assert any(parser.parse(text) for text in texts)


def test_kakao_pane_digit_is_converted_to_strict_otp_candidate(monkeypatch):
    window = FakeWindow("KakaoTalk", [], class_name="EVA_Window_Dblclk")
    window.descendants = lambda: [
        FakeControl("123456", control_type="Pane"),
        FakeControl("오후 2:15", control_type="Pane"),
    ]
    desktop = FakeDesktop([window])
    monkeypatch.setattr("kakao.listener.Desktop", lambda backend: desktop)
    parser = OtpParser(keywords=["인증번호"], min_length=4, max_length=8)

    texts, _ = make_listener()._scan(include_kakao_windows=True)

    assert any((result := parser.parse(text)) and result.code == "123456" for text in texts)
