# 狼人杀（AI 评测）项目

简介
本项目用于让 AI 扮演所有玩家进行狼人杀对局，支持多模型映射与评测采样。

快速开始
先安装后端依赖：
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt

配置 API Key（三种可选方式）：
- 环境变量：OPENAI_API_KEY
- 根目录文件：在项目根放置名为 `api_key` 的纯文本文件，包含密钥
- JSON 文件：在根目录放 `api_keys.json`，键名如 OPENAI_API_KEY

多模型配置
示例配置文件：[`games/werewolf/backend/ai_models.example.json`](games/werewolf/backend/ai_models.example.json:1)
若要自定义，复制为 [`games/werewolf/backend/ai_models.json`](games/werewolf/backend/ai_models.json:1) 并修改 `default_model` 与 `player_models`。

运行后端
python games/werewolf/backend/app.py
后端默认监听 8080，提供 /rooms、/rooms/<id>/join、/start、/step 等 API，用于创建/加入/开始/推进回合。

前端（开发）
进入前端目录并安装：
cd games/werewolf/frontend
npm install
npm run dev
前端使用 Vite，package.json 已设置 proxy 到 http://localhost:8080，可在浏览器打开提示的地址访问简易 UI。

运行测试
pytest

重要文件说明
- [`games/werewolf/backend/app.py`](games/werewolf/backend/app.py:1) — 后端主程序（房间管理、游戏状态机）
- [`games/werewolf/backend/ai_client.py`](games/werewolf/backend/ai_client.py:1) — AI 调用、提示构建与策略后备
- [`games/werewolf/backend/ai_models.example.json`](games/werewolf/backend/ai_models.example.json:1) — 多模型示例映射
- [`games/werewolf/frontend/src/App.jsx`](games/werewolf/frontend/src/App.jsx:1) — 简易前端界面

后续建议
- 增加决策/响应日志（记录每次调用的模型、耗时与原始响应）以便评测分析
- 增加更高级的 AI 策略与多轮对话模拟
- 导出评测结果（CSV/JSON）便于统计与比较

许可
MIT