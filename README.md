# The Unseen · 不可见

> "人无法直接看到自己的存在，但世界始终记录着人的影响。"
> "People cannot directly see their own existence, but the world always records their impact."

## 项目简介

**The Unseen** 是一个探索人与数字空间关系的生成式交互艺术装置。

摄像头感知你的手——**每一种手势都是一种空间语言**。张开手掌建立连接，握拳聚集能量，捏合创造生命。你不是在操作软件，而是在与一个会呼吸、会记忆、会生长的数字生态系统对话。

---

## 版本

### V4 — Spatial Gesture Language ← 当前版本

- 🔌 **单进程架构** — `python main.py` 一行启动
- 🖐️ **空间手势语言** — 6 种空间能力：Connect / Gather / Create / Guide / Expand / Merge
- 🎭 **空间情绪系统** — Calm / Focused / Hope / Curiosity / Freedom / Harmony → 调制流场/辉光/色温
- 🌊 **涟漪系统** — 统一交互反馈语言
- ✨ **记忆碎片** — 可收集光点，驱动探索
- 🌱 **数字生命** — DLA 有机生长 + 生态系统
- 💾 **持久化** — JSON 自动保存，重启恢复

### V3 — Digital Organism

记忆种子 · DLA 生长 · 能量系统 · 数字森林 · 昼夜循环 · 持久化

### V2 — Responsive Space

Perlin Noise 流场 · 手部影响场 · 三层粒子 · 空间状态机

### V1 — Basic Interaction

摄像头 → MediaPipe → 粒子跟随手

---

## 快速开始

```bash
pip install -r requirements.txt
cd py5_visual
python main.py
```

```bash
python main.py --fresh      # 全新开始
python main.py --release    # Release 模式
python main.py --no-camera  # 无摄像头演示
```

| 按键 | 功能 |
|------|------|
| `D` | 调试面板（FPS 火花图、能量、手势、能力状态、情绪） |
| `F` | FPS 角标 |
| `R` | Debug / Release 切换 |
| `Q` | 退出 + Presence Report |

---

## 系统架构

```
Camera → MediaPipe (21 landmarks) → HandState (EMA)
                                        │
                    ┌───────────────────┤
                    ▼                   ▼
             GestureManager      InfluenceField
               (7 gestures)        (引力+尾流)
                    │                   │
                    ▼                   ▼
          SpaceAbilityManager     FlowField
            (6 abilities)      (Perlin Noise)
                    │                   │
                    ├───────────────────┤
                    ▼                   ▼
             SpaceMood           ParticleManager
           (modulates flow,       (3 layers)
            glow, color)              │
                    │                 ▼
                    └──────→  RippleManager
                              FragmentManager
                              OrganismManager
                              EnergyManager
                                    │
                                    ▼
                               Render (py5)
                                    │
                                    ▼
                            Persistence (JSON)
```

---

## 空间能力系统

核心理念：**Gesture → Intent → Space Ability → Space Mood → Response**

手势不是按钮。每种手势对应一种"空间能力"——持续保持手势来充能，充能完成后能力激活。
中途松开会取消，保证每个动作都有意图。

### 能力状态机

```
IDLE → PREPARING → CHARGING → ACTIVATED → COOLDOWN → IDLE
         ↑                          ↑
    手势开始                    充能完成
    (0.3~2.0s)               (应用效果+情绪)
```

### 六种空间能力

| 手势 | 能力 | 充能 | 冷却 | 情绪 | 视觉反馈 |
|------|------|------|------|------|----------|
| 🖐️ Open Palm | **Connect** 连接 | 0.5s | 3s | Calm | 蓝色柔光扩散，粒子缓慢聚拢 |
| ✊ Fist | **Gather** 聚集 | 1.0s | 3s | Focused | 金色能量环收缩，流场加速 |
| 🤏 Pinch | **Create** 创造 | 1.5s | 5s | Hope | 金色种子形成动画，紫色涟漪 |
| ☝️ Point | **Guide** 引导 | 0.3s | 1s | Curiosity | 指尖轨迹光点，流场跟随 |
| 🙌 Expand | **Expand** 扩张 | 0.8s | 4s | Freedom | 青色呼吸环扩展，粒子分散 |
| 🙌 Compress | **Merge** 融合 | 2.0s | 6s | Harmony | 紫色连接桥，有机体连接 |

### Connect（连接）— Open Palm

与空间建立平静连接。粒子主动靠近，流场减速，辉光柔和。
**情绪：Calm** → 流场 ×0.6 / 辉光 ×0.7 / 色温偏蓝

### Gather（聚集）— Fist

聚焦空间能量。流场向拳头收缩，能量快速增长，附近种子获得生长加速。
**情绪：Focused** → 流场 ×1.4 / 辉光 ×1.3 / 色温偏暖

### Create（创造）— Pinch

在捏合位置创造新的数字生命。金色种子出现，随后自动生长为 DLA 有机体。
**情绪：Hope** → 流场 ×0.9 / 辉光 ×1.2 / 色温暖金
冷却最长（5s），每次创造都有仪式感。

### Guide（引导）— Point

