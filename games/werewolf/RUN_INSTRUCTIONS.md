# 本地运行说明

先决条件
- Python 3.10+ 已安装
- Node.js + npm 已安装
- 在项目根目录填写 API Key：参考 [`api_keys.example.json`](api_keys.example.json:1)

后端（打开第一个 PowerShell 终端）
cd e:\CODE\Astra-Synergy\AI-CHAT
cd games/werewolf/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 可选：在根目录创建 api_keys.json，格式同 api_keys.example.json
# 示例（PowerShell）:
echo '{ "openai": { "api_key": "YOUR_OPENAI_KEY", "model_url":"https://api.openai.com/v1/chat/completions" } }' > ..\..\api_keys.json
# 启动后端
uvicorn games.werewolf.backend.app:app --reload --host 127.0.0.1 --port 8000

前端（打开第二个终端）
cd e:\CODE\Astra-Synergy\AI-CHAT\games\werewolf\frontend
npm install
npm run dev
# Vite 默认在 http://localhost:5173 打开前端页面

测试与调试
- 使用前端界面创建房间并添加 AI / 人类玩家
- 触发 AI 模拟：POST http://127.0.0.1:8000/simulate_ai_game?num_players=6
- WebSocket 连接：ws://127.0.0.1:8000/ws/{game_id}

关键文件
- 后端入口：[`games/werewolf/backend/app.py`](games/werewolf/backend/app.py:1)
- 前端入口：[`games/werewolf/frontend/src/App.jsx`](games/werewolf/frontend/src/App.jsx:1)

常见问题
- 若端口被占用，请更换端口后重启
- API Key 未生效请检查 `api_keys.json` 或环境变量
