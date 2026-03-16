from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import List


def basic_sanitize(text: str) -> str:
    """
    Minimal normalization for user-sanitized input (used for prompt text).
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def load_lines(path: str, *, max_lines: int | None = None) -> List[str]:
    """
    Load lines from a keylog file.
    """
    lines: List[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            lines.append(line.rstrip("\n"))
            if max_lines is not None and i + 1 >= max_lines:
                break
    return lines


@dataclass(frozen=True)
class KeylogFeatures:
    total_lines: int
    total_events: int
    printable_events: int
    special_events: int
    backspace_events: int
    enter_events: int
    tab_events: int
    ctrl_events: int
    alt_events: int
    esc_events: int
    shift_events: int
    unknown_special_events: int
    chars_per_min_estimate: float | None
    span_seconds: float | None

    def to_dict(self) -> dict:
        return {
            "total_lines": self.total_lines,
            "total_events": self.total_events,
            "printable_events": self.printable_events,
            "special_events": self.special_events,
            "backspace_events": self.backspace_events,
            "enter_events": self.enter_events,
            "tab_events": self.tab_events,
            "ctrl_events": self.ctrl_events,
            "alt_events": self.alt_events,
            "esc_events": self.esc_events,
            "shift_events": self.shift_events,
            "unknown_special_events": self.unknown_special_events,
            "chars_per_min_estimate": self.chars_per_min_estimate,
            "span_seconds": self.span_seconds,
        }


_TS_RE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+-\s+")
_PRINTABLE_RE = re.compile(r"\bKey:\s+(.)\s*$")
_SPECIAL_RE = re.compile(r"\bSpecial Key:\s+(.+?)\s*$")


def _parse_timestamp(line: str) -> datetime.datetime | None:
    m = _TS_RE.match(line)
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def extract_features(lines: List[str]) -> KeylogFeatures:
    """
    Extract privacy-preserving features from a raw keystroke log.

    This does NOT reconstruct the typed text.
    """
    total_lines = len(lines)
    total_events = 0
    printable_events = 0
    special_events = 0

    backspace_events = 0
    enter_events = 0
    tab_events = 0
    ctrl_events = 0
    alt_events = 0
    esc_events = 0
    shift_events = 0
    unknown_special_events = 0

    first_ts: datetime.datetime | None = None
    last_ts: datetime.datetime | None = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        ts = _parse_timestamp(line)
        if ts is not None:
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts

        if _PRINTABLE_RE.search(line):
            total_events += 1
            printable_events += 1
            continue

        m_spec = _SPECIAL_RE.search(line)
        if not m_spec:
            continue

        total_events += 1
        special_events += 1
        token = (m_spec.group(1) or "").strip().lower()

        if "backspace" in token:
            backspace_events += 1
        elif "enter" in token:
            enter_events += 1
        elif "tab" in token:
            tab_events += 1
        elif "ctrl" in token or "control" in token:
            ctrl_events += 1
        elif "alt" in token:
            alt_events += 1
        elif "esc" in token:
            esc_events += 1
        elif "shift" in token:
            shift_events += 1
        else:
            unknown_special_events += 1

    span_seconds: float | None = None
    if first_ts is not None and last_ts is not None and last_ts >= first_ts:
        span_seconds = (last_ts - first_ts).total_seconds()

    chars_per_min_estimate: float | None = None
    if span_seconds and span_seconds > 0:
        chars_per_min_estimate = printable_events / (span_seconds / 60.0)

    return KeylogFeatures(
        total_lines=total_lines,
        total_events=total_events,
        printable_events=printable_events,
        special_events=special_events,
        backspace_events=backspace_events,
        enter_events=enter_events,
        tab_events=tab_events,
        ctrl_events=ctrl_events,
        alt_events=alt_events,
        esc_events=esc_events,
        shift_events=shift_events,
        unknown_special_events=unknown_special_events,
        chars_per_min_estimate=chars_per_min_estimate,
        span_seconds=span_seconds,
    )


