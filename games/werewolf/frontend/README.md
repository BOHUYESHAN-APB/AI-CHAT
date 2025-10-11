# Werewolf 前端（React）说明

目标
- 使用 Vite + React 快速搭建前端，用于展示房间列表、加入房间、查看玩家与投票、以及触发 AI 对战模拟。
- 优先实现最小可用界面以便进行模型对战与能力评测。

建议技术栈
- React 18 + Vite
- axios 或 fetch 用于调用后端 API
- 可选：Tailwind CSS / 基本 CSS

项目结构（建议）
games/werewolf/frontend/
├─ package.json
├─ index.html
├─ src/
│  ├─ main.jsx
│  ├─ App.jsx
│  ├─ pages/
│  │  ├─ Lobby.jsx
│  │  ├─ GameView.jsx
│  └─ components/
│     ├─ PlayerList.jsx
│     └─ VoteControls.jsx

快速开始（开发）
1. 进入前端目录并初始化
   cd games/werewolf/frontend
   npm create vite@latest . -- --template react
2. 安装依赖
   npm install
3. 启动开发服务器
   npm run dev

与后端联动
- 默认后端地址（开发）: http://127.0.0.1:8000
- 在前端中通过环境变量配置后端 URL（例如 Vite 使用 `import.meta.env.VITE_API_BASE`）
- 示例请求：
  - 创建房间: POST /games
  - 加入房间: POST /games/{game_id}/join
  - 启动游戏: POST /games/{game_id}/start
  - 触发 AI 轮次: POST /games/{game_id}/ai_turn
  - 模拟完整 AI 对战: POST /simulate_ai_game

API Key 使用说明
- 后端从项目根目录 `api_keys.json` 或 `api_keys.example.json` 读取密钥；前端不应直接包含密钥。
- 若需要在前端触发需授权的后端操作，请在后端实现安全代理或使用服务器端保存的 key。

下一步建议
- 我可以现在生成 Vite React 项目初始文件（package.json + src/App.jsx + src/main.jsx）并加入调用后端的最小 UI。请确认是否继续创建这些文件。