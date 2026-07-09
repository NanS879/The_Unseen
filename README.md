# The Unseen · 不可见

> "人无法直接看到自己的存在，但世界始终记录着人的影响。"
> "People cannot directly see their own existence, but the world always records their impact."

## 项目简介

**The Unseen** 是一个探索人与数字空间之间隐性关系的生成式交互艺术作品。

通过摄像头与 AI 感知，你的手在由数千个粒子组成的数字生态系统中产生不可见的力场——划过空气，留下光的痕迹。你不是在控制粒子，而是在改变整个空间。

---

## 版本

### V3 — Digital Organism（数字生命） ← 当前版本

空间不仅是响应式的——它**记住你**，并因为你而**生长**：

- 🌱 **记忆种子** — 手停留超过 2 秒，种下一颗"记忆种子"
- 🔬 **DLA 生长** — 种子用扩散限制聚合算法生长为有机分枝结构
- ⚡ **能量系统** — 移动产生能量，停留将能量转化为生命生长
- 🌲 **数字森林** — 多个生命体共存，距离近则竞争、适中则连接、远则独立
- 🌅 **昼夜循环** — 5 分钟周期，流场/辉光/生长/色温随"时间"变化
- 📊 **行为分析** — 统计总距离、平均速度、停留时间、交互次数
- 💾 **持久化** — JSON 自动存储，重启后空间继续生长

### V2 — Responsive Space（响应式空间）

整个空间成为一个具有生命感的数字生态系统：

- 🌬️ **呼吸感** — Perlin Noise 流场持续缓慢演化
- 🌊 **流动感** — 三层粒子叠加，运动尾迹
- 🎚️ **层次感** — Background / Interaction / Highlight 三层独立行为
- 🧬 **生命周期** — 每个粒子经历 birth → growth → peak → decay → death → respawn
- 🧠 **空间状态机** — IDLE / ACTIVE / EXCITED / CALM 四态自动切换
- 🎨 **统一色板** — 蓝 / 紫 / 金

### V1 — Basic Interaction（基础交互）

> 用户移动手掌，粒子跟随运动。（已完成）

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 感知 | **MediaPipe Hands** | 双手 21 点关键点检测 |
| 采集 | **OpenCV** | 摄像头实时捕获 |
| 通信 | **python-osc** | UDP 进程间实时通信 |
| 渲染 | **py5** (Processing Python) | 生成艺术 / 粒子系统 / Perlin Noise |
| 数学 | **Perlin Noise 3D** | 流场向量生成 |

---

## 项目结构

```
The_Unseen/
├── python_tracker/              # 手部追踪 + OSC 发送端
│   ├── main.py                  # 摄像头采集主循环
│   ├── hand_tracking.py         # MediaPipe Hands 封装（双手）
│   ├── osc_sender.py            # OSC 发送客户端
│   ├── test_osc_receiver.py     # OSC 接收测试工具
│   └── requirements.txt
│
├── py5_visual/                  # 生成艺术渲染端
│   ├── main.py                  # py5 主入口（V2+V3 编排）
│   ├── config.py                # 集中参数管理（V2+V3 所有参数）
│   │
│   ├── V2 模块：
│   ├── flow_field.py            # Perlin Noise 2D 流场
│   ├── influence_field.py       # 手部影响场（引力 + 尾流）
│   ├── particle.py              # 粒子（生命周期 + 尾迹 + 发光）
│   ├── particle_manager.py      # 三层粒子编排器
│   ├── space_state.py           # 空间状态机（IDLE/ACTIVE/EXCITED/CALM）
│   ├── hand_state.py            # 手部状态 + OSC 服务端
│   ├── render_utils.py          # 视觉润色（光环、暗角、状态面板）
│   │
│   ├── V3 模块：
│   ├── memory_seed.py           # 记忆种子（位置/能量/序列化）
│   ├── growth_algorithm.py      # DLA 扩散限制聚合生长引擎
│   ├── organism.py              # 数字生命体 + 生态系统管理器
│   ├── energy_manager.py        # 统一能量系统
│   ├── behavior_analyzer.py     # 用户行为统计分析
│   ├── time_system.py           # 昼夜循环时间系统
│   ├── persistence.py           # JSON 持久化存储
│   │
│   └── requirements.txt
│   ├── particle.py              # 粒子（生命周期 + 运动尾迹 + 发光）
│   ├── particle_manager.py      # 三层粒子编排器
│   ├── space_state.py           # 空间状态机（4 态）
│   ├── hand_state.py            # 手部状态 + OSC 服务端
│   ├── render_utils.py          # 视觉润色（光环、暗角、状态面板）
│   └── requirements.txt
│
├── requirements.txt             # 统一依赖
├── .gitignore
└── README.md
```

---

## 系统架构

