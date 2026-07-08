# The Unseen · 不可见

> "人无法直接看到自己的存在，但世界始终记录着人的影响。"
> "People cannot directly see their own existence, but the world always records their impact."

## 项目简介

**The Unseen** 是一个探索人与数字空间之间隐性关系的生成式交互艺术作品。

通过摄像头与 AI 感知，你的手在由数千个粒子组成的数字生态系统中产生不可见的力场——划过空气，留下光的痕迹。你不是在控制粒子，而是在改变整个空间。

---

## 版本

### V2 — Responsive Space（响应式空间） ← 当前版本

整个空间成为一个具有生命感的数字生态系统：

- 🌬️ **呼吸感** — Perlin Noise 流场持续缓慢演化
- 🌊 **流动感** — 3000 粒子三层叠加，运动尾迹
- 🎚️ **层次感** — Background / Interaction / Highlight 三层独立行为
- 🧬 **生命周期** — 每个粒子经历 birth → growth → peak → decay → death → respawn
- 🧠 **空间状态机** — IDLE / ACTIVE / EXCITED / CALM 四态自动切换
- 🎨 **统一色板** — 蓝 / 紫 / 金，颜色随距离、速度、生命阶段动态变化

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
│   ├── main.py                  # py5 主入口（169 行，纯编排）
│   ├── config.py                # 集中参数管理（所有可调参数）
│   ├── flow_field.py            # Perlin Noise 2D 流场
│   ├── influence_field.py       # 手部影响场（引力 + 尾流）
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

| 用户行为 | 空间状态 | 视觉效果 |
|----------|----------|----------|
| 无人 | **IDLE** | 深蓝粒子缓慢漂浮，无尾迹，空间安静呼吸 |
| 手出现，缓慢移动 | **ACTIVE** | 蓝紫粒子向手聚拢，中等尾迹，光环出现 |
| 快速挥手 | **EXCITED** | 金色长尾迹爆发，更多光环，粒子剧烈扰动 |
| 停下不动 | **CALM** | 空间逐渐恢复平静，影响力减弱 |
| 手离开 | **IDLE** | 回归无人状态，粒子继续缓慢漂浮 |

**速度驱动视觉：**

- 🐢 **缓慢移动** → 空间平静，微弱尾迹
- 🐇 **快速挥手** → 空间明显被扰动，长尾迹，强辉光

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

颜色根据**生命周期阶段**、**当前速度**、**与手的距离**动态变化。

---

## 性能

| 指标 | V2 数值 |
|------|---------|
| 总粒子数 | 2950（2000+800+150） |
| 目标帧率 | 60 FPS |
| 流场网格 | 52×29 cells |
| OSC 延迟 | < 1ms (本地 UDP) |
| 双手追踪延迟 | ~15ms (MediaPipe) |

若性能不足，可在 [config.py](py5_visual/config.py) 中降低 `PARTICLE_*_COUNT` 或增大 `FLOW_CELL_SIZE`。

---

## 路线图

### V3 — Digital Life（数字生命）← 规划中

- 粒子集群行为（flocking: separation / alignment / cohesion）
- 生长系统：粒子可分裂、融合
- 声音交互：麦克风输入驱动空间脉动
- 空间记忆：粒子记住用户常去区域

### V4 — AI Narrative（AI 叙事）← 远期规划

- 行为分析：识别手势语义
- AI 驱动的空间叙事生成
- 多设备联动

---

## 许可

仅供学习与艺术创作使用。

---

## 致谢

- [MediaPipe](https://developers.google.com/mediapipe) — Google 开源感知框架
- [py5](https://py5coding.org/) — Python 创意编程库
- [Processing](https://processing.org/) — 生成艺术先驱平台