指尖引导空间流向。流场跟随食指方向，粒子沿轨迹运动，有机体缓慢靠近。
**情绪：Curiosity** → 流场 ×1.2 / 辉光 ×0.9
充能最快（0.3s），适合持续使用。

### Expand（扩张）— 双手展开

空间深呼吸。流场大幅减速，粒子向外扩散，大范围涟漪。
**情绪：Freedom** → 流场 ×0.5 / 辉光 ×0.6 / 色温偏青

### Merge（融合）— 双手靠近

两个有机体通过光桥连接。需要持续保持 2 秒——最长充能，最具仪式感。
**情绪：Harmony** → 流场 ×0.8 / 辉光 ×1.1 / 色温偏紫

---

## 手势识别

基于 MediaPipe 21 点手部关键点。每个手势通过指关节几何关系实时判定。

### 单手手势

| 手势 | 检测方法 | 充能 | 冷却 |
|------|----------|------|------|
| 🖐️ Open Palm | 4 指伸展 (tip-to-MCP > 50%) | 0.5s | 3s |
| ✊ Fist | 4 指卷曲 (tip-to-wrist < 70%) | 1.0s | 3s |
| 🤏 Pinch | 拇指尖↔食指尖 < 6% | 1.5s | 5s |
| ☝️ Point | 食指伸展 + 其余 3 指卷曲 | 0.3s | 1s |
| ✌️ Victory | 食指+中指伸展，其余卷曲 | — | 2s |
| 💨 Swipe | 手速 > 0.06 | — | 2s |
| 🧘 Hold | 手速 < 0.015 持续 | — | — |

### 双手交互

| 交互 | 检测条件 | 效果 |
|------|----------|------|
| Expand | 双手距离增大 > 30% | 流场发散 |
| Compress | 双手距离缩小 > 30% | 能量爆发 +8 |
| Cross | 双手 X 轴位置互换 | 紫色涟漪 |
| Sync | 双手同向移动 | 螺旋流场 |

---

## 数字生命系统

### 记忆种子

手在同一区域停留约 1.5 秒，自动生成一颗记忆种子。种子以紫色脉冲光点显示，继续停留积累能量。能量达阈值（40）后触发 DLA 生长。

| 参数 | 值 |
|------|-----|
| 停留半径 | 80 px |
| 停留时间 | 1.5 s |
| 速度阈值 | < 0.10 |
| 生长阈值 | 40 能量 |

### DLA 有机生长

扩散限制聚合算法（Diffusion Limited Aggregation）——模拟闪电、珊瑚、树根的自然分枝形态。每帧释放 40 个 walker 随机游走，碰到已有结构就"粘住"。每次生长结果都不同。

### 数字生态规则

- 距离 < 40px → 竞争，双方生长减速
- 距离 40–200px → 独立 + 紫色连接线
- 距离 > 200px → 完全独立
- 最多 8 个有机体共存

### 能量系统

```
手移动  → +能量（速度 × 增益率）
手停留  → 能量转化为生长
无人    → 能量缓慢衰减 (-1.5/s)
收集碎片 → 立即 +5~20 能量
Gather  → +5 能量
Connect → +3 能量
Expand  → +8 能量
```

### 昼夜循环

5 分钟完整昼夜周期。正弦波驱动：

| 时段 | 流场 | 辉光 | 生长 | 色温 |
|------|------|------|------|------|
| 🌅 黎明 | ×1.0 | 暗 | ×1.4 快 | 中性 |
| ☀️ 正午 | ×1.3 | ×0.7 亮 | ×0.6 | 暖 |
| 🌆 黄昏 | ×1.0 | 暗 | ×1.4 快 | 中性 |
| 🌙 深夜 | ×0.7 | ×1.3 | ×0.6 | 冷 |

### 持久化

每 30 秒自动保存到 `the_unseen_state.json`：
能量 · 行为统计 · 所有有机体（种子 + 完整 DLA 点云） · 时间系统

重启自动恢复——**空间不会重置，它记住你。**

---

## 项目结构