```
Config（集中参数）
    │
    ├──→ FlowField ────────────┐
    │     Perlin Noise 流场     │
    │     · get_force(x,y)     │
    │     · enabled toggle     │
    │                          │
    ├──→ InfluenceField ───────┤
    │     手部影响场            ├──→ ParticleManager ──→ main.py
    │     · 引力 + 尾流        │     三层粒子编排         draw() 循环
    │     · 反平方/高斯衰减    │
    │                          │
    └──→ SpaceState ───────────┘
         空间状态机
         · IDLE/ACTIVE/EXCITED/CALM
         · 状态驱动乘数
```

---

## 子系统详解

### 1. FlowField（流场）— [flow_field.py](py5_visual/flow_field.py)

二维 Perlin Noise 向量场。空间中每个位置都有一个方向向量，粒子每帧根据位置读取对应方向。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `cell_size` | 25 | 网格精度（越小越精细） |
| `noise_scale` | 0.004 | 空间频率（越小漩涡越大） |
| `time_scale` | 0.006 | 时间演化速度 |
| `flow_strength` | 0.30 | 基础力强度 |
| `enabled` | True | 可独立开关，方便调试 |

**接口：** `update(time)`, `get_force(x, y)`, `toggle()`

### 2. InfluenceField（用户影响场）— [influence_field.py](py5_visual/influence_field.py)

根据手部位置生成空间影响区域。每个手产生两个力：

- **引力** — 将粒子拉向手的位置，随距离衰减
- **尾流** — 沿手运动方向推动粒子

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `radius` | 250 px | 最大影响半径 |
| `strength` | 800 | 基础引力强度 |
| `falloff` | inverse_square | 衰减方式（或 gaussian） |
| `wake_strength` | 3.0 | 尾流推力 |

**支持多手叠加**，天然支持未来多人交互扩展。

**接口：** `update(hands)`, `get_force(px, py)`, `get_influence_at(px, py)`

### 3. Particle（粒子）— [particle.py](py5_visual/particle.py)

每个粒子拥有完整的生命周期和运动尾迹。

#### 生命周期

```
age/life:  0%      10%      30%               70%       100%
            │ birth │ growth │      peak        │ decay  │ dead
 opacity:   0→255    255      255              255→0      respawn
    size:   0.3→1.0  1.0→1.15  1.0              1.0→0.3   respawn
```

#### 运动尾迹

- 存储最近 N 帧位置（deque），绘制为 Polyline
- 尾迹长度随当前速度动态缩放（越快尾迹越长）
- 透明度从头向尾衰减

#### 发光渲染

4 层同心圆：外层光晕 → 中层辉光 → 内层核心 → 灼热白心

**接口：** `apply_force()`, `update()`, `display()`, `is_dead()`, `respawn()`, `life_stage()`, `current_opacity()`, `current_size()`

### 4. ParticleManager（粒子管理器）— [particle_manager.py](py5_visual/particle_manager.py)

三层粒子系统，每层独立参数和行为：

| 层 | 名称 | 数量 | 速度 | 尺寸 | 颜色 | 受手影响 | 尾迹 |
|----|------|------|------|------|------|----------|------|
| 1 | Background | 2000 | 慢 (1.5) | 大 (2–5) | 深蓝 | ×0.05 | 短 |
| 2 | Interaction | 800 | 中 (3.5) | 中 (1.5–4) | 蓝紫 | ×1.0 | 中 |
| 3 | Highlight | 150 | 快 (5.0) | 小 (1–3.5) | 暖金 | ×2.0 | 长 |

**接口：** `update(flow, influence, multipliers)`, `display(py5, influence, trail_mult)`

### 5. SpaceState（空间状态机）— [space_state.py](py5_visual/space_state.py)

空间根据用户行为自动切换"情绪"：

```
         ┌──────────────────────────────┐
         │                              │
    ┌────▼────┐   手出现    ┌───────────┴──┐   快速挥手    ┌──────────┐
    │  IDLE   │───────────→│   ACTIVE    │──────────────→│ EXCITED  │
    │  无人   │←───────────│   活跃中     │               │  剧烈扰动 │
    └─────────┘  超时消失   └─────────────┘               └─────┬────┘
         ▲                              ↑                       │
         │          ┌──────────┐        │        减速           │
         └──────────│   CALM   │←───────┘                       │
             超时   │ 恢复平静 │←───────────────────────────────┘
                   └──────────┘
```

**状态驱动乘数：**

| 状态 | 流场速度 | 影响力 | 尾迹 | 背景残影 |
|------|----------|--------|------|----------|
| IDLE | ×0.5 | ×0.0 | ×0.5 | 浅 (α=8) |
| ACTIVE | ×1.0 | ×1.0 | ×1.0 | 中 (α=14) |
| EXCITED | ×2.0 | ×1.8 | ×2.0 | 深 (α=22) |
| CALM | ×0.7 | ×0.5 | ×0.8 | 中 (α=14) |

