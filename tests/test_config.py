import pytest

from main import validate_config


def valid_config():
    return {
        "otp_min_length": 4,
        "otp_max_length": 8,
        "otp_keywords": ["otp"],
        "kakao_window_title_keywords": ["KakaoTalk"],
        "browser_title_keywords": ["Chrome"],
        "input_keywords": ["otp"],
    }


def test_config_defaults_are_applied():
    config = validate_config(valid_config())
    assert config["auto_submit"] is False
    assert config["allowed_domains"] == []
    assert "kakao" in config["kakao_notification_app_keywords"]
    assert "notification" in config["notification_window_title_keywords"]
    assert config["notification_window_class_names"] == ["Chrome_WidgetWin_1", "Progman"]
    assert config["notification_max_text_blocks"] == 30
    assert config["notification_max_width"] == 700
    assert config["notification_max_height"] == 500
    assert config["listen_kakao_windows"] is False
    assert config["listen_kakao_notifications"] is False
    assert config["kakao_window_digit_only_otp_length"] == 6
    assert config["otp_source"] == "outlook_com"
    assert config["email_poll_interval_seconds"] == 2.0
    assert config["mark_email_as_read"] is False
    assert config["delete_email"] is False


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("otp_min_length", True),
        ("poll_interval_seconds", 0),
        ("auto_submit", "false"),
        ("listen_kakao_windows", "false"),
        ("listen_kakao_notifications", "false"),
        ("kakao_window_digit_only_otp_length", 9),
        ("otp_keywords", "otp"),
        ("log_level", "VERBOSE"),
        ("otp_source", "outlook_web"),
        ("mark_email_as_read", True),
        ("delete_email", True),
        ("email_otp_pattern", r"[0-9]{6}"),
    ],
)
def test_invalid_config_is_rejected(key, value):
    config = valid_config()
    config[key] = value
    with pytest.raises(ValueError):
        validate_config(config)


def test_nonempty_allowed_domains_is_rejected_until_supported():
    config = valid_config()
    config["allowed_domains"] = ["example.com"]
    with pytest.raises(ValueError, match="not supported safely"):
        validate_config(config)


def test_unknown_config_key_is_rejected():
    config = valid_config()
    config["auto_sumbit"] = True
    with pytest.raises(ValueError, match="Unknown config keys"):
        validate_config(config)


def test_required_keyword_list_must_not_be_empty():
    config = valid_config()
    config["input_keywords"] = []
    with pytest.raises(ValueError, match="must not be empty"):
        validate_config(config)
