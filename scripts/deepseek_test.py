"""
Standalone DeepSeek / Doubao API test. Zero project dependencies.

Usage: python deepseek_test.py
Reads ../config.json for credentials. Falls back to env vars.
"""
import json, os, sys, time, urllib.request, urllib.error

# ── Locate config.json ───────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config.json")

def load_config():
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        api = data.get("api", {})
        lang = api.get("language", api)  # dual-mode or legacy
        return {
            "provider": lang.get("provider", "deepseek"),
            "model": lang.get("model", "deepseek-chat"),
            "api_key": lang.get("api_key", "") or os.environ.get("DEEPSEEK_API_KEY", ""),
            "endpoint": lang.get("endpoint", "https://api.deepseek.com/v1/chat/completions"),
            "timeout": int(lang.get("timeout_seconds", 8)),
        }
    return {}

cfg = load_config()
if not cfg.get("api_key"):
    print("[FAIL] No API key found.")
    print("  Check: config.json → api.language.api_key")
    print("  Or:    set DEEPSEEK_API_KEY environment variable")
    sys.exit(1)

# ── Build request ────────────────────────────────────
payload = {
    "model": cfg["model"],
    "messages": [
        {"role": "system", "content": "Reply with ONLY valid JSON: {\"greeting\":\"hello\",\"mood\":\"curious\"}"},
        {"role": "user", "content": "Say hello."},
    ],
    "temperature": 0.3,
    "max_tokens": 50,
}

print(f"[TEST] Provider: {cfg['provider']}")
print(f"[TEST] Model:    {cfg['model']}")
print(f"[TEST] Endpoint: {cfg['endpoint']}")
print(f"[TEST] Key:      ***{cfg['api_key'][-8:]}")
print()

# ── Send ─────────────────────────────────────────────
print("[HTTP] Connecting...")
start = time.time()

req = urllib.request.Request(
    cfg["endpoint"],
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['api_key']}",
    })

try:
    with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
        elapsed = time.time() - start
        body = resp.read().decode("utf-8")
        data = json.loads(body)

        print(f"[HTTP] Status: {resp.status}")
        print(f"[HTTP] Elapsed: {elapsed:.2f}s")
        print(f"[HTTP] Model used: {data.get('model', '?')}")
        usage = data.get("usage", {})
        print(f"[HTTP] Tokens: prompt={usage.get('prompt_tokens','?')} "
              f"completion={usage.get('completion_tokens','?')}")

        content = data["choices"][0]["message"]["content"]
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rstrip("```")
        try:
            parsed = json.loads(content)
            print(f"[JSON] Parsed OK: {parsed}")
        except json.JSONDecodeError:
            print(f"[JSON] Raw content: {content}")

        print()
        print("[PASS] API connection successful.")

except urllib.error.HTTPError as e:
    elapsed = time.time() - start
    body = e.read().decode("utf-8")
    print(f"[FAIL] HTTP {e.code} after {elapsed:.2f}s")
    print(f"[FAIL] Response: {body[:500]}")
    sys.exit(2)

except urllib.error.URLError as e:
    elapsed = time.time() - start
    print(f"[FAIL] Network error after {elapsed:.2f}s: {e.reason}")
    sys.exit(3)

except Exception as e:
    print(f"[FAIL] {type(e).__name__}: {e}")
    sys.exit(4)