**接口：** `update(has_hands, max_speed)`, `state`, `flow_multiplier`, `influence_multiplier`, `trail_multiplier`, `trail_alpha`, `just_entered`

### 6. Config（集中参数）— [config.py](py5_visual/config.py)

所有可调参数集中管理，无魔法数字。

```python
from config import Config

# 画布
Config.WIDTH = 1920
Config.HEIGHT = 1080

# 粒子数量
Config.PARTICLE_BG_COUNT = 3000

# 流场
Config.FLOW_STRENGTH = 0.5

# 影响力
Config.INFLUENCE_RADIUS = 350

# 状态阈值
Config.STATE_EXCITED_SPEED = 0.08

# 颜色
Config.Palette.HL_BASE = (255, 150, 50)  # 高亮层改为橙色
```

---

## V3 子系统详解

### 7. MemorySeed（记忆种子）— [memory_seed.py](py5_visual/memory_seed.py)

当手在某个位置停留超过 2 秒，一颗记忆种子被种下。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SEED_DWELL_RADIUS` | 50 px | 手必须在此范围内 |
| `SEED_DWELL_TIME` | 2.0 s | 创建种子所需停留时间 |
| `SEED_MAX_ENERGY` | 100.0 | 最大能量 |
| `SEED_ENERGY_RATE` | 15.0/s | 停留时能量获取速率 |
| `SEED_GROWTH_THRESHOLD` | 60.0 | 生长所需能量阈值 |

**接口：** `update(dt, hand_near, speed)`, `display(py5)`, `serialize()/deserialize()`

### 8. DLA Growth（生长引擎）— [growth_algorithm.py](py5_visual/growth_algorithm.py)

扩散限制聚合（Diffusion Limited Aggregation）— 模拟闪电、珊瑚、树根的自然分枝形态。

- 每帧释放 25 个 walker，从边界随机游走
- 碰到已有结构就"粘住"，形成新的生长点
- 空间哈希网格 O(1) 碰撞检测
- 同一个种子每次生长结果都不同（不可预测性）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DLA_WALKERS_PER_FRAME` | 25 | 每帧 walker 数量 |
| `DLA_MAX_STEPS` | 120 | walker 最大步数 |
| `DLA_STICK_RADIUS` | 3.0 px | 接触距离 |
| `DLA_MAX_RADIUS` | 140 px | 最大生长半径 |

### 9. Organism（数字生命体）— [organism.py](py5_visual/organism.py)

Organism = MemorySeed + DLAEngine。种子能量达标后，消耗全局能量启动生长。

**生态系统规则：**
- 距离 < 40px：竞争，双方生长速度降低
- 距离 40–200px：独立生长，绘制连接线（菌丝网络）
- 距离 > 200px：完全独立
- 最多 8 个生命体共存（超出则移除最旧的）

### 10. EnergyManager（能量系统）— [energy_manager.py](py5_visual/energy_manager.py)

统一的全局能量池。所有系统都从中获取能量。

```
移动 → +能量（速度 × 8.0/s）
静止 → 能量转化为生长
无人 → 衰减（-1.5/s）
```

**能量乘数：** 流场 0.5–1.0 | 辉光 0.4–1.0 | 生长 0.2–1.0 | 密度 0.5–1.0

### 11. TimeSystem（时间系统）— [time_system.py](py5_visual/time_system.py)

5 分钟昼夜循环。正弦波驱动，影响整个空间的"情绪"：

| 时段 | 流场 | 辉光 | 生长 | 色温 |
|------|------|------|------|------|
| 🌅 黎明 | ×1.0 | 暗 | ×1.4 快 | 中性 |
| ☀️ 正午 | ×1.3 快 | ×0.7 亮 | ×0.6 慢 | 暖 |
| 🌆 黄昏 | ×1.0 | 暗 | ×1.4 快 | 中性 |
| 🌙 深夜 | ×0.7 慢 | ×1.3 暗 | ×0.6 慢 | 冷 |

### 12. Persistence（持久化）— [persistence.py](py5_visual/persistence.py)

每 30 秒自动保存到 `the_unseen_state.json`。保存内容：

- 能量状态
- 行为统计（总距离、速度、停留时间…）
- 所有生命体（种子 + 完整生长结构）
- 时间系统状态

下次启动自动恢复——**空间不会重置，它记住你**。

```bash
python main.py --fresh   # 清除记忆，从头开始
```

---

## 安装

```bash
# 克隆仓库
git clone <repo-url>
cd The_Unseen

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 依赖

```
mediapipe
opencv-python
python-osc
py5
numpy
```

---

## 运行

需要**同时运行两个进程**（两个终端窗口）：

```bash
# 终端 1 — 手部追踪（摄像头 + AI）
cd python_tracker
python main.py

