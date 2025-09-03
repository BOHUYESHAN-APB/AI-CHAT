# 项目设置指南

## 快速开始

### 1. 环境准备
确保您的系统已安装：
- Python 3.8 或更高版本
- pip (Python包管理器)

### 2. 克隆项目
```bash
git clone https://github.com/your-username/AI-CHAT.git
cd AI-CHAT
```

### 3. 创建虚拟环境（推荐）
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 4. 安装依赖
```bash
# 创建基础requirements.txt（如果还没有）
echo "PyQt6>=6.0.0
PyYAML>=6.0
requests>=2.25.0
aiohttp>=3.8.0
openai>=1.0.0
anthropic>=0.3.0
google-generativeai>=0.3.0" > requirements.txt

# 安装依赖
pip install -r requirements.txt
```

### 5. 项目结构初始化
```bash
# 创建必要的目录结构
mkdir -p werewolf-game/src/ui
mkdir -p werewolf-game/src/models
mkdir -p werewolf-game/config
mkdir -p werewolf-game/assets/icons
mkdir -p werewolf-game/assets/styles
mkdir -p common/ai_providers
mkdir -p common/utils
mkdir -p tests/unit_tests
mkdir -p tests/integration_tests
mkdir -p logs
```

## AI API 配置

### 1. 获取API密钥

#### OpenAI API
1. 访问 https://platform.openai.com
2. 注册账号并登录
3. 进入API Keys页面
4. 创建新的API密钥
5. 复制密钥备用

#### Anthropic API (Claude)
1. 访问 https://console.anthropic.com
2. 注册账号并登录
3. 进入API Keys页面
4. 创建新的API密钥
5. 复制密钥备用

#### Google AI API (Gemini)
1. 访问 https://makersuite.google.com
2. 使用Google账号登录
3. 创建API密钥
4. 复制密钥备用

### 2. 创建配置文件
```bash
# 进入狼人杀游戏目录
cd werewolf-game

# 创建配置文件模板
cat > config/config.template.yaml << 'EOF'
# AI游戏测试平台配置文件
version: "1.0.0"

# AI服务提供商配置
ai_providers:
  - name: "GPT-4"
    provider: "openai"
    api_key: "your-openai-api-key-here"
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 1000
    enabled: true
    
  - name: "Claude-3"
    provider: "anthropic" 
    api_key: "your-claude-api-key-here"
    model: "claude-3-sonnet-20240229"
    temperature: 0.7
    max_tokens: 1000
    enabled: true

# 游戏设置
game_settings:
  display:
    theme: "dark"
    language: "zh-CN"
    font_size: 12

# 狼人杀游戏设置
werewolf_game:
  default_settings:
    player_count: 8
    roles:
      werewolf: 2
      villager: 4
      prophet: 1
      witch: 1
EOF

# 复制模板为实际配置文件
cp config/config.template.yaml config/config.yaml
```

### 3. 编辑配置文件
用文本编辑器打开 `werewolf-game/config/config.yaml`，替换其中的API密钥：

```yaml
ai_providers:
  - name: "GPT-4"
    provider: "openai"
    api_key: "sk-your-actual-openai-key"  # 替换为实际密钥
    model: "gpt-4"
    # ... 其他设置
    
  - name: "Claude-3"
    provider: "anthropic"
    api_key: "sk-ant-your-actual-claude-key"  # 替换为实际密钥
    model: "claude-3-sonnet-20240229"
    # ... 其他设置
```

### 4. 环境变量配置（可选）
您也可以使用环境变量来设置API密钥：

```bash
# Windows
set OPENAI_API_KEY=sk-your-openai-key
set ANTHROPIC_API_KEY=sk-ant-your-claude-key
set GOOGLE_API_KEY=your-google-key

# Linux/Mac
export OPENAI_API_KEY=sk-your-openai-key
export ANTHROPIC_API_KEY=sk-ant-your-claude-key
export GOOGLE_API_KEY=your-google-key
```

## 首次运行

### 1. 创建主程序入口
```bash
# 创建狼人杀游戏主程序
cat > werewolf-game/src/main.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
狼人杀游戏主程序入口
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    """主函数"""
    print("🐺 AI狼人杀游戏启动中...")
    print("📁 当前目录:", os.getcwd())
    print("🚀 准备启动PyQt6界面...")
    
    # 这里将会启动PyQt6应用程序
    # 实际代码将在后续开发中实现
    
    print("✅ 程序初始化完成")
    print("📋 下一步：实现PyQt6主界面")

if __name__ == "__main__":
    main()
EOF
```

### 2. 运行测试
```bash
# 运行主程序测试
cd werewolf-game
python src/main.py
```

您应该看到类似这样的输出：
```
🐺 AI狼人杀游戏启动中...
📁 当前目录: /path/to/AI-CHAT/werewolf-game
🚀 准备启动PyQt6界面...
✅ 程序初始化完成
📋 下一步：实现PyQt6主界面
```

## 开发模式设置

### 1. 安装开发工具
```bash
pip install black pylint pytest pytest-qt
```

### 2. 代码格式化配置
创建 `.pre-commit-config.yaml`：
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/pylint
    rev: v2.17.0
    hooks:
      - id: pylint
        additional_dependencies: [pylint-qt6]
```

### 3. 编辑器配置
创建 `.editorconfig`：
```ini
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
max_line_length = 88
```

## 故障排除

### 常见问题

#### 1. PyQt6安装失败
```bash
# 尝试使用conda安装
conda install pyqt

# 或者使用系统包管理器
# Ubuntu/Debian
sudo apt-get install python3-pyqt6

# Fedora
sudo dnf install python3-qt6
```

#### 2. API密钥无效
- 检查API密钥格式是否正确
- 确认API服务是否可用
- 检查网络连接

#### 3. 导入错误
确保Python路径设置正确：
```python
import sys
sys.path.insert(0, '/path/to/your/project')
```

### 调试模式
启用详细日志：
```bash
# 设置环境变量
export PYTHONPATH=.:$PYTHONPATH
export QT_DEBUG_PLUGINS=1
export DEBUG=1

# 运行程序
python werewolf-game/src/main.py
```

## 下一步行动

根据我们的开发计划，接下来需要：

1. **实现PyQt6主窗口框架** - 创建基本的GUI界面
2. **开发AI API配置管理系统** - 实现配置文件的读取和验证
3. **设计YAML配置文件结构** - 完善配置文件的详细结构
4. **创建可视化AI配置界面** - 让用户可以通过UI配置AI设置

### 立即开始开发
```bash
# 切换到代码模式进行具体实现
# 我将为您切换到Code模式来开始PyQt6开发
```

## 支持与帮助

如果遇到问题，请：

1. 检查本文档的相关章节
2. 查看项目README.md文件
3. 检查日志文件 `logs/game.log`
4. 在项目Issue中提出问题

## 更新日志

### v0.1.0 - 初始设置
- ✅ 项目基础结构创建
- ✅ 文档系统完善
- ✅ 配置文件模板
- ✅ 开发环境设置
- 🔄 PyQt6界面开发（进行中）

---

*祝您开发愉快！🐺🎮*