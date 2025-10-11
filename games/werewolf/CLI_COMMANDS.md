# 一键运行命令（可复制粘贴）

下面是 Windows (PowerShell) 与 Unix (bash) 的可直接复制运行命令。

## Windows PowerShell (复制并粘贴到 PowerShell)

```powershell
# 后端：创建并激活虚拟环境、安装依赖、创建示例 api_keys.json、启动服务器
cd e:\CODE\Astra-Synergy\AI-CHAT\games\werewolf\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 在项目根创建 api_keys.json（替换 YOUR_OPENAI_KEY）
Set-Content -Path ..\..\api_keys.json -Value '{ "openai": { "api_key": "YOUR_OPENAI_KEY", "model_url":"https://api.openai.com/v1/chat/completions" } }' -Encoding utf8
# 启动后端
uvicorn games.werewolf.backend.app:app --reload --host 127.0.0.1 --port 8000
```

## Unix / WSL / macOS (bash)

```bash
# 后端：创建并激活虚拟环境、安装依赖、创建示例 api_keys.json、启动服务器
cd e:/CODE/Astra-Synergy/AI-CHAT/games/werewolf/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 在项目根创建 api_keys.json（替换 YOUR_OPENAI_KEY）
cat > ../../api_keys.json <<'JSON'
{
  "openai": {
    "api_key": "YOUR_OPENAI_KEY",
    "model_url": "https://api.openai.com/v1/chat/completions"
  }
}
JSON
# 启动后端
uvicorn games.werewolf.backend.app:app --reload --host 127.0.0.1 --port 8000
```

## 前端 (Vite)

```bash
cd e:/CODE/Astra-Synergy/AI-CHAT/games/werewolf/frontend
npm install
# 可选设置 API 地址
echo "VITE_API_BASE=http://127.0.0.1:8000" > .env
npm run dev
```

## 调试命令示例

```bash
# 模拟 6 个 AI 对战（REST）
curl -X POST "http://127.0.0.1:8000/simulate_ai_game?num_players=6"

# 使用 wscat 测试 WebSocket（需要安装 wscat）
npx wscat -c "ws://127.0.0.1:8000/ws/{game_id}"
```

## 快速检查

- 后端地址: http://127.0.0.1:8000
- 前端地址 (Vite): 默认 http://localhost:5173

参考文档：[`games/werewolf/RUN_INSTRUCTIONS.md`](games/werewolf/RUN_INSTRUCTIONS.md:1)