"""
Seedance 1.0 Video Generation Client.

Uses Volcano Engine Ark API for text-to-video generation.
Creates tasks, polls for completion, downloads generated video.

Endpoints differ from chat completions:
    Create: POST /api/v3/contents/generations/tasks
    Poll:   GET  /api/v3/contents/generations/tasks/{id}

Design:
    - Async task model: create → poll → download
    - Config from config.json → api.vision
    - Mock mode if API unavailable
"""

import json
import os
import time
import urllib.request
import urllib.error
from typing import Optional


# ============================================================
# Seedance Client
# ============================================================

class SeedanceClient:
    """Video generation client for Doubao Seedance 1.0.

    Usage:
        client = SeedanceClient()
        task_id = client.create(prompt="A field of white daisies under blue sky")
        result = client.poll_until_done(task_id)  # blocks until complete
        client.download(result["video_url"], "output.mp4")
    """

    CREATE_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
    POLL_URL   = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{id}"
    POLL_INTERVAL = 3.0      # seconds between polls
    MAX_POLL_TIME = 120.0    # max seconds to wait

    def __init__(self, api_key: str = "", model: str = "",
                 timeout: float = 10.0) -> None:
        """Load config from config.json or accept explicit params.

        Args:
            api_key: API key override.
            model: Model name override.
            timeout: HTTP timeout in seconds.
        """
        from ..config_loader import cfg
        vis = cfg.vision
        self.api_key = api_key or vis.api_key
        self.model = model or vis.model
        self.timeout = timeout
        self.available = bool(self.api_key)

        # Track latest task for logging
        self.last_task_id: Optional[str] = None
        self.last_video_url: Optional[str] = None

    # ── Create Task ───────────────────────────────────

    def create(
        self,
        prompt: str,
        duration: int = 5,
        ratio: str = "16:9",
        resolution: str = "720p",
        watermark: bool = False,
        seed: int = -1,
    ) -> Optional[str]:
        """Submit a video generation task.

        Args:
            prompt: Text description of the video.
            duration: Video duration in seconds (2-12).
            ratio: Aspect ratio ("16:9", "9:16", "1:1", etc.).
            resolution: "480p", "720p", or "1080p".
            watermark: Whether to include watermark.
            seed: Random seed (-1 for random).

        Returns:
            Task ID string, or None on failure.
        """
        if not self.available:
            print("[Seedance] API key not configured — skipping")
            return None

        payload = {
            "model": self.model,
            "content": [{"type": "text", "text": prompt}],
            "duration": duration,
            "ratio": ratio,
            "resolution": resolution,
            "watermark": watermark,
            "seed": seed,
        }

        print(f"[Seedance] Creating task: \"{prompt[:60]}...\" "
              f"({duration}s, {ratio}, {resolution})")

        try:
            req = urllib.request.Request(
                self.CREATE_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                })
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            task_id = data.get("id", "")
            if task_id:
                self.last_task_id = task_id
                print(f"[Seedance] Task created: {task_id}")
                return task_id
            else:
                print(f"[Seedance] No task ID in response: {data}")
                return None

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            print(f"[Seedance] HTTP {e.code}: {body[:300]}")
            return None
        except Exception as e:
            print(f"[Seedance] Error: {e}")
            return None

    # ── Poll ──────────────────────────────────────────

    def poll(self, task_id: str) -> Optional[dict]:
        """Check task status. Returns full response dict or None."""
        if not self.available:
            return None

        url = self.POLL_URL.format(id=task_id)
        try:
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            print(f"[Seedance] Poll HTTP {e.code}: {body[:200]}")
            return None
        except Exception as e:
            print(f"[Seedance] Poll error: {e}")
            return None

    def poll_until_done(self, task_id: str) -> Optional[dict]:
        """Block until task completes. Returns success dict or None.

        Args:
            task_id: Task ID from create().

        Returns:
            {"video_url": "...", "duration": 5, ...} or None.
        """
        start = time.time()
        print(f"[Seedance] Polling {task_id}...")

        while time.time() - start < self.MAX_POLL_TIME:
            data = self.poll(task_id)
            if data is None:
                time.sleep(self.POLL_INTERVAL)
                continue

            status = data.get("status", "unknown")
            print(f"[Seedance] Status: {status} "
                  f"({time.time() - start:.0f}s elapsed)")

            if status == "succeeded":
                content = data.get("content", {})
                video_url = content.get("video_url", "")
                if video_url:
                    self.last_video_url = video_url
                    print(f"[Seedance] Complete! Video: {video_url[:80]}...")
                    return {
                        "video_url": video_url,
                        "duration": data.get("duration", 5),
                        "frames": data.get("frames", 0),
                        "ratio": data.get("ratio", "16:9"),
                        "seed": data.get("seed", -1),
                    }
                else:
                    print("[Seedance] Succeeded but no video_url in response")
                    return None

            elif status in ("failed", "expired", "cancelled"):
                error = data.get("error", {})
                print(f"[Seedance] Task {status}: {error}")
                return None

            time.sleep(self.POLL_INTERVAL)

        print(f"[Seedance] Timeout after {self.MAX_POLL_TIME:.0f}s")
        return None

    # ── Download ──────────────────────────────────────

    def download(self, video_url: str, output_path: str) -> bool:
        """Download generated video to local file.

        Args:
            video_url: URL from poll_until_done() result.
            output_path: Local path to save the video.

        Returns:
            True on success.
        """
        print(f"[Seedance] Downloading: {video_url[:60]}...")
        try:
            req = urllib.request.Request(video_url)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(data)
            size_kb = len(data) / 1024
            print(f"[Seedance] Downloaded: {output_path} ({size_kb:.0f} KB)")
            return True
        except Exception as e:
            print(f"[Seedance] Download failed: {e}")
            return False


# ============================================================
# Mock Client — for offline/dev mode
# ============================================================

class MockSeedance:
    """Simulates successful video generation for offline dev."""

    def __init__(self) -> None:
        self.available = False

    def create(self, prompt: str = "", **kw) -> Optional[str]:
        print(f"[Seedance Mock] Create task for: \"{prompt[:50]}...\"")
        return f"mock-{int(time.time())}"

    def poll(self, task_id: str) -> Optional[dict]:
        return {"status": "succeeded",
                "content": {"video_url": ""},
                "duration": 5, "frames": 120, "ratio": "16:9"}

    def poll_until_done(self, task_id: str) -> Optional[dict]:
        print(f"[Seedance Mock] Task {task_id} completed (mock)")
        return {"video_url": "", "duration": 5,
                "frames": 120, "ratio": "16:9", "seed": 42}

    def download(self, video_url: str, output_path: str) -> bool:
        print(f"[Seedance Mock] Skipped download (mock mode)")
        return True
