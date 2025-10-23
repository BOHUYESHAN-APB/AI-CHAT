# 狼人杀AI对战 - 桌面应用版

## 📦 完整功能清单

### ✅ 已完成功能

#### 后端核心逻辑
- [x] 6-12人游戏支持
- [x] 完整角色系统（狼人、预言家、女巫、猎人、守卫、村民、丘比特、白痴）
- [x] 角色分配与偏好配置
- [x] **狼人3轮夜间讨论机制**
- [x] **各职业夜间思考独白**（预言家、女巫、守卫）
- [x] 白天发言系统
- [x] 投票与公投机制
- [x] 完整历史记录（含夜间讨论）
- [x] 多provider API配置
- [x] 自动化测试脚本

#### 前端UI系统
- [x] 统一现代化主题（紫蓝渐变）
- [x] 组件库（Card、Button、RoleBadge等）
- [x] 圆桌游戏可视化
- [x] 头像系统
- [x] 发言气泡显示

#### 桌面应用
- [x] Electron配置
- [x] 自动启动后端
- [x] 自定义菜单
- [x] Windows/macOS打包支持

### 🚧 待优化功能

- [ ] 夜间讨论UI可视化（狼人协商过程）
- [ ] 职业独白显示面板
- [ ] 历史回放功能
- [ ] 游戏录像导出
- [ ] 统计分析面板
- [ ] 音效与动画

---

## 🚀 快速开始

### 开发环境运行

1. **启动后端**（在项目根目录）:
   ```powershell
   python games/werewolf/backend/app.py
   ```

2. **启动前端**（在 `games/werewolf/frontend` 目录）:
   ```powershell
   npm install
   npm run dev
   ```

3. 浏览器访问 `http://localhost:5173`

### 运行自动化测试

```powershell
python games/werewolf/scripts/test_game_flow.py
```

### 桌面应用开发模式

```powershell
cd games/werewolf/frontend
npm install
npm run electron:dev
```

### 打包桌面应用

```powershell
cd games/werewolf/frontend
npm run electron:build
```

生成的安装包在 `games/werewolf/frontend/dist-electron` 目录。

---

## 📖 核心功能详解

### 1. 夜间发言机制

#### 狼人讨论（3轮）
- **第1轮**: 各狼人提出击杀建议
- **第2轮**: 讨论与协商
- **第3轮**: 最终决策

数据存储在 `history[].night_talks` 中：
```json
{
  "player": "AI_1",
  "round": 1,
  "speech": "我建议杀AI_4",
  "meta": {"heuristic": false},
  "model": "gpt-4",
  "latency": 1.2
}
```

#### 职业独白
- **预言家**: 查验结果与推理
- **女巫**: 用药决策思考
- **守卫**: 守护策略

数据存储在同一 `night_talks` 数组：
```json
{
  "player": "AI_3",
  "role": "seer",
  "speech": "[seer独白] 我查验了AI_5，发现他是villager",
  "type": "monologue"
}
```

### 2. UI主题系统

所有组件使用统一的 `theme.js` 配置：

```javascript
import { theme, Card, Button, RoleBadge } from './components';

// 使用示例
<Card hover>
  <RoleBadge role="werewolf" size="md" />
  <Button variant="primary">开始游戏</Button>
</Card>
```

### 3. 桌面应用架构

```
frontend/
├── electron/
│   ├── main.js       # Electron主进程（启动后端+窗口管理）
│   └── preload.js    # 安全上下文桥接
├── src/
│   ├── theme.js      # 统一主题配置
│   ├── components.jsx # 通用组件库
│   ├── App.jsx       # 主应用
│   └── RoundTableGame.jsx # 游戏可视化
└── package.json      # 含Electron配置
```

---

## 🎮 游戏逻辑流程

```
创建房间 → 配置玩家/角色 → 开始游戏
    ↓
夜间（Night Phase）:
  1. 狼人3轮讨论 → 决定击杀目标
  2. 预言家查验 → 生成独白
  3. 女巫用药 → 生成独白
  4. 守卫守护 → 生成独白
  5. 记录所有night_talks
    ↓
白天（Day Phase）:
  1. 公布夜间结果
  2. 所有玩家发言（current_talks）
  3. 投票公投
  4. 处决玩家
    ↓
判定胜负 → 循环或结束
```

---

## 🔧 配置文件说明

### `api_keys.json` (项目根目录)
```json
{
  "providers": {
    "openai-main": {
      "api_key": "sk-xxx",
      "model": "gpt-4o-mini",
      "model_url": "https://api.openai.com/v1/chat/completions"
    },
    "azure-team": {
      "api_key": "az-xxx",
      "model": "gpt-35-turbo",
      "model_url": "https://xxx.openai.azure.com/..."
    }
  },
  "player_map": {
    "AI_1": "openai-main",
    "AI_2": "azure-team"
  }
}
```

### `games/werewolf/config.json`
```json
{
  "players": ["AI_1", "AI_2", "AI_3", "AI_4", "AI_5", "AI_6"],
  "role_preferences": {
    "AI_1": "werewolf",
    "AI_3": "seer",
    "AI_5": "witch"
  },
  "avatars": {
    "AI_1": "data:image/png;base64,..."
  }
}
```

---

## 📊 API端点参考

### 房间管理
- `GET /rooms` - 获取所有房间
- `POST /rooms` - 创建房间
- `POST /rooms/:id/start` - 开始游戏
- `POST /rooms/:id/step` - 推进回合
- `GET /rooms/:id/state` - 获取房间状态

### 配置管理
- `GET /config/api_keys` - 获取API配置
- `POST /config/api_keys` - 更新API配置
- `GET /config/players` - 获取玩家配置
- `POST /config/players` - 更新玩家配置

---

## 🐛 故障排查

### 问题：后端无法启动
- 检查端口8080是否被占用
- 确认Python环境已激活
- 查看是否缺少依赖（`pip install -r requirements.txt`）

### 问题：前端无法连接后端
- 确认后端运行在 `http://127.0.0.1:8080`
- 检查 `vite.config.js` 中的代理配置
- 查看浏览器控制台的CORS错误

### 问题：AI没有发言
- 检查 `api_keys.json` 配置是否正确
- 查看后端日志中的AI调用错误
- 确认至少运行了2次 step（lobby→night→day）

### 问题：角色显示unknown
- 已修复：`game.roles` 字段已添加
- 刷新前端页面或重新启动

---

## 📝 下一步开发建议

1. **夜间讨论可视化**
   - 创建专门的夜间讨论面板
   - 显示狼人3轮协商过程
   - 动画展示职业独白

2. **完整UI统一**
   - 使用新的组件库重构所有页面
   - 统一卡片、按钮、表单样式
   - 添加过渡动画

3. **桌面应用优化**
   - 添加托盘图标
   - 系统通知集成
   - 自动更新功能

4. **游戏增强**
   - 历史回放系统
   - 统计分析面板
   - 自定义角色配置UI

---

## 📄 许可证

MIT License

---

**开发团队**: AI-CHAT Project  
**最后更新**: 2025-10-13