# 终端 2 — 视觉渲染（粒子系统）
cd py5_visual
python main.py
```

**可选参数：**

```bash
# 追踪端
python main.py --no-debug          # 关闭摄像头预览窗口
python main.py --osc-port 12001    # 自定义 OSC 端口

# 渲染端
python main.py --osc-port 12001    # 匹配追踪端的 OSC 端口
```

**退出：** 追踪端按 `q`，渲染端按 `ESC` 或关闭窗口。

---

## 交互行为

| 用户行为 | 空间状态 | V2 视觉效果 | V3 数字生命 |
|----------|----------|------------|------------|
| 无人 | **IDLE** | 深蓝粒子缓慢漂浮 | 能量衰减，生命停止生长 |
| 手出现，缓慢移动 | **ACTIVE** | 蓝紫粒子向手聚拢 | 能量增加，生命可生长 |
| 快速挥手 | **EXCITED** | 金色长尾迹爆发 | 能量快速增长 |
| **手停留 >2s** | ACTIVE | — | 🌱 **种下记忆种子** |
| **继续停留** | ACTIVE | — | 🔬 种子生长为分枝结构 |
| 停下不动 | **CALM** | 空间逐渐恢复平静 | 生命继续缓慢生长 |
| 手离开 | **IDLE** | 回归无人状态 | 生命体留在原地 |
| **关闭重开** | — | — | 💾 **空间恢复，生命继续** |

**速度驱动视觉：**

- 🐢 **缓慢移动** → 空间平静，微弱尾迹，能量缓慢积累
- 🐇 **快速挥手** → 空间明显被扰动，长尾迹，强辉光，能量快速增长
- 🧘 **静止停留** → 种下种子，能量转化为生长，数字生命诞生

---

## 测试

```bash
# 测试 OSC 通信（无需渲染端）
cd python_tracker
python test_osc_receiver.py
# 然后在另一个终端运行追踪端，应看到手部数据打印
```

### 调试开关

在 [config.py](py5_visual/config.py) 中：

- `FLOW_ENABLED = False` — 关闭流场（粒子不漂移）
- `INFLUENCE_ENABLED = False` — 关闭手部影响
- `DEBUG_SHOW_STATUS = False` — 隐藏状态叠加层
- `VIGNETTE_ENABLED = False` — 关闭暗角

---

## 颜色系统

统一色板，不使用随机颜色：

| 角色 | 颜色 | 用途 |
|------|------|------|
| Background | 深蓝 `(100, 140, 220)` | Layer 1 — 空间基底 |
| Interaction | 蓝紫 `(140, 120, 230)` | Layer 2 — 主要交互 |
| Highlight | 暖金 `(255, 200, 100)` | Layer 3 — 高亮尾迹 |
| Left Hand | 品红 `(255, 150, 255)` | 左手光环 |
| Right Hand | 暖金 `(255, 200, 100)` | 右手光环 |
| Core | 纯白 `(255, 255, 255)` | 粒子中心灼热点 |
| **V3 Life** | 生命蓝 `(80, 140, 255)` | 生命体核心 |
| **V3 Memory** | 记忆紫 `(160, 120, 240)` | 种子 + 连接线 |
| **V3 Energy** | 能量金 `(255, 210, 80)` | 能量指示 |
| **V3 Growth** | 生长白 `(240, 240, 255)` | 新生枝端 |

颜色根据**生命周期阶段**、**当前速度**、**与手的距离**、**昼夜时间**动态变化。

---

## 性能

| 指标 | V3 数值 |
|------|---------|
| 总粒子数 | 1280（800+400+80） |
| 每帧 draw calls | ~3,100（优化后） |
| DLA walkers/帧 | 25 |
| 最大生命体数 | 8 |
| 目标帧率 | 60 FPS |
| 自动保存间隔 | 30 秒 |
| 昼夜周期 | 5 分钟 |

---

## 路线图

### V3 — Digital Organism（数字生命）← ✅ 已完成

- ✅ DLA 扩散限制聚合生长
- ✅ 记忆种子系统
- ✅ 统一能量系统
- ✅ 行为统计分析
- ✅ 昼夜循环
- ✅ JSON 持久化
- ✅ 数字生态系统规则

### V4 — AI Narrative（AI 叙事）← 远期规划

- 行为分析：识别手势语义
- AI 驱动的空间叙事生成
- 声音交互：麦克风输入驱动空间脉动
- 多设备联动
- 多人交互

---

## 许可

仅供学习与艺术创作使用。

---

## 致谢

- [MediaPipe](https://developers.google.com/mediapipe) — Google 开源感知框架
- [py5](https://py5coding.org/) — Python 创意编程库
- [Processing](https://processing.org/) — 生成艺术先驱平台
