"""
Standalone Seedance 1.0 API test. Zero project dependencies.

Usage: python scripts/seedance_test.py

Reads ../config.json for vision model credentials.
Creates a video → polls → downloads → saves.
"""

import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config.json")

# ── Load config ───────────────────────────────────────
with open(CFG_PATH, encoding="utf-8") as f:
    cfg = json.load(f)
vis = cfg.get("api", {}).get("vision", {})
API_KEY = vis.get("api_key", "") or os.environ.get("DOUBAO_API_KEY", "")
MODEL = vis.get("model", "doubao-seedance-1.0-pro-250528")
ENDPOINT = vis.get("endpoint", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
TIMEOUT = int(vis.get("timeout_seconds", 10))

# Override endpoint for Seedance (different from chat)
CREATE_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
POLL_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{id}"

print(f"[Test] API Key: {'***' + API_KEY[-8:] if API_KEY else 'MISSING'}")
print(f"[Test] Model: {MODEL}")
print(f"[Test] Create URL: {CREATE_URL}")

if not API_KEY:
    print("\n[FAIL] No API key for vision model.")
    print("  Edit config.json → api.vision.api_key")
    sys.exit(1)

# ── Step 1: Create task ───────────────────────────────
prompt = "写实风格，广阔的深蓝色星空下，一片安静的麦田随风轻轻摇摆，镜头缓慢向前推进，画面宁静而梦幻"
payload = json.dumps({
    "model": MODEL,
    "content": [{"type": "text", "text": prompt}],
    "duration": 5,
    "ratio": "16:9",
    "resolution": "480p",
    "watermark": False,
}).encode("utf-8")

print(f"\n[Step 1] Creating task...")
print(f"  Prompt: {prompt}")
print(f"  Payload: {len(payload)} bytes")

start = time.time()
req = urllib.request.Request(
    CREATE_URL, data=payload,
    headers={"Content-Type": "application/json",
             "Authorization": f"Bearer {API_KEY}"})

try:
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"[Step 1] HTTP {e.code}: {e.read().decode()[:500]}")
    sys.exit(2)

task_id = data.get("id", "")
if not task_id:
    print(f"[Step 1] No task ID: {data}")
    sys.exit(3)

print(f"[Step 1] Task created: {task_id}")

# ── Step 2: Poll ──────────────────────────────────────
print(f"\n[Step 2] Polling... (max 120s)")
elapsed = 0
while elapsed < 120:
    req = urllib.request.Request(
        POLL_URL.format(id=task_id),
        headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            poll = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[Step 2] Poll error: {e}")
        time.sleep(3); elapsed += 3; continue

    status = poll.get("status", "?")
    elapsed = time.time() - start
    print(f"[Step 2] {status} ({elapsed:.0f}s)")

    if status == "succeeded":
        video_url = poll.get("content", {}).get("video_url", "")
        if video_url:
            print(f"[Step 2] Video ready: {video_url[:80]}...")
            break
        else:
            print("[Step 2] No video_url in success response")
            sys.exit(4)
    elif status in ("failed", "expired", "cancelled"):
        print(f"[Step 2] Task {status}: {poll.get('error', {})}")
        sys.exit(5)

    time.sleep(3)

# ── Step 3: Download ──────────────────────────────────
print(f"\n[Step 3] Downloading...")
req = urllib.request.Request(video_url)
with urllib.request.urlopen(req, timeout=60) as resp:
    video_data = resp.read()

out_path = os.path.join(ROOT, "seedance_output.mp4")
with open(out_path, "wb") as f:
    f.write(video_data)

print(f"[Step 3] Saved: {out_path} ({len(video_data)/1024:.0f} KB)")
total = time.time() - start
print(f"\n[PASS] Total time: {total:.0f}s")
print(f"[PASS] Output: {out_path}")
