# 🐺 AI狼人杀游戏

基于AI的狼人杀游戏测试平台，提供两个独立的软件版本，用于评估不同AI模型的推理和策略能力。

## 📁 项目结构

本项目分为两个独立的软件版本：

```
werewolf-game/
├── qt-project/         # PyQt6版本 (功能完整)
│   ├── src/           # 源代码
│   ├── config/        # 配置文件
│   ├── README.md      # 项目说明
│   └── requirements.txt # 依赖列表
├── ctk-project/       # CustomTkinter版本 (开发中)
│   ├── src/           # 源代码
│   ├── config/        # 配置文件
│   ├── README.md      # 项目说明
│   └── requirements.txt # 依赖列表
├── doc/               # 文档目录
│   ├── README_CUSTOMTKINTER.md  # CustomTkinter版本详细说明
│   ├── REQUIREMENTS.md         # 完整依赖说明
│   ├── 项目架构说明.md         # 技术架构文档
│   └── 开发计划.md            # 项目开发路线图
└── README.md          # 项目总说明
```

## 🎯 版本选择

### 🖥️ PyQt6版本 (qt-project)
- ✅ **功能完整** - 包含完整的游戏逻辑和界面
- ✅ **现代化界面** - 基于PyQt6的现代化图形界面
- ✅ **API支持** - 完整的HTTP API服务器
- ✅ **测试验证** - 包含完整的测试脚本

### 🎨 CustomTkinter版本 (ctk-project)
- 🔄 **开发中** - 基础架构已搭建
- 🔄 **现代化界面** - 基于CustomTkinter的界面
- 🔄 **功能待实现** - 游戏逻辑和AI集成待开发

## 🚀 快速开始

### PyQt6版本 (推荐)
```bash
cd qt-project
pip install -r requirements.txt
python src/main.py
```

### CustomTkinter版本 (开发中)
```bash
cd ctk-project
pip install -r requirements.txt
python src/main.py
```

## ✨ 项目特性

- 🤖 多AI提供商支持 (OpenAI, Claude, Gemini)
- 💬 气泡式聊天界面
- 🎮 完整狼人杀游戏规则
- ⚙️ YAML配置文件管理
- 📊 游戏数据记录和分析

## 📚 文档资源

详细的技术文档和说明请查看 `doc/` 目录：

- **📖 README_CUSTOMTKINTER.md** - CustomTkinter版本详细功能说明
- **📋 REQUIREMENTS.md** - 完整的依赖管理和安装指南
- **🏗️ 项目架构说明.md** - 技术架构和模块设计
- **📅 开发计划.md** - 项目开发路线图和里程碑

## 📄 许可证

本项目采用GNU General Public License v3.0 (GPLv3)许可证。

### 许可证说明

本项目使用GPLv3许可证，这意味着：
- ✅ 您可以自由使用、修改和分发本软件
- ✅ 您可以用于商业目的
- ✅ 您可以修改源代码
- ✅ 您可以分发修改后的版本

**重要要求：**
- 📋 分发时必须包含完整的GPLv3许可证文本
- 📋 修改后的版本必须使用相同的许可证
- 📋 必须提供源代码给接收者

### 完整许可证

详见项目根目录的`LICENSE`文件。

## 🤝 贡献

欢迎提交Issue和Pull Request！所有贡献都将遵循GPLv3许可证。