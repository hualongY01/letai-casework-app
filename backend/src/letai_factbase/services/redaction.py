import re
from dataclasses import dataclass, field


@dataclass
class RedactionResult:
    text: str
    summary: dict[str, int] = field(default_factory=dict)


REDACTION_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "id_number",
        re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
        "[REDACTED_ID_NUMBER]",
    ),
    (
        "phone_number",
        re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
        "[REDACTED_PHONE]",
    ),
    (
        "bank_account",
        re.compile(r"(?<!\d)\d{12,30}(?!\d)"),
        "[REDACTED_BANK_ACCOUNT]",
    ),
    (
        "address_label",
        re.compile(
            r"((?:Address|Home Address|Contact Address|Mailing Address|"
            r"\u5bb6\u5ead\u4f4f\u5740|\u4f4f\u5740|"
            r"\u8054\u7cfb\u5730\u5740|\u901a\u8baf\u5730\u5740)[:\uff1a\s]*)"
            r"([^\u3002\n\r\uff1b;]{4,80})",
            re.IGNORECASE,
        ),
        r"\1[REDACTED_ADDRESS]",
    ),
]


def redact_sensitive_text(text: str) -> RedactionResult:
    redacted = text
    summary: dict[str, int] = {}
    for key, pattern, replacement in REDACTION_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        if count:
            summary[key] = count
    return RedactionResult(text=redacted, summary=summary)
