# 狼人杀（Werewolf）游戏 - 项目说明

简介
本目录用于开发一款基于浏览器/REST 的狼人杀游戏服务器与简单前端。

目标
- 使用 Python + FastAPI 实现后端游戏状态机与 API
- 提供简易前端用于玩家交互（可选：React / Svelte）
- 包含单元测试与文档

项目结构（初始）
games/werewolf/
├─ README.md
├─ backend/
├─ ├─ app.py            # FastAPI 入口
├─ ├─ game_engine.py    # 核心状态机与规则
├─ ├─ models.py         # 数据模型
├─ ├─ requirements.txt
├─ frontend/            # 可选：前端代码
└─ tests/               # 单元测试

快速开始（开发）
1. 创建并激活虚拟环境：python -m venv .venv && .venv\\Scripts\\Activate.ps1
2. 安装依赖：pip install -r games/werewolf/backend/requirements.txt
3. 启动开发服务器：
   cd games/werewolf/backend && uvicorn app:app --reload --host 127.0.0.1 --port 8000

下一步
- 设计游戏规则与数据模型
- 初始化 backend/app.py 与核心状态机实现

维护者
- 初始化：自动化脚本
