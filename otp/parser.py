from __future__ import annotations

import re
import hashlib
import time
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class ParsedOtp:
    code: str


class OtpParser:
    def __init__(self, keywords: Iterable[str], min_length: int = 4, max_length: int = 8):
        if min_length < 3 or max_length < min_length:
            raise ValueError("Invalid OTP length range")

        escaped = [re.escape(k.strip()) for k in keywords if k and k.strip()]
        keyword_group = "|".join(escaped) or r"인증번호|verification\s*code|otp"
        self.patterns = [
            re.compile(
                rf"(?:{keyword_group})[^0-9]{{0,40}}"
                rf"(?<![0-9./-])([0-9]{{{min_length},{max_length}}})(?![0-9./-])",
                re.IGNORECASE,
            ),
            re.compile(
                rf"(?<![0-9./-])([0-9]{{{min_length},{max_length}}})(?![0-9./-])"
                rf"[^\n]{{0,40}}(?:{keyword_group})",
                re.IGNORECASE,
            ),
        ]

    def parse(self, text: str) -> Optional[ParsedOtp]:
        if not text:
            return None

        compact = " ".join(text.split())
        for pattern in self.patterns:
            for match in pattern.finditer(compact):
                start, end = match.span(1)
                if self._is_part_of_grouped_number(compact, start, end):
                    continue
                return ParsedOtp(code=match.group(1))
        return None

    @staticmethod
    def _is_part_of_grouped_number(text: str, start: int, end: int) -> bool:
        """Reject phone/date fragments separated by spaces or punctuation."""
        prefix = text[:start]
        suffix = text[end:]
        return bool(
            re.search(r"[0-9]{2,4}[\s,./-]$", prefix)
            or re.match(r"^[\s,./-][0-9]{2,4}(?:\D|$)", suffix)
        )

    @staticmethod
    def fingerprint(code: str) -> str:
        """Return a non-reversible value suitable for short-lived deduplication."""
        return hashlib.sha256(code.encode("ascii", errors="ignore")).hexdigest()


class OtpDeduplicator:
    """Keep only hashed OTP fingerprints for a bounded amount of time."""

    def __init__(self, ttl_seconds: float):
        if ttl_seconds <= 0:
            raise ValueError("OTP deduplication TTL must be positive")
        self.ttl_seconds = float(ttl_seconds)
        self._seen: dict[str, float] = {}

    def is_duplicate(self, code: str, now: float | None = None) -> bool:
        checked_at = time.time() if now is None else float(now)
        self._seen = {
            fingerprint: seen_at
            for fingerprint, seen_at in self._seen.items()
            if checked_at - seen_at < self.ttl_seconds
        }
        fingerprint = OtpParser.fingerprint(code)
        if fingerprint in self._seen:
            return True
        self._seen[fingerprint] = checked_at
        return False
