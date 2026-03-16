from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiResult:
    text: str


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key.strip()
        self.model = model.strip()

    def generate(self, prompt: str) -> GeminiResult:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_http_error: int | None = None
        last_error_body: str | None = None
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                break
            except urllib.error.HTTPError as e:
                last_http_error = int(getattr(e, "code", 0) or 0)
                try:
                    last_error_body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    last_error_body = None
                # 429 = rate limit; 503 = transient service issue
                if last_http_error in (429, 503) and attempt < 4:
                    time.sleep(1.5 * (2**attempt))
                    continue
                detail = ""
                if last_error_body:
                    # Avoid dumping huge responses.
                    detail = f"\nResponse body:\n{last_error_body[:2000]}"
                raise RuntimeError(f"Gemini HTTPError: {last_http_error}{detail}") from e
            except Exception as e:
                raise RuntimeError(f"Gemini request failed: {type(e).__name__}") from e
        else:
            detail = ""
            if last_error_body:
                detail = f"\nResponse body:\n{last_error_body[:2000]}"
            raise RuntimeError(f"Gemini HTTPError: {last_http_error or 'unknown'}{detail}")

        try:
            data = json.loads(raw)
            text = data["candidates"][0]["content"]["parts"][0].get("text", "")
            return GeminiResult(text=text)
        except Exception as e:
            raise RuntimeError("Failed to parse Gemini response.") from e

