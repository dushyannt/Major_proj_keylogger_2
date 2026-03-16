from __future__ import annotations

import argparse
import json
import os
import sys

from config import GEMINI_API_KEY, GEMINI_MODEL, INPUT_FILE, PROMPT_FILE
from gemini_client import GeminiClient
from keylog_processor import (
    KeylogFeatures,
    basic_sanitize,
    extract_features,
    load_lines,
)


def build_prompt(user_prompt: str, features: KeylogFeatures) -> str:
    return f"""{user_prompt.strip()}

FEATURES_JSON_START
{json.dumps(features.to_dict(), indent=2)}
FEATURES_JSON_END
"""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Analyze keystroke log features with Gemini.")
    parser.add_argument(
        "--prompt",
        required=False,
        help=f"Prompt/instructions to send to Gemini. If omitted, reads from {PROMPT_FILE}.",
    )
    parser.add_argument(
        "--prompt-file",
        default=PROMPT_FILE,
        help=f"Prompt file path (default: {PROMPT_FILE}). Ignored if --prompt is set.",
    )
    parser.add_argument(
        "--file",
        default=INPUT_FILE,
        help=f"Input text file (default: {INPUT_FILE}).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=20000,
        help="Max chars to send (default: 20000).",
    )
    args = parser.parse_args(argv)

    if not GEMINI_API_KEY:
        print("Error: set GEMINI_API_KEY in your environment.", file=sys.stderr)
        return 2

    prompt_text = (args.prompt or "").strip()
    if not prompt_text:
        if not os.path.exists(args.prompt_file):
            print(
                f"Error: no --prompt provided and prompt file not found: {args.prompt_file}",
                file=sys.stderr,
            )
            return 2
        with open(args.prompt_file, "r", encoding="utf-8", errors="replace") as f:
            prompt_text = f.read()
        prompt_text = basic_sanitize(prompt_text)
        if not prompt_text:
            print(f"Error: prompt file is empty: {args.prompt_file}", file=sys.stderr)
            return 2

    if not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        return 2

    lines = load_lines(args.file)
    features = extract_features(lines)

    client = GeminiClient(api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
    prompt = build_prompt(prompt_text, features)
    result = client.generate(prompt)

    print(result.text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

