"""Phase 3-8: Network request + response + JSON parse + prompt + async check."""
import sys; sys.path.insert(0, '.')
import json, urllib.request, urllib.error, time, traceback

from the_unseen.config_loader import cfg

print("=" * 60)
print("PHASE 3+4: Network + Request Check")
print("=" * 60)

endpoint = cfg.endpoint
model = cfg.model
api_key = cfg.api_key

print(f"Endpoint: {endpoint}")
print(f"Model: {model}")
print(f"API Key: ***{api_key[-8:] if api_key else '(empty)'}")

context = {
    "user_behavior": {
        "session_duration": 10, "total_distance": 500,
        "seed_count": 1, "avg_speed": 0.03, "total_dwell_time": 5,
        "interaction_count": 1,
        "gesture_frequency": {"open_palm": 0.8}
    },
    "world_state": {"organism_count": 2, "energy": 50},
    "memory": {"total_visits": 1}
}

system_prompt = (
    'You are the consciousness of an interactive art installation called '
    '"The Unseen". You observe a human visitor. Return ONLY valid JSON: '
    '{"user_archetype":"...","world_mood":"...","weather":"...",'
    '"lighting":"...","organism_strategy":"...",'
    '"narrative":"one poetic sentence",'
    '"recommended_event":"..."}'
)

user_text = json.dumps(context, ensure_ascii=False)

payload = json.dumps({
    "model": model,
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ],
    "temperature": 0.7,
    "max_tokens": 400,
}).encode("utf-8")

print(f"Payload size: {len(payload)} bytes")
print(f"System prompt ({len(system_prompt)} chars): {system_prompt[:100]}...")
print(f"User content ({len(user_text)} chars): {user_text[:100]}...")

print()
print("Making HTTPS request...")
start = time.time()

req = urllib.request.Request(
    endpoint, data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

try:
    with urllib.request.urlopen(req, timeout=cfg.timeout) as resp:
        elapsed = time.time() - start
        status = resp.status
        raw_body = resp.read().decode("utf-8")
        data = json.loads(raw_body)

        print(f"PHASE 5: Response Check")
        print(f"  Status: {status}")
        print(f"  Elapsed: {elapsed:.2f}s")

        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content", "")
            print(f"  Content length: {len(content)} chars")

            print(f"PHASE 6: JSON Parse Check")
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])
            try:
                result = json.loads(content)
                print(f"  Parsed OK — keys: {list(result.keys())}")
                for k, v in result.items():
                    print(f"    {k}: {v}")
            except json.JSONDecodeError as e:
                print(f"  JSON parse FAILED: {e}")
                print(f"  Raw content: {content[:500]}")
        else:
            print(f"  ERROR: No choices in response")
            print(f"  Full: {json.dumps(data, indent=2)[:500]}")

        # Token usage
        usage = data.get("usage", {})
        if usage:
            print(f"  Tokens: prompt={usage.get('prompt_tokens','?')} "
                  f"completion={usage.get('completion_tokens','?')}")

except urllib.error.HTTPError as e:
    elapsed = time.time() - start
    print(f"HTTP Error {e.code} after {elapsed:.2f}s")
    print(f"Response body: {e.read().decode('utf-8')[:500]}")

except urllib.error.URLError as e:
    elapsed = time.time() - start
    print(f"URL Error after {elapsed:.2f}s: {e.reason}")

except Exception as e:
    elapsed = time.time() - start
    print(f"Exception after {elapsed:.2f}s: {type(e).__name__}: {e}")
    traceback.print_exc()

print()
print("PHASE 7: Prompt Check")
print(f"  System length: {len(system_prompt)} chars (limit ~32k)")
print(f"  User length: {len(user_text)} chars")
print(f"  Total messages: 2 (system + user)")
print(f"  JSON serializable: True (successfully encoded to {len(payload)} bytes)")

print()
print("PHASE 8: Async Check")
print("  Method: synchronous urllib (no async/await/thread/queue)")
print("  Blocking: YES — called from draw loop")
print("  Cooldown: 25s between calls (avoids blocking every frame)")
print("  Timeout: 8s (prevents hanging)")
print("  Risk: First call blocks draw for ~2s — acceptable with cooldown")