```
py5_visual/                          # 26 个模块，py5 flat import
│
├── main.py                          # 入口 — 单循环：摄像头→手势→能力→模拟→渲染
├── config.py                        # 所有参数（~250 行）
│
├── 感知层
│   ├── camera_tracker.py            # 内联 MediaPipe + OpenCV + 21 点 landmarks
│   └── hand_state.py                # 手部位置 EMA 平滑
│
├── 手势 + 能力层
│   ├── gesture_manager.py           # 手势识别 + 状态机 + 双手检测
│   ├── ability_base.py              # BaseAbility + SpaceMood + AbilityState
│   ├── ability_manager.py           # 6 种能力 + SpaceAbilityManager
│   └── interaction_rules.py         # 非能力手势 → 涟漪效果
│
├── 模拟层
│   ├── flow_field.py                # Perlin Noise 2D 流场
│   ├── influence_field.py           # 手部影响场（引力 + 尾流）
│   ├── particle.py                  # 粒子（5 阶段生命周期 + smoothstep 缓动）
│   ├── particle_manager.py          # 三层粒子编排（800/400/80）
│   └── space_state.py               # 空间状态机（IDLE/ACTIVE/EXCITED/CALM）
│
├── 生命层
│   ├── memory_seed.py               # 记忆种子（位置/能量/脉冲动画）
│   ├── growth_algorithm.py          # DLA 引擎（空间哈希 O(1) 碰撞）
│   ├── organism.py                  # 生命体 + 生态管理器
│   ├── energy_manager.py            # 能量池 + 乘数调制
│   ├── behavior_analyzer.py         # 行为统计（距离/速度/停留/交互次数）
│   ├── time_system.py               # 昼夜循环（正弦波 + 相位调制）
│   └── persistence.py               # JSON 保存/恢复
│
├── 交互层
│   ├── ripple.py                    # 涟漪（扩展环 + 粒子推力）
│   └── fragment.py                  # 记忆碎片（飞向手 + 收集奖励）
│
├── 渲染 + 调试
│   ├── render_utils.py              # 手部柔光光环 + 启动引导提示
│   └── debug_overlay.py             # 玻璃态 HUD + FPS 火花图
│
└── 基础设施
    ├── logger.py                    # 结构化日志（Debug/Release）
    └── easing.py                    # 缓动函数（smoothstep / ease-in-out）
```

---

## 交互行为

| 行为 | 即时反馈 | 系统影响 |
|------|----------|----------|
| 手进入 | 粒子聚拢，ACTIVE 状态 | 能量开始积累 |
| 缓慢移动 | 粒子跟随，柔光光环，涟漪 | 能量缓慢增长 |
| 快速挥手 | 涟漪爆发，EXCITED 状态 | 能量快速增长 |
| 🖐️ **张开手掌 0.5s** | 蓝色柔光扩散 | Connect 激活 → Calm |
| ✊ **握拳 1.0s** | 金色能量环收缩 | Gather 激活 → Focused |
| 🤏 **捏合 1.5s** | 金色种子形成 + 紫色涟漪 | Create → 新生命诞生 |
| ☝️ **食指指向 0.3s** | 指尖光点轨迹 | Guide → 流场跟随 |
| 🙌 **双手展开 0.8s** | 青色呼吸环扩展 | Expand → Freedom |
| 🙌 **双手靠近 2.0s** | 紫色连接桥 | Merge → Harmony |
| ✌️ V 手势 | 白色大涟漪 | 模式轮换 |
| 手停留 | 紫色脉冲种子 | 种子积累能量 |
| 继续停留 | DLA 白色分枝生长 | 有机体诞生 |
| 靠近碎片 | 碎片加速飞向手 | 收集能量 |
| 手离开 | IDLE，能量衰减 | 生命体留在原地 |
| 按 Q 退出 | Presence Report | JSON 全量保存 |
| 重新启动 | 空间恢复 | 生命继续生长 |

---

## 颜色系统

| 角色 | 色值 | 用途 |
|------|------|------|
| Background | `(100, 140, 220)` | 背景粒子 |
| Interaction | `(140, 120, 230)` | 交互粒子 |
| Highlight | `(255, 200, 100)` | 高亮粒子 |
| Hand Left | `(255, 150, 255)` | 左手光环 |
| Hand Right | `(255, 200, 100)` | 右手光环 |
| Life | `(80, 140, 255)` | 有机体核心（旧枝） |
| Memory | `(160, 120, 240)` | 种子 + 连接线 |
| Energy | `(255, 210, 80)` | 碎片 + 能量条 + 充能环 |
| Growth | `(240, 240, 255)` | 新生枝端（白色） |

---

## 性能

| 指标 | 值 |
|------|-----|
| 总粒子 | 1280（BG 800 / INT 400 / HL 80） |
| 帧率 | 60 FPS |
| 流场 | 52×29 cells，每 3 帧更新 |
| DLA | 40 walkers/帧，O(1) 碰撞 |
| MediaPipe | 每 2 帧处理 |
| 最大有机体 | 8 |
| 最大涟漪 | 25 |
| 最大碎片 | 15 |
| 自动保存 | 每 30 秒 |

---

## 调试

| 按键 | 功能 |
|------|------|
| `D` | 完整调试面板 |
| `F` | FPS 角标 |
| `R` | Debug/Release 切换 |
| `Q` | 退出 + Presence Report |

**调试面板内容：** FPS + 帧耗时 + FPS 火花图 · 空间状态 · 时间段 · 粒子数（分 BG/INT/HL） · 有机体/种子/生长点数 · 能量条 · 手部位置/速度 · 当前手势 + 置信度 · 活跃能力 + 状态 + 情绪

---

## 依赖

```
mediapipe
opencv-python
py5
numpy
```

---

## 路线图

| 版本 | 主题 | 状态 |
|------|------|------|
| V1 | 基础交互 | ✅ |
| V2 | 响应式空间 | ✅ |
| V3 | 数字生命 | ✅ |
| V4 | 空间手势语言 | ✅ |
| V5 | 声音 / AI / 多人 | 🔮 |

---

## 许可

仅供学习与艺术创作使用。

## 致谢

[MediaPipe](https://developers.google.com/mediapipe) · [py5](https://py5coding.org/) · [Processing](https://processing.org/)
