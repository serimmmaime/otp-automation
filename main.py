from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DEFAULT_CONFIG = {
    "otp_source": "outlook_com",
    "poll_interval_seconds": 1.0,
    "otp_expire_seconds": 90,
    "dedupe_ttl_seconds": 600,
    "allowed_domains": [],
    "auto_submit": False,
    "dry_run": False,
    "log_level": "INFO",
    "kakao_notification_app_keywords": ["kakao", "카카오톡"],
    "notification_window_title_keywords": ["notification", "알림"],
    "notification_window_class_names": ["Chrome_WidgetWin_1", "Progman"],
    "notification_max_text_blocks": 30,
    "notification_max_width": 700,
    "notification_max_height": 500,
    "listen_kakao_windows": False,
    "listen_kakao_notifications": False,
    "kakao_window_digit_only_otp_length": 6,
    "email_subject_keywords": ["[SSO] 통합로그인 인증코드"],
    "email_sender_display_names": ["INNOCEAN Single Sign-On", "이노션"],
    "email_allowed_sender_addresses": [],
    "email_otp_pattern": r"인증코드\s*\[\s*([0-9]{6})\s*\]",
    "email_max_age_seconds": 90,
    "email_poll_interval_seconds": 2.0,
    "email_max_items": 50,
    "mark_email_as_read": False,
    "delete_email": False,
}


