"""
Unified API client — reads config.json for language + vision models.

Language model: used for behavior analysis + narrative generation.
Vision model: reserved for future visual scene understanding.

Both fall back to RuleEngine on any failure.
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional

from ..config_loader import cfg
from .llm_interface import LLMInterface, RuleEngine


class LLMClient(LLMInterface):
    """Language model client. Endpoint from cfg.language."""

    def __init__(self) -> None:
        lang = cfg.language
        self._available = lang.available
        self._api_key = lang.api_key
        self._model = lang.model
        self._endpoint = lang.endpoint
        self._cooldown = lang.cooldown
        self._timeout = lang.timeout
        self._last_call: float = 0.0
        self._cached_result: Optional[dict] = None
        self._fallback = RuleEngine()

    def is_available(self) -> bool:
        return self._available

    @property
    def provider_name(self) -> str:
        if not self._available:
            return "rule_engine"
        return cfg.language.provider

    # ── Text analysis (language model) ──────────────────

    def analyze_session(self, context: dict) -> dict:
        if not self._available:
            return self._fallback.analyze_session(context)
        now = time.time()
        if now - self._last_call < self._cooldown:
            return self._cached_result or self._fallback.analyze_session(context)

        system = (
            'You are the consciousness of an interactive art installation called '
            '"The Unseen". Users interact via hand gestures. '
            'Return ONLY valid JSON:\n'
            '{"user_archetype":"Creator|Explorer|Observer|Connector|Visitor",'
            '"world_mood":"Calm|Hope|Curiosity|Dream|Harmony|Bloom|Silence",'
            '"weather":"Calm|Wind|Storm|Aurora",'
            '"lighting":"Warm|Cool|Neutral|Soft|Dramatic",'
            '"organism_strategy":"Curious|Fearful|Approach|Observe|Balanced",'
            '"narrative":"one poetic sentence about this moment",'
            '"recommended_event":"Calm|Bloom|Aurora|Storm|Gust"}'
        )
        user_text = json.dumps(context, ensure_ascii=False)

        try:
            payload = json.dumps({
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.7,
                "max_tokens": 400,
            }).encode("utf-8")

            req = urllib.request.Request(
                self._endpoint, data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                })
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1]
                    if content.endswith("```"):
                        content = content[:-3]
                result = json.loads(content)
                self._last_call = time.time()
                self._cached_result = result
                return result
        except Exception:
            return self._fallback.analyze_session(context)

    def generate_narrative(self, context: dict) -> str:
        return self.analyze_session(context).get(
            "narrative", "You were here. The world has changed.")

    def propose_evolution(self, context: dict) -> dict:
        return self._fallback.propose_evolution(context)
