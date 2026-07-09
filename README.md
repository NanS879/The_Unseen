# The Unseen · 不可见

> "人无法直接看到自己的存在，但世界始终记录着人的影响。"
> "People cannot directly see their own existence, but the world always records their impact."

## 项目简介

**The Unseen** 是一个探索人与数字空间关系的生成式交互艺术装置。

摄像头感知你的手 — 每一种手势都是一种空间语言。粒子跟随、涟漪扩散、种子生根、生命生长。你不是在操作软件，而是在与一个会呼吸、会记忆、会生长的数字生态系统对话。

---

## 快速开始

```bash
git clone <repo-url>
cd The_Unseen
pip install -r requirements.txt

# 一行启动
python -m the_unseen

# 可选参数
python -m the_unseen --fresh     # 全新开始（清除记忆）
python -m the_unseen --release   # Release 模式（关闭调试输出）
```

**快捷键：**

| 按键  | 功能                                               |
| ----- | -------------------------------------------------- |
| `D` | 调试面板（FPS 火花图、能量、手势、能力状态、情绪） |
| `F` | FPS 角标                                           |
| `R` | Debug / Release 切换                               |
| `Q` | 退出 + Presence Report                             |

---

## 项目结构

```
The_Unseen/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── the_unseen/                          # 主包 (29 模块, 7 子包)
│   ├── __init__.py
│   ├── __main__.py                      # python -m the_unseen 入口
│   ├── main.py                          # py5 sketch 主循环
│   ├── config.py                        # 集中参数管理
│   │
│   ├── perception/                      # 感知层
│   │   ├── camera_tracker.py            # 内联 MediaPipe + OpenCV
│   │   └── hand_state.py                # 手部 EMA 平滑
│   │
│   ├── simulation/                      # 模拟层
│   │   ├── flow_field.py                # Perlin Noise 2D 流场
│   │   ├── influence_field.py           # 手部影响场
│   │   ├── particle.py                  # 粒子 (5 阶段生命周期)
│   │   ├── particle_manager.py          # 三层粒子编排
│   │   └── space_state.py               # 空间状态机
│   │
│   ├── life/                            # 生命层
│   │   ├── memory_seed.py               # 记忆种子
│   │   ├── growth_algorithm.py          # DLA 生长引擎
│   │   ├── organism.py                  # 生命体 + 生态系统
│   │   ├── energy_manager.py            # 统一能量系统
│   │   ├── behavior_analyzer.py         # 行为统计
│   │   ├── time_system.py               # 昼夜循环
│   │   └── persistence.py               # JSON 持久化
│   │
│   ├── interaction/                     # 交互层
│   │   ├── gesture_manager.py           # 手势识别 + 状态机
│   │   ├── ability_base.py              # BaseAbility + SpaceMood
│   │   ├── ability_manager.py           # 6 种空间能力
│   │   ├── interaction_rules.py         # 非能力手势 → 效果
│   │   ├── ripple.py                    # 涟漪系统
│   │   └── fragment.py                  # 记忆碎片
│   │
│   ├── feedback/                        # 反馈层
│   │   ├── feedback_composer.py         # Camera + Time + Post + Lighting
│   │   ├── procedural_bg.py             # 程序化背景
│   │   ├── visual_system.py             # Depth + Variety + Camera + Lighting
│   │   └── audio_hook.py               # 音频接口 (预留)
│   │
│   ├── ui/                              # 界面层
│   │   ├── render_utils.py              # 手部光环 + 引导提示
│   │   └── debug_overlay.py             # 性能面板 + FPS 火花图
│   │
│   └── utils/                           # 工具层
│       ├── logger.py                    # 结构化日志
│       └── easing.py                    # 缓动函数
│
├── tests/                               # 测试
│   └── test_imports.py
│
└── docs/                                # 文档 (预留)
```

---

## 技术栈

| 层级 | 技术                    | 用途               |
| ---- | ----------------------- | ------------------ |
| 感知 | MediaPipe Hands         | 双手 21 点关键点   |
| 采集 | OpenCV                  | 摄像头捕获 (内联)  |
| 渲染 | py5 (Processing Python) | 粒子系统 / 流场    |
| 数学 | Perlin Noise 3D, DLA    | 流场向量、有机生长 |
| 存储 | JSON                    | 持久化状态         |

---

## 系统架构

```
Camera → MediaPipe → HandState (perception/)
                         │
        ┌────────────────┤
        ▼                ▼
 GestureManager    InfluenceField
 (interaction/)    (simulation/)
        │                │
        ▼                ▼
SpaceAbilityManager   FlowField
 (interaction/)      (simulation/)
        │                │
        ├────────────────┤
        ▼                ▼
  FeedbackComposer   ParticleManager
   (feedback/)       (simulation/)
        │                │
        ├────────────────┤
        ▼                ▼
 Ripple / Fragment  OrganismManager
 (interaction/)      (life/)
        │                │
        └────────┬───────┘
                 ▼
            Render (py5)
                 │
                 ▼
         Persistence (JSON)
```

---

## 交互

| 行为          | 能力         | 充能 | 情绪      | 反馈                         |
| ------------- | ------------ | ---- | --------- | ---------------------------- |
| 🖐️ 张开手掌 | Connect 连接 | 0.5s | Calm      | 蓝色柔光 + 粒子聚拢          |
| ✊ 握拳       | Gather 聚集  | 1.0s | Focused   | 金色能量环 + 流场压缩        |
| 🤏 捏合       | Create 创造  | 1.5s | Hope      | 冻结帧 + 金色闪光 + 种子诞生 |
| ☝️ 食指     | Guide 引导   | 0.3s | Curiosity | 轨迹光点 + 流场跟随          |
| 🙌 展开       | Expand 扩张  | 0.8s | Freedom   | 镜头拉远 + 曝光提升 + 呼吸   |
| 🙌 靠近       | Merge 融合   | 2.0s | Harmony   | 慢动作 + 紫色光桥 + 生命连接 |
| 停留          | Seed 种子    | 1.5s | —        | 紫色脉冲 → DLA 生长         |
| 挥手          | Ripple 涟漪  | —   | —        | 扩展环 + 粒子推力 + 镜头抖动 |

---

## 版本历史

| 版本 | 主题                                                    | 状态 |
| ---- | ------------------------------------------------------- | ---- |
| V1   | 基础交互 — 粒子跟随手                                  | ✅   |
| V2   | 响应式空间 — 流场 + 影响场 + 状态机                    | ✅   |
| V3   | 数字生命 — DLA 生长 + 能量 + 持久化                    | ✅   |
| V4   | 空间手势语言 — 单进程 + 6 种能力 + 涟漪                | ✅   |
| V5   | 沉浸式反馈 — Camera/Time/Post/Lighting 系统            | ✅   |
| V6   | 视觉身份 — 程序化背景 + 深度 + 粒子多样性 + 状态主题色 | ✅   |

---

## 许可

仅供学习与艺术创作使用。

## 致谢

[MediaPipe](https://developers.google.com/mediapipe) · [py5](https://py5coding.org/) · [Processing](https://processing.org/)