def load_config() -> dict:
    with open(ROOT / "config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return validate_config(cfg)


def validate_config(cfg: object) -> dict:
    if not isinstance(cfg, dict):
        raise ValueError("Config root must be a JSON object")
    required = [
        "otp_keywords",
        "otp_min_length",
        "otp_max_length",
        "kakao_window_title_keywords",
        "browser_title_keywords",
        "input_keywords",
    ]
    missing = [key for key in required if key not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {', '.join(missing)}")

    allowed_keys = set(DEFAULT_CONFIG) | set(required)
    unknown = sorted(set(cfg) - allowed_keys)
    if unknown:
        raise ValueError(f"Unknown config keys: {', '.join(unknown)}")

    cfg = {**DEFAULT_CONFIG, **cfg}
    list_keys = (
        "otp_keywords",
        "kakao_window_title_keywords",
        "browser_title_keywords",
        "input_keywords",
        "allowed_domains",
        "kakao_notification_app_keywords",
        "notification_window_title_keywords",
        "notification_window_class_names",
        "email_subject_keywords",
        "email_sender_display_names",
        "email_allowed_sender_addresses",
    )
    for key in list_keys:
        value = cfg[key]
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError(f"Config '{key}' must be a list of non-empty strings")
    for key in (
        "otp_keywords",
        "kakao_window_title_keywords",
        "browser_title_keywords",
        "input_keywords",
        "kakao_notification_app_keywords",
        "notification_window_title_keywords",
        "notification_window_class_names",
        "email_subject_keywords",
    ):
        if not cfg[key]:
            raise ValueError(f"Config '{key}' must not be empty")

    if not isinstance(cfg["otp_min_length"], int) or isinstance(cfg["otp_min_length"], bool):
        raise ValueError("Config 'otp_min_length' must be an integer")
    if not isinstance(cfg["otp_max_length"], int) or isinstance(cfg["otp_max_length"], bool):
        raise ValueError("Config 'otp_max_length' must be an integer")
    if cfg["otp_min_length"] < 3 or cfg["otp_max_length"] < cfg["otp_min_length"]:
        raise ValueError("Invalid OTP length range")
    pane_otp_length = cfg["kakao_window_digit_only_otp_length"]
    if (
        not isinstance(pane_otp_length, int)
        or isinstance(pane_otp_length, bool)
        or pane_otp_length < cfg["otp_min_length"]
        or pane_otp_length > cfg["otp_max_length"]
    ):
        raise ValueError(
            "Config 'kakao_window_digit_only_otp_length' must be an integer within the OTP length range"
        )

    for key in (
        "poll_interval_seconds",
        "otp_expire_seconds",
        "dedupe_ttl_seconds",
        "notification_max_text_blocks",
        "notification_max_width",
        "notification_max_height",
        "email_max_age_seconds",
        "email_poll_interval_seconds",
        "email_max_items",
    ):
        value = cfg[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"Config '{key}' must be a positive number")
    for key in (
        "auto_submit",
        "dry_run",
        "listen_kakao_windows",
        "listen_kakao_notifications",
        "mark_email_as_read",
        "delete_email",
    ):
        if not isinstance(cfg[key], bool):
            raise ValueError(f"Config '{key}' must be true or false")
    if not isinstance(cfg["log_level"], str) or cfg["log_level"].upper() not in {
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    }:
        raise ValueError("Config 'log_level' is invalid")
    if cfg["otp_source"] not in {"outlook_com", "kakao_uia"}:
        raise ValueError("Config 'otp_source' must be 'outlook_com' or 'kakao_uia'")
    if not isinstance(cfg["email_otp_pattern"], str):
        raise ValueError("Config 'email_otp_pattern' must be a string")
    import re
    try:
        email_pattern = re.compile(cfg["email_otp_pattern"])
    except re.error as exc:
        raise ValueError("Config 'email_otp_pattern' is invalid") from exc
    if email_pattern.groups != 1:
        raise ValueError("Config 'email_otp_pattern' must have exactly one capture group")
    if not cfg["email_sender_display_names"] and not cfg["email_allowed_sender_addresses"]:
        raise ValueError("Configure at least one allowed email sender")
    if cfg["mark_email_as_read"] or cfg["delete_email"]:
        raise ValueError("This utility never marks OTP email as read or deletes it")
    if cfg["allowed_domains"]:
        raise ValueError(
            "Config 'allowed_domains' is not supported safely by the current UIA backend; leave it empty"
        )
    return cfg


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Outlook/KakaoTalk OTP autofill for Chrome on Windows")
    p.add_argument("--dry-run", action="store_true", help="Detect OTP but never type it")
    p.add_argument("--diagnose-kakao", action="store_true", help="Print KakaoTalk UIA text count and exit")
    p.add_argument("--diagnose-chrome", action="store_true", help="Print active Chrome Edit controls and exit")
    p.add_argument("--diagnose-outlook", action="store_true", help="Print redacted Classic Outlook connectivity and exit")
    p.add_argument(
        "--diagnose-delay",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Wait before diagnostics so the target UI can be brought to the foreground",
    )
    return p.parse_args()


def ensure_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("This application supports Windows only.")


def main() -> None:
    args = parse_args()
    ensure_windows()

    from browser.autofill import ChromeOtpAutofill
    from kakao.listener import KakaoUiListener
    from email_source.outlook import OutlookComSource
    from otp.parser import OtpDeduplicator, OtpParser
    from utils.logger import build_logger

    cfg = load_config()
    logger = build_logger(level=cfg.get("log_level", "INFO"))

    diagnose_delay = 5.0 if args.diagnose_chrome and args.diagnose_delay is None else (args.diagnose_delay or 0)
    if diagnose_delay < 0:
        raise ValueError("--diagnose-delay must not be negative")
    if (args.diagnose_kakao or args.diagnose_chrome) and diagnose_delay:
        print(f"Diagnostics will start in {diagnose_delay:g} seconds. Activate the target window now...")
        time.sleep(diagnose_delay)

    parser = OtpParser(
        keywords=cfg["otp_keywords"],
        min_length=cfg["otp_min_length"],
        max_length=cfg["otp_max_length"],
    )
    listener = KakaoUiListener(
        title_keywords=cfg["kakao_window_title_keywords"],
        notification_app_keywords=cfg["kakao_notification_app_keywords"],
        notification_window_title_keywords=cfg["notification_window_title_keywords"],
        notification_window_class_names=cfg["notification_window_class_names"],
        notification_max_text_blocks=cfg["notification_max_text_blocks"],
        notification_max_width=cfg["notification_max_width"],
        notification_max_height=cfg["notification_max_height"],
        otp_keywords=cfg["otp_keywords"],
        listen_kakao_windows=cfg["listen_kakao_windows"],
        listen_kakao_notifications=cfg["listen_kakao_notifications"],
        kakao_window_digit_only_otp_length=cfg["kakao_window_digit_only_otp_length"],
        poll_interval=cfg.get("poll_interval_seconds", 0.5),
        dedupe_ttl_seconds=cfg.get("dedupe_ttl_seconds", 600),
    )
    outlook_source = OutlookComSource(
        subject_keywords=cfg["email_subject_keywords"],
        sender_display_names=cfg["email_sender_display_names"],
        allowed_sender_addresses=cfg["email_allowed_sender_addresses"],
        otp_pattern=cfg["email_otp_pattern"],
        max_age_seconds=cfg["email_max_age_seconds"],
        poll_interval=cfg["email_poll_interval_seconds"],
        max_items=cfg["email_max_items"],
    )
    autofill = ChromeOtpAutofill(
        browser_title_keywords=cfg["browser_title_keywords"],
        input_keywords=cfg["input_keywords"],
    )

    if args.diagnose_kakao:
        diagnostic = listener.diagnose()
        print(f"Desktop UIA windows: {diagnostic.desktop_windows}")
        print(f"KakaoTalk title matches: {diagnostic.title_matched_windows}")
        print(f"Kakao notification matches: {diagnostic.notification_matched_windows}")
        print(f"KakaoTalk UIA text blocks: {diagnostic.text_blocks}")
        print(f"UIA access errors: {diagnostic.access_errors}")
        print(f"Redacted candidate windows: {len(diagnostic.candidates)}")
        for candidate in diagnostic.candidates:
            print(
                {
                    "class_name": candidate.class_name,
                    "text_blocks": candidate.text_blocks,
                    "kakao_title_match": candidate.kakao_title_match,
                    "notification_title_match": candidate.notification_title_match,
                    "kakao_app_marker": candidate.kakao_app_marker,
                    "otp_keyword_marker": candidate.otp_keyword_marker,
                    "digit_candidate_marker": candidate.digit_candidate_marker,
                    "otp_and_digit_marker": candidate.otp_and_digit_marker,
                }
            )
        print("Message contents are intentionally hidden.")
        return

    if args.diagnose_chrome:
        controls = autofill.diagnose()
        print(f"Chrome Edit controls: {len(controls)}")
        for item in controls:
            print(item)
        return

    if args.diagnose_outlook:
        diagnostic = outlook_source.diagnose()
        print(f"Classic Outlook COM available: {diagnostic.com_available}")
        print(f"Outlook MAPI session available: {diagnostic.session_available}")
        print(f"Outlook stores: {diagnostic.stores}")
        print(f"Default Inbox available: {diagnostic.inbox_available}")
        print(f"Recent messages checked: {diagnostic.recent_messages_checked}")
        print(f"Metadata matches: {diagnostic.metadata_matches}")
        print(f"Received within 30 minutes: {diagnostic.received_within_30_minutes}")
        print(f"Subject filter passes: {diagnostic.subject_matches}")
        print(f"Sender filter passes: {diagnostic.sender_matches}")
        print(f"Body pattern passes: {diagnostic.body_pattern_matches}")
        print(f"Newest message calculated age (seconds): {diagnostic.newest_message_age_seconds}")
        print(f"Outlook access errors: {diagnostic.access_errors}")
        print("Email subjects, senders, bodies, and OTP values are intentionally hidden.")
        return

    dry_run = bool(args.dry_run or cfg.get("dry_run", False))
    otp_deduplicator = OtpDeduplicator(cfg["dedupe_ttl_seconds"])
    expire_seconds = float(cfg["otp_expire_seconds"])

    source_name = cfg["otp_source"]
    source = outlook_source if source_name == "outlook_com" else listener
    logger.info("OTP Autofill started")
    logger.info("dry_run=%s auto_submit=%s", dry_run, bool(cfg.get("auto_submit", False)))
    logger.info("Initializing configured OTP source: %s", source_name)

    for message in source.messages(
        on_idle=lambda: logger.info("Still waiting for a new OTP message"),
        on_ready=lambda: logger.info(
            "READY: request a new OTP now; messages already visible were ignored"
        ),
    ):
        parsed = parser.parse(message.text)
        if not parsed:
            continue

        now = time.time()
        if now - message.detected_at > expire_seconds:
            logger.info("Expired OTP-like message ignored")
            continue
        if otp_deduplicator.is_duplicate(parsed.code, now=now):
            logger.info("Duplicate OTP ignored")
            continue

        logger.info("OTP-like message detected")

        if dry_run:
            if autofill.has_suitable_input():
                logger.info("Chrome OTP field detected; dry-run enabled, autofill skipped")
            else:
                logger.warning("Dry-run: no suitable active Chrome input was found")
            continue

        if autofill.fill(parsed.code, auto_submit=cfg.get("auto_submit", False)):
            logger.info("OTP filled into active Chrome window")
        else:
            logger.warning("OTP detected, but no suitable active Chrome input was found")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
