<div align="center">

# The Unseen · 不可见

*A living digital ecosystem that sees you, remembers you, and grows because of you.*

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MediaPipe](https://img.shields.io/badge/Perception-MediaPipe-orange)](https://developers.google.com/mediapipe)
[![py5](https://img.shields.io/badge/Render-py5-ff69b4)](https://py5coding.org/)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek%20%7C%20Doubao-purple)](https://platform.deepseek.com)

> *"People cannot directly see their own existence, but the world always records their impact."*
> *「人无法直接看到自己的存在，但世界始终记录着人的影响。」*

</div>

---

## About

**The Unseen** is an interactive generative art installation that creates a living digital ecosystem with artificial consciousness.

Your webcam perceives your hands. Particles follow your movements. Ripples spread where you wave. Digital organisms are born where you pause. An AI brain watches everything — adjusting the world's mood, weather, and life strategies based on your behavior.

You are not an operator. You are a visitor in a world that breathes, thinks, and remembers.

---

## Quick Start

```bash
git clone <repo-url>
cd The_Unseen
pip install -r requirements.txt
python -m the_unseen
```

```bash
python -m the_unseen --fresh      # Clear all memory
python -m the_unseen --release    # Production mode (quiet logs)
python -m the_unseen --camera     # Enable webcam background
```

### Keyboard Controls

| Key | Action |
|-----|--------|
| `D` | Toggle debug overlay (FPS sparkline, energy, gesture, mood, weather) |
| `F` | Toggle FPS badge |
| `C` | Toggle camera background |
| `R` | Toggle debug / release log mode |
| `Q` | Exit with Presence Report |

---

## Project Structure

```
The_Unseen/
├── README.md
├── LICENSE
├── requirements.txt
├── config.template.json
├── .gitignore
│
├── the_unseen/                     # Main package
│   ├── __main__.py                 # Entry point + py5 sketch
│   ├── main.py                     # Helper functions
│   ├── config.py                   # Parameters + Palette.Theme
│   ├── config_loader.py            # config.json reader
│   ├── state.py                    # AppState singleton
│   │
│   ├── perception/                 # Perception layer
│   │   ├── camera_tracker.py       # MediaPipe + OpenCV
│   │   └── hand_state.py           # Hand position smoothing
│   │
│   ├── simulation/                 # Simulation layer
│   │   ├── flow_field.py           # Perlin Noise 2D flow field
│   │   ├── influence_field.py      # Hand influence field
│   │   ├── particle.py             # Particle lifecycle
│   │   ├── particle_manager.py     # 3-layer particle system
│   │   └── space_state.py          # Space state machine
│   │
│   ├── life/                       # Life layer
│   │   ├── memory_seed.py          # Memory seeds
│   │   ├── growth_algorithm.py     # DLA growth engine
│   │   ├── organism.py             # Digital organisms + ecosystem
│   │   ├── energy_manager.py       # Global energy system
│   │   ├── behavior_analyzer.py    # User behavior statistics
│   │   ├── time_system.py          # Day/night cycle
│   │   └── persistence.py          # JSON state persistence
│   │
│   ├── interaction/                # Interaction layer
│   │   ├── gesture_manager.py      # Hand gesture recognition
│   │   ├── ability_base.py         # BaseAbility + SpaceMood
│   │   ├── ability_manager.py      # 6 space abilities
│   │   ├── interaction_rules.py    # Gesture → effect routing
│   │   ├── ripple.py               # Ripple system
│   │   └── fragment.py             # Memory fragments
│   │
│   ├── feedback/                   # Feedback layer
│   │   ├── feedback_composer.py    # Camera + Time + Post effects
│   │   ├── procedural_bg.py        # Procedural background
│   │   ├── visual_system.py        # Depth + Particle variety + Lighting
│   │   ├── camera_background.py    # Webcam background + 10 filters
│   │   └── audio_hook.py           # Audio interface (reserved)
│   │
│   ├── world/                      # World layer
│   │   ├── world_state.py          # WorldState singleton
│   │   ├── perception.py           # Organism perception
│   │   ├── organism_ai.py          # Autonomous organism AI
│   │   └── living_world.py         # Ecosystem + Weather + Exhibition
│   │
│   ├── ai/                         # AI layer
│   │   ├── presence.py             # WorldBrain + PresenceEngine
│   │   ├── llm_interface.py        # LLMInterface + RuleEngine
│   │   ├── llm_client.py           # Unified API client
│   │   ├── deepseek_client.py      # DeepSeek client
│   │   ├── seedance_client.py      # Seedance video generation
│   │   └── behavior_reporter.py    # Behavior data aggregator
│   │
│   ├── ui/                         # UI layer
│   │   ├── render_utils.py         # Hand auras + startup hints
│   │   └── debug_overlay.py        # Performance HUD
│   │
│   └── utils/                      # Utilities
│       ├── logger.py               # Structured logging
│       └── easing.py               # Easing functions
│
├── tests/                           # Tests
│   └── test_imports.py
│
├── scripts/                         # Dev tools
│   ├── deepseek_test.py            # Language model API test
│   └── seedance_test.py            # Video generation API test
│
└── docs/                            # Documentation (reserved)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Camera + MediaPipe                   │
└─────────────────────────┬───────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   GestureManager  InfluenceField   SpaceState
          │               │               │
          ▼               ▼               │
  SpaceAbilityMgr   FlowField             │
          │               │               │
          ├───────────────┤               │
          ▼               ▼               │
   FeedbackComposer  ParticleManager      │
          │          (3 layers)           │
          │               │               │
          │   ┌───────────┼───────────┐   │
          │   ▼           ▼           ▼   │
          │ RippleMgr FragmentMgr OrganismMgr
          │   │           │           │   │
          │   └───────────┼───────────┘   │
          │               ▼               │
          │         WorldState(W)         │
          │               │               │
          │   ┌───────────┼───────────┐   │
          │   ▼           ▼           ▼   │
          │ OrganismAI Ecosystem  Weather  │
          │                              │
          │         ┌────────────────────┘
          │         ▼
          │   WorldBrain ← LLMClient (DeepSeek/Doubao)
          │         │         ← MockBrain (offline fallback)
          │         ▼
          │   Mood / Weather / Lighting / Strategy / Narrative
          │         │
          │         ▼
          └──→ PresenceEngine (The Core / breath / attention)
                    │
                    ▼
               Render (py5)
                    │
                    ▼
            Persistence (JSON)
```

---

## AI Configuration

Copy the template and fill in your API keys:

```bash
cp config.template.json config.json
```

Then edit `config.json`:

```json
{
  "api": {
    "language": {
      "provider": "deepseek",
      "model": "deepseek-chat",
      "api_key": "sk-your-key",
      "endpoint": "https://api.deepseek.com/v1/chat/completions",
      "cooldown_seconds": 25,
      "timeout_seconds": 8
    },
    "vision": {
      "provider": "doubao",
      "model": "doubao-seedance-1-0-pro-250528",
      "api_key": "ark-your-key",
      "endpoint": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
      "cooldown_seconds": 30,
      "timeout_seconds": 10
    }
  }
}
```

- **`language`** — Text analysis (DeepSeek, Doubao, any OpenAI-compatible API)
- **`vision`** — Video/image generation (Doubao Seedance 1.0)
- **No key?** → Automatically uses RuleEngine (deterministic offline mode, always available)

### Testing the API

```bash
python scripts/deepseek_test.py     # Test language model connection
python scripts/seedance_test.py     # Test video generation end-to-end
```

---

## AI Presence

### The Core

A glowing orb at the center of the world. It breathes, changes color with the AI's mood, drifts toward the user, pulses when "thinking", and flashes when making decisions. It is the visual body of the artificial consciousness.

### Analysis Cycle (every 10 seconds)

1. The Core enters **Thinking** state (aura expands)
2. Behavior data is sent to the language model (or MockBrain)
3. AI returns structured JSON: mood · weather · lighting · organism strategy · narrative
4. A poetic sentence appears at the bottom of the screen (5-second fade)
5. Green pulsing indicator in top-right shows current mood

### Emotion → World Modulation

| Emotion | Core Color | Flow Speed | Organism Behavior | Camera Filter |
|---------|-----------|------------|-------------------|---------------|
| Calm | Blue | 0.7× | 0.6× | normal |
| Hope | Gold | 1.0× | 1.2× | warm |
| Curiosity | Light Blue | 1.2× | 1.5× | ai_vision |
| Dream | Purple | 0.5× | 0.8× | dream |
| Silence | Deep Blue | 0.4× | 0.4× | noir |
| Bloom | Pink | 1.4× | 1.8× | glitch |
| Lonely | Cyan | 0.3× | 0.3× | cold |

---

## Camera Background

Enable with `--camera` flag or `C` key. Features 10 real-time OpenCV filters that switch automatically with the AI's mood.

| Filter | Effect |
|--------|--------|
| `normal` | Original webcam feed |
| `grayscale` | Black and white |
| `warm` | Golden tone (red +30%, blue -30%) |
| `cold` | Blue tone (blue +40%, red -40%) |
| `dream` | Gaussian blur + purple overlay |
| `noir` | High contrast + vignette |
| `ai_vision` | Cyan-green futuristic tech look |
| `sketch` | Sobel edge detection |
| `pixel` | Low-resolution pixel art |
| `glitch` | Horizontal slice shift + channel offset |

All filters operate on the background only — foreground particles, UI, and organisms are never affected.

---

## Gesture Interaction

| Gesture | Ability | Charge | Cooldown | Mood | Effect |
|---------|---------|--------|----------|------|--------|
| 🖐️ Open Palm | Connect | 0.5s | 3s | Calm | Particles gather, organisms approach |
| ✊ Fist | Gather | 1.0s | 3s | Focused | Energy ring, flow compression |
| 🤏 Pinch | Create | 1.5s | 5s | Hope | Golden seed → DLA organism birth |
| ☝️ Point | Guide | 0.3s | 1s | Curiosity | Flow follows finger, trail particles |
| 🙌 Two-Hand Expand | Expand | 0.8s | 4s | Freedom | Particles spread, camera zooms out |
| 🙌 Two-Hand Compress | Merge | 2.0s | 6s | Harmony | Organism connection bridge |
| Wave | Ripple | — | — | — | Expanding rings push particles |
| Hold Still | Seed | 1.5s | — | — | Purple seed → autonomous organism |

### Gesture State Machine

```
IDLE → PREPARING → CHARGING (0.3s–2s) → ACTIVATED → COOLDOWN → IDLE
                   ↑ gesture released = cancel
```

Gestures must be **held continuously** to charge. Releasing mid-charge cancels the ability. This gives each action weight — you must commit.

---

## Digital Ecosystem

### Memory Seeds & DLA Growth

When your hand stays in one area for 1.5 seconds, a memory seed is planted. As the seed accumulates energy, it grows via **Diffusion Limited Aggregation** — an algorithm that simulates the organic branching patterns found in lightning, coral, and tree roots. Each seed produces a unique structure.

### Autonomous Organisms

Every organism has independent AI: states (idle, explore, observe, follow, flee, sleep, fade), emotions (curiosity, fear, affinity), and perception of the world.

### Ecological Rules

| Distance | Effect |
|----------|--------|
| < 120 px | Competition — growth slowed for both |
| 120–200 px | Attraction — swarming behavior |
| > 200 px | Independent |

### Space Weather

Weather cycles every 20–40 seconds. AI can override weather for 20-second periods.

| Weather | Flow | Organism Speed | Color Shift |
|---------|------|---------------|-------------|
| Calm | 0.7× | 0.6× | Cool blue |
| Wind | 1.3× | 1.0× | Neutral |
| Storm | 1.8× | 1.5× | Warm gold |
| Aurora | 1.1× | 1.3× | Purple |

---

## Dependencies

```
mediapipe>=0.10.14
opencv-python>=4.8.0
py5>=0.10.0
numpy>=1.26.0
```

---

## Version History

| Version | Theme | Status |
|---------|-------|--------|
| V1 | Basic interaction — particles follow hands | ✅ |
| V2 | Responsive space — flow field, influence field, state machine | ✅ |
| V3 | Digital life — DLA growth, energy system, persistence | ✅ |
| V4 | Spatial gesture language — single process, 6 abilities, ripples | ✅ |
| V5 | Immersive feedback — Camera, Time, Post, Lighting systems | ✅ |
| V6 | Visual identity — procedural background, state themes, particle variety | ✅ |
| V7 | Digital ecosystem — autonomous AI organisms, weather, exhibition mode | ✅ |
| V8 | World consciousness — AI presence, The Core, camera filters, dual-model API | ✅ |

---

## License

MIT — free for learning, art, and creative use.

## Acknowledgments

- [MediaPipe](https://developers.google.com/mediapipe) — hand tracking
- [py5](https://py5coding.org/) — creative coding framework
- [Processing](https://processing.org/) — the project that started it all
- [DeepSeek](https://platform.deepseek.com) — language model API
- [Volcano Engine ARK](https://www.volcengine.com/docs/82379) — Seedance API
