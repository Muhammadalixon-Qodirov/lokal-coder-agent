"""llama-server (OpenAI-mos API) uchun minimal klient."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx

DEFAULT_URL = os.environ.get("CODER_LLM_URL", "http://127.0.0.1:8080")


@dataclass
class Completion:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tokens_per_sec: float = 0.0
    draft_accepted: float | None = None  # draft tokenlar qabul qilingan ulush (0..1)
    raw: dict = field(default_factory=dict, repr=False)


class LLM:
    def __init__(self, url: str = DEFAULT_URL, timeout: float = 600.0):
        self.url = url.rstrip("/")
        self.http = httpx.Client(timeout=timeout)

    def health(self) -> bool:
        try:
            return self.http.get(f"{self.url}/health").status_code == 200
        except httpx.HTTPError:
            return False

    def chat(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.1,
        stop: list[str] | None = None,
        json_schema: dict | None = None,
    ) -> Completion:
        body = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if stop:
            body["stop"] = stop
        if json_schema:
            # llama-server javobni grammatika bilan shu sxemaga majburlaydi
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "schema": json_schema}}
        r = self.http.post(f"{self.url}/v1/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()

        usage = data.get("usage", {})
        timings = data.get("timings", {})
        draft_n = timings.get("draft_n") or 0
        draft_ok = timings.get("draft_n_accepted") or 0
        return Completion(
            text=data["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            tokens_per_sec=timings.get("predicted_per_second", 0.0),
            draft_accepted=(draft_ok / draft_n) if draft_n else None,
            raw=data,
        )

    def count_tokens(self, text: str) -> int:
        r = self.http.post(f"{self.url}/tokenize", json={"content": text})
        r.raise_for_status()
        return len(r.json()["tokens"])
