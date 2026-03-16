from __future__ import annotations
import re
from pathlib import Path


KEY_RE = re.compile(r"Key:\s+(.)")
SPECIAL_RE = re.compile(r"Special Key:\s+Key\.(.+)")


def clean_keystrokes(input_file: str, output_file: str):

    buffer = []
    lines = []

    with open(input_file, "r", encoding="utf-8", errors="replace") as f:

        for line in f:

            # detect normal key
            m_key = KEY_RE.search(line)

            if m_key:
                char = m_key.group(1)

                # remove control characters
                if ord(char) >= 32:
                    buffer.append(char)

                continue

            # detect special key
            m_special = SPECIAL_RE.search(line)

            if m_special:

                key = m_special.group(1).lower()

                if "space" in key:
                    buffer.append(" ")

                elif "enter" in key:
                    lines.append("".join(buffer))
                    buffer = []

                elif "backspace" in key:
                    if buffer:
                        buffer.pop()

                # ignore ctrl, alt, esc, etc.

    if buffer:
        lines.append("".join(buffer))

    text = "\n".join(lines)

    # clean repeated spaces
    text = re.sub(r"\s+", " ", text)

    # remove strange 'K' separators
    text = text.replace("K", " ")

    # final cleanup
    text = re.sub(r"\s+", " ", text).strip()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print("Clean text written to:", output_file)


if __name__ == "__main__":

    base = Path(__file__).resolve().parent

    clean_keystrokes(
        base / "keystrokes.txt",
        base / "clean_text.txt"
    )