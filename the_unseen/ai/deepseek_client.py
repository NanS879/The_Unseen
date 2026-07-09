"""
DeepSeek API Client — reads api_key from config.json.

Sends structured JSON. Falls back to RuleEngine on failure.
All settings (key, model, cooldown, timeout) from AppConfig.
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional

from ..config_loader import cfg
from .llm_interface import LLMInterface, RuleEngine

API_URL = "https://api.deepseek.com/v1/chat/completions"


class DeepSeekClient(LLMInterface):
    """DeepSeek API backend. All config from config.json."""

    def __init__(self) -> None:
        self._available = cfg.ai_available
        self._api_key = cfg.api_key
        self._model = cfg.model
        self._cooldown = cfg.cooldown
        self._timeout = cfg.timeout
        self._last_call: float = 0.0
        self._cached_result: Optional[dict] = None
        self._fallback = RuleEngine()

    def is_available(self) -> bool:
        return self._available

    def analyze_session(self, context: dict) -> dict:
        if not self._available:
            return self._fallback.analyze_session(context)
        now = time.time()
        if now - self._last_call < self._cooldown:
            return self._cached_result or self._fallback.analyze_session(context)

        system = (
            'You are the World Brain of an interactive art installation. '
            'Users interact via hand gestures. Return ONLY valid JSON:\n'
            '{"user_archetype":"Creator|Explorer|Observer|Connector|Visitor",'
            '"world_mood":"Calm|Hope|Curiosity|Dream|Harmony|Bloom",'
            '"weather":"Calm|Wind|Storm|Aurora",'
            '"lighting":"Warm|Cool|Neutral|Soft|Dramatic",'
            '"organism_strategy":"Curious|Fearful|Approach|Observe|Balanced",'
            '"narrative":"one poetic sentence",'
            '"recommended_event":"Calm|Gust|Bloom|Aurora"}'
        )
        try:
            payload = json.dumps({
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
                "temperature": 0.7, "max_tokens": 300,
                "response_format": {"type": "json_object"},
            }).encode("utf-8")

            req = urllib.request.Request(
                API_URL, data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                })
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result = json.loads(data["choices"][0]["message"]["content"])
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
