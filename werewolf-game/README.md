# 🐺 AI狼人杀游戏

基于PyQt6的AI狼人杀游戏测试平台，用于评估不同AI模型的推理和策略能力。

## 项目特性

- 🤖 多AI提供商支持 (OpenAI, Claude, Gemini)
- 🖥️ PyQt6可视化界面
- 💬 气泡式聊天界面
- 🎮 完整狼人杀游戏规则
- ⚙️ YAML配置文件管理
- 📊 游戏数据记录和分析

## 快速开始

### 1. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置AI API
复制配置文件模板并编辑：
```bash
cp config/config.template.yaml config/config.yaml
# 编辑config.yaml，添加您的API密钥
```

### 4. 运行游戏
```bash
python src/main.py
```

## 项目结构

```
werewolf-game/
├── src/                 # 源代码
│   ├── main.py         # 程序入口
│   ├── app.py          # 应用程序类
│   ├── config_manager.py
│   ├── game_engine.py
│   ├── ai_controller.py
│   ├── ui/             # 用户界面
│   └── models/         # 数据模型
├── config/             # 配置文件
├── assets/             # 资源文件
├── tests/              # 测试代码
├── venv/               # 虚拟环境
└── requirements.txt    # 依赖列表
```

## 开发状态

- ✅ 项目架构设计
- ✅ 文档系统
- 🔄 PyQt6界面开发 (进行中)
- 🔄 AI集成开发
- 🔄 游戏规则实现

## 许可证

MIT License - 详见项目根目录的LICENSE.md文件