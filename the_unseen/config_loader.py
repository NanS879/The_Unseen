"""
Project configuration loaded from config.json at repo root.

Dual-model architecture:
    language — text analysis (DeepSeek, Claude, OpenAI, or rule_engine)
    vision   — visual analysis (Doubao Seedance, etc.) — reserved for future

Usage:
    from .config_loader import cfg
    cfg.language.api_key     # DeepSeek key
    cfg.language.provider    # "deepseek"
    cfg.vision.api_key       # Doubao key
    cfg.vision.provider      # "doubao"
"""

import json
import os
from typing import Optional


class _ModelConfig:
    """Config for a single AI model endpoint."""
    def __init__(self) -> None:
        self.provider: str = ""
        self.model: str = ""
        self.api_key: str = ""
        self.endpoint: str = ""
        self.cooldown: float = 25.0
        self.timeout: float = 8.0

    @property
    def available(self) -> bool:
        return bool(self.api_key) and self.provider != ""


class AppConfig:
    """Reads config.json from project root. Singleton.

    Attributes:
        language: _ModelConfig for text analysis (always available via RuleEngine).
        vision:   _ModelConfig for visual analysis (reserved).
        log_level: "DEBUG" / "INFO" / "WARNING".
    """

    _instance: Optional["AppConfig"] = None

    def __new__(cls) -> "AppConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "config.json")

        # ── Defaults ────────────────────────────────────
        self.language = _ModelConfig()
        self.language.provider = "deepseek"
        self.language.model = "deepseek-chat"
        self.language.endpoint = "https://api.deepseek.com/v1/chat/completions"

        self.vision = _ModelConfig()
        self.vision.provider = "doubao"
        self.vision.model = "doubao-seedance-1-0-pro-250528"
        self.vision.endpoint = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

        self.log_level: str = "DEBUG"

        # ── Read file ────────────────────────────────────
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return

        api = data.get("api", {})

        # New dual-model format
        lang = api.get("language", {})
        if lang:
            self.language.provider = lang.get("provider", self.language.provider)
            self.language.model = lang.get("model", self.language.model)
            self.language.api_key = lang.get("api_key", "")
            self.language.endpoint = lang.get("endpoint", self.language.endpoint)
            self.language.cooldown = float(lang.get("cooldown_seconds", 25))
            self.language.timeout = float(lang.get("timeout_seconds", 8))

        vis = api.get("vision", {})
        if vis:
            self.vision.provider = vis.get("provider", self.vision.provider)
            self.vision.model = vis.get("model", self.vision.model)
            self.vision.api_key = vis.get("api_key", "")
            self.vision.endpoint = vis.get("endpoint", self.vision.endpoint)
            self.vision.cooldown = float(vis.get("cooldown_seconds", 30))
            self.vision.timeout = float(vis.get("timeout_seconds", 10))

        # Backward compat: old flat format
        if not lang and not vis and api.get("provider"):
            old_provider = api.get("provider", "")
            if old_provider == "doubao":
                self.language.provider = "doubao"
                self.language.model = api.get("doubao_model", self.language.model)
                self.language.api_key = api.get("doubao_api_key", "")
                self.language.endpoint = api.get("doubao_endpoint", self.language.endpoint)
            elif old_provider == "deepseek":
                self.language.provider = "deepseek"
                self.language.model = api.get("deepseek_model", self.language.model)
                self.language.api_key = api.get("deepseek_api_key", "")
                self.language.endpoint = "https://api.deepseek.com/v1/chat/completions"

        # Env var overrides
        ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
        db_key = os.environ.get("DOUBAO_API_KEY", "")
        if ds_key and not self.language.api_key:
            self.language.api_key = ds_key
        if db_key and not self.vision.api_key:
            self.vision.api_key = db_key

        dbg = data.get("debug", {})
        self.log_level = dbg.get("log_level", "DEBUG")

    # ── Convenience (backward compat) ──────────────────

    @property
    def ai_available(self) -> bool:
        """Language model available?"""
        return self.language.available

    @property
    def provider(self) -> str:
        return self.language.provider

    @property
    def model(self) -> str:
        return self.language.model

    @property
    def api_key(self) -> str:
        return self.language.api_key

    @property
    def endpoint(self) -> str:
        return self.language.endpoint

    @property
    def cooldown(self) -> float:
        return self.language.cooldown

    @property
    def timeout(self) -> float:
        return self.language.timeout

    @property
    def is_multimodal(self) -> bool:
        return True  # vision model always configured


cfg = AppConfig()
