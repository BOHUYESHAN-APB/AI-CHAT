# 前端调试与日志采集（可复制命令）

简要：按下面命令/步骤操作，复制结果粘贴回我这里，我会分析。

1) 浏览器控制台（DevTools）
- 打开：F12 或 Ctrl+Shift+I
- Console：右键 → Clear，重现问题（刷新页面）
- 全选并复制控制台内容（Ctrl+A → Ctrl+C），粘贴到此处

2) Network（网络）与 HAR 导出
- 打开 Network，勾选 "Preserve log"
- 过滤器选 XHR / WS，重现问题
- 右键任一请求 → Save all as HAR with content（或 Export HAR）
- 若不能导出，右键需要的请求 → Copy → Copy response / Copy as cURL，粘贴到这里
- WebSocket：在 Network 找到 ws 连接，点开 → Messages → 复制最近的消息/错误

3) 快速命令（在终端复制执行）
- 创建房间（REST）：
  curl -v -X POST "http://127.0.0.1:8000/games" -H "Content-Type: application/json" -d "{\"name\":\"test\"}"
- 查询房间：
  curl -v "http://127.0.0.1:8000/games/{game_id}"
- 模拟 6 个 AI：
  curl -v -X POST "http://127.0.0.1:8000/simulate_ai_game?num_players=6"
- 测试 WebSocket（使用 wscat / npx）：
  npx wscat -c "ws://127.0.0.1:8000/ws/{game_id}"

4) 后端进程与重启（Windows PowerShell 可直接运行）
- 查看占用端口：
  netstat -ano | findstr :8000
- 重启后端（在项目根）：
  set PYTHONPATH=%CD% && cd games/werewolf/backend && .venv\\Scripts\\Activate.ps1 && uvicorn games.werewolf.backend.app:app --reload --host 127.0.0.1 --port 8000
- 重启前端：
  cd games/werewolf/frontend && npm install && npm run dev

5) 参考文件（我将检查这些文件）
- 后端：[`games/werewolf/backend/app.py`](games/werewolf/backend/app.py:1)
- 前端：[`games/werewolf/frontend/src/App.jsx`](games/werewolf/frontend/src/App.jsx:1)

将复制的控制台文本与 HAR/请求粘贴到这里，我会立刻分析并给出修复命令。