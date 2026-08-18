from types import SimpleNamespace

from browser.autofill import ChromeOtpAutofill


class FakeEdit:
    def __init__(self, name, automation_id="", class_name="", password=False):
        self.element_info = SimpleNamespace(
            name=name,
            automation_id=automation_id,
            class_name=class_name,
        )
        self._password = password
        self.typed = []

    def window_text(self):
        return ""

    def is_password(self):
        return self._password

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    def set_focus(self):
        return None

    def type_keys(self, keys, **kwargs):
        self.typed.append(keys)


class FakeWindow:
    def __init__(self, edits):
        self.edits = edits

    def descendants(self, control_type):
        assert control_type == "Edit"
        return self.edits


def autofill():
    return ChromeOtpAutofill(
        browser_title_keywords=["Chrome"],
        input_keywords=["인증", "보안 코드", "otp", "code"],
    )


def test_security_code_field_scores_positive():
    assert autofill()._score_edit(FakeEdit("보안 코드")) > 0


def test_phone_field_scores_negative():
    assert autofill()._score_edit(FakeEdit("전화 번호")) < 0


def test_search_field_with_code_in_name_is_rejected():
    assert autofill()._score_edit(FakeEdit("Search code")) < 0


def test_password_field_is_rejected_even_with_otp_keyword():
    assert autofill()._score_edit(FakeEdit("OTP", password=True)) < 0


def test_multiple_otp_fields_are_rejected_as_ambiguous():
    window = FakeWindow([FakeEdit("OTP digit 1"), FakeEdit("OTP digit 2")])
    assert autofill()._find_best_input(window) is None


def test_six_split_inputs_are_filled_when_code_length_matches(monkeypatch):
    edits = [FakeEdit(f"OTP digit {index}") for index in range(1, 7)]
    instance = autofill()
    monkeypatch.setattr(instance, "_foreground_handle", lambda: 100)
    monkeypatch.setattr(instance, "_active_chrome_window", lambda: FakeWindow(edits))

    assert instance.fill("123456") is True
    assert [edit.typed[-1] for edit in edits] == list("123456")


def test_split_inputs_are_rejected_when_count_does_not_match_code(monkeypatch):
    edits = [FakeEdit(f"OTP digit {index}") for index in range(1, 7)]
    instance = autofill()
    monkeypatch.setattr(instance, "_foreground_handle", lambda: 100)
    monkeypatch.setattr(instance, "_active_chrome_window", lambda: FakeWindow(edits))

    assert instance.fill("1234") is False
