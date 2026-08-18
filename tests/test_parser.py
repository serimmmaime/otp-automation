import pytest

from otp.parser import OtpDeduplicator, OtpParser


@pytest.fixture
def parser():
    return OtpParser(
        keywords=["인증번호", "인증 번호", "인증코드", "verification code", "otp"],
        min_length=4,
        max_length=8,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("인증번호는 381492 입니다.", "381492"),
        ("[서비스] 인증 번호 [123456] 를 입력해주세요.", "123456"),
        ("Verification code: 998877", "998877"),
        ("OTP 4455 expires in 3 minutes", "4455"),
        ("778899 is your verification code", "778899"),
        ("인증코드: 1234", "1234"),
        ("인증번호 12345678", "12345678"),
    ],
)
def test_parse_valid(parser, text, expected):
    assert parser.parse(text).code == expected


@pytest.mark.parametrize(
    "text",
    [
        "주문번호는 381492 입니다.",
        "오늘 날짜는 20260818입니다.",
        "인증번호를 입력해주세요.",
        "OTP 12",
        "그냥 일반 카카오톡 메시지",
    ],
)
def test_parse_rejects_non_otp(parser, text):
    assert parser.parse(text) is None


def test_invalid_length_range():
    with pytest.raises(ValueError):
        OtpParser(["otp"], min_length=8, max_length=4)


def test_empty_message(parser):
    assert parser.parse("") is None


def test_phone_number_is_not_partial_otp(parser):
    assert parser.parse("인증번호 문의: 010-1234-5678") is None


def test_phone_number_before_keyword_is_not_partial_otp(parser):
    assert parser.parse("010-1234-5678 인증번호 문의") is None


def test_separated_date_near_keyword_is_not_otp(parser):
    assert parser.parse("OTP 처리일 2026-08-18") is None


def test_space_separated_phone_before_keyword_is_not_partial_otp(parser):
    assert parser.parse("010 1234 5678 인증번호 문의") is None


def test_fingerprint_does_not_contain_code(parser):
    code = "381492"
    fingerprint = parser.fingerprint(code)
    assert code not in fingerprint
    assert fingerprint == parser.fingerprint(code)


def test_same_otp_is_duplicate_within_ttl():
    deduplicator = OtpDeduplicator(ttl_seconds=60)
    assert deduplicator.is_duplicate("123456", now=100) is False
    assert deduplicator.is_duplicate("123456", now=159) is True


def test_same_otp_is_allowed_after_ttl():
    deduplicator = OtpDeduplicator(ttl_seconds=60)
    assert deduplicator.is_duplicate("123456", now=100) is False
    assert deduplicator.is_duplicate("123456", now=160) is False
