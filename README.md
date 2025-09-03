# AI Game Testing Platform / AI游戏测试平台

🎮 一个用于测试和比较不同AI模型能力的游戏平台

## 项目简介

本项目旨在通过复刻经典游戏（如狼人杀、AI小镇等）来评估和比较不同AI模型的推理、策略制定和交互能力。每个游戏测试都在独立的文件夹中作为单独的项目模块。

## 主要特性

- 🤖 **多AI支持**: 支持配置无限数量的AI API（OpenAI、Claude、Gemini等）
- 🖥️ **可视化界面**: 基于PyQt6的直观用户界面
- 💬 **实时聊天**: 气泡式聊天界面，实时显示AI之间的对话
- 🎯 **游戏引擎**: 完整的狼人杀游戏规则引擎
- ⚙️ **灵活配置**: YAML格式的配置文件，支持自定义设置
- 🎮 **用户参与**: 支持用户作为玩家或裁判参与游戏
- 📊 **数据分析**: 记录和分析AI表现，比较不同模型能力

## 项目结构

```
AI-CHAT/
├── werewolf-game/          # 狼人杀游戏模块
│   ├── src/               # 源代码
│   ├── config/            # 配置文件
│   ├── assets/            # 资源文件
│   └── docs/              # 文档
├── ai-town/               # AI小镇模块（待开发）
├── other-games/           # 其他游戏模块（待开发）
├── common/                # 共用组件和工具
├── LICENSE                # MIT许可证
└── README.md              # 项目说明
```

## 技术栈

- **前端界面**: PyQt6
- **配置管理**: YAML
- **AI接口**: 多种AI API支持
- **数据存储**: JSON/SQLite
- **编程语言**: Python 3.8+

## 快速开始

### 环境要求

- Python 3.8+
- PyQt6
- 其他依赖见各模块的requirements.txt

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/your-username/AI-CHAT.git
cd AI-CHAT
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置AI API
   - 复制配置模板：`cp config/config.template.yaml config/config.yaml`
   - 编辑配置文件，添加您的AI API密钥

4. 运行狼人杀游戏
```bash
cd werewolf-game
python main.py
```

## 游戏模块

### 🐺 狼人杀 (Werewolf Game)

经典的狼人杀游戏，支持：
- 多种角色配置（狼人、村民、预言家、女巫等）
- 自动角色分配
- 完整的昼夜循环流程
- 实时AI对话显示
- 手动游戏进程控制

### 🏘️ AI小镇 (AI Town) - 计划中

基于AI的虚拟小镇模拟游戏。

### 🎲 其他游戏 - 计划中

更多经典游戏的AI版本实现。

## 配置说明

### AI API配置

在`config/config.yaml`中配置您的AI服务：

```yaml
ai_providers:
  - name: "GPT-4"
    provider: "openai"
    api_key: "your-openai-key"
    model: "gpt-4"
    
  - name: "Claude"
    provider: "anthropic"
    api_key: "your-claude-key"
    model: "claude-3-sonnet"
```

### 游戏设置

```yaml
game_settings:
  player_count: 8
  roles:
    werewolf: 2
    villager: 4
    prophet: 1
    witch: 1
  
  display:
    show_roles: false
    chat_style: "bubble"
    layout: "circular"
```

## 开发指南

### 添加新的AI提供商

1. 在`common/ai_providers/`中创建新的提供商类
2. 实现标准的AI接口
3. 在配置文件中添加相应设置

### 添加新游戏

1. 在项目根目录创建新的游戏文件夹
2. 实现游戏规则引擎
3. 创建相应的UI界面
4. 添加配置文件支持

## 贡献指南

欢迎提交Issues和Pull Requests！请阅读[贡献指南](CONTRIBUTING.md)了解详情。

## 许可证

本项目采用MIT许可证 - 详见[LICENSE](LICENSE)文件。

## 联系方式

- 项目维护者：[您的名字]
- 邮箱：[您的邮箱]
- 项目地址：https://github.com/yrname/AI-CHAT

## 更新日志

### v0.1.0 (开发中)
- 项目初始化
- 狼人杀游戏基础框架
- AI API配置系统
- PyQt6界面设计

---

*让AI在游戏中展现智慧，在竞技中见证进步！*