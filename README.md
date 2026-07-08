# The Unseen (不可见)

> "人无法直接看到自己的存在，但世界会记录人的影响。"
> "People cannot directly see their own existence, but the world records their impact."

## 项目简介

一个基于人工智能感知、计算机视觉和生成艺术的交互装置作品。

通过摄像头检测人体手部位置，在由粒子组成的数字空间中产生不可见的引力场——手划过空气，留下光的痕迹。

## 技术栈

- **Python 3.12**
- **MediaPipe Hands** — 手部关键点检测
- **OpenCV** — 摄像头捕获
- **OSC (Open Sound Control)** — 进程间实时通信
- **py5** — Python 创意编程 / 生成艺术渲染

## 项目结构

```
The_Unseen/
├── python_tracker/       # 手部追踪 + OSC 发送端
│   ├── main.py
│   ├── hand_tracking.py
│   ├── osc_sender.py
│   ├── test_osc_receiver.py
│   └── requirements.txt
├── py5_visual/           # py5 粒子系统 + OSC 接收端
│   ├── main.py
│   ├── particle.py
│   ├── flow_field.py
│   └── requirements.txt
├── requirements.txt      # 统一依赖文件
├── .gitignore
└── README.md
```

## 安装

```bash
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

## 运行方式

需要同时运行两个进程（两个终端窗口）：

```bash
# 终端 1 — 启动手部追踪
cd python_tracker
python main.py

# 终端 2 — 启动视觉渲染
cd py5_visual
python main.py
```

按 `q` 退出追踪端，按 `ESC` 或关闭窗口退出视觉端。

## 交互说明

- **无手时**：粒子缓慢漂浮，模拟"无人的不可见空间"
- **手静止**：手附近产生引力场，粒子向手靠近
- **手快速移动**：产生光粒子尾迹，形成"空气被划开"的效果
