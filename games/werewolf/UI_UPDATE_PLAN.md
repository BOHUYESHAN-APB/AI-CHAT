# 狼人杀游戏 - 现代化UI更新说明

## 🎨 UI风格统一方案

### 核心设计语言
- **渐变色系**: 紫蓝渐变 (#667eea → #764ba2) 作为主色调
- **卡片式布局**: 所有组件采用圆角卡片 (borderRadius: 16px)
- **柔和阴影**: 使用 rgba 透明度阴影营造层次感
- **流畅动画**: hover/focus 状态添加 transition 过渡
- **图标语言**: 使用 emoji 图标增强视觉识别

### 已更新组件

#### 1. 玩家配置 (PlayersConfig)
- ✅ 头像上传功能 (支持本地图片, base64存储)
- ✅ 网格布局展示玩家卡片
- ✅ 渐变色头像默认背景
- ✅ 交互式按钮 (hover动画)
- ✅ 状态徽章显示玩家数量

#### 2. 圆桌游戏 (RoundTableGame)
- ✅ 圆形桌面布局
- ✅ 渐变色中央状态区
- ✅ 玩家气泡发言
- ✅ 死亡/存活状态可视化

#### 3. 房间列表 (RoomsPanel)
需要更新为卡片式布局

#### 4. API Keys编辑器
需要更新为现代化表单设计

## 📋 修复清单

### 后端修复
- [x] 修复 `start_room_game` - 从config.json读取AI玩家列表
- [x] 应用角色偏好配置
- [x] 支持头像字段存储

### 前端修复
- [x] PlayersConfig - 头像上传 + 现代化UI
- [x] RoundTableGame - 圆桌可视化
- [ ] RoomsPanel - 卡片式布局
- [ ] ApiKeysEditor - 现代化表单
- [ ] 主布局 - 统一导航栏设计

## 🚀 下一步

1. **测试后端修复**
   ```bash
   # 重启后端
   python games/werewolf/backend/app.py
   ```

2. **前端热更新**
   ```bash
   # 前端会自动热更新
   # 刷新浏览器查看变化
   ```

3. **验证流程**
   - 配置6个AI玩家
   - 上传头像
   - 创建房间
   - 开始游戏
   - 查看圆桌UI

## 📸 头像存储说明

头像使用 base64 编码存储在 `config.json`:
```json
{
  "players": ["AI_1", "AI_2", ...],
  "avatars": {
    "AI_1": "data:image/png;base64,iVBORw0KG..."
  }
}
```

在圆桌UI中自动加载显示。
