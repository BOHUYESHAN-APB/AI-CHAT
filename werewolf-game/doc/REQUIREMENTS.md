# 依赖说明

## 📁 项目结构

本项目分为两个独立版本，每个版本有各自的依赖要求：

### PyQt6版本 (qt-project/)
- 功能完整的版本
- 基于PyQt6图形界面
- 包含完整的游戏逻辑和API服务器

### CustomTkinter版本 (ctk-project/)
- 开发中的版本
- 基于CustomTkinter界面
- 轻量级，启动快速

## Python包依赖

### PyQt6版本依赖
```txt
PyQt6>=6.0.0
PyYAML>=6.0
requests>=2.25.0
aiohttp>=3.8.0
openai>=1.0.0
anthropic>=0.3.0
google-generativeai>=0.3.0
```

### CustomTkinter版本依赖
```txt
customtkinter>=5.2.0
PyYAML>=6.0
requests>=2.28.0
openai>=1.0.0
anthropic>=0.3.0
google-generativeai>=0.3.0
```

### 开发工具 (可选)
```txt
black>=23.0.0
pylint>=2.17.0
pytest>=7.0.0
pytest-qt>=4.0.0
```

## 安装命令

### 基础安装
```bash
pip install PyQt6 PyYAML requests aiohttp
```

### 完整安装（包含所有AI服务）
```bash
pip install PyQt6 PyYAML requests aiohttp openai anthropic google-generativeai
```

### 开发环境安装
```bash
pip install PyQt6 PyYAML requests aiohttp openai anthropic google-generativeai black pylint pytest pytest-qt
```

## 版本要求

- **Python**: 3.8+
- **PyQt6**: 6.0.0+
- **OpenAI**: 1.0.0+
- **Anthropic**: 0.3.0+
- **Google Generative AI**: 0.3.0+

## 可选依赖

### 数据库支持
```txt
sqlite3>=3.0.0  # Python内置
```

### 日志处理
```txt
loguru>=0.7.0  # 可选，更友好的日志
```

### 性能优化
```txt
ujson>=5.0.0  # 更快的JSON处理
```

## 环境配置

### 虚拟环境创建
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 依赖安装脚本
创建 `install_deps.py`:
```python
#!/usr/bin/env python3
import subprocess
import sys

dependencies = [
    "PyQt6",
    "PyYAML", 
    "requests",
    "aiohttp",
    "openai",
    "anthropic",
    "google-generativeai"
]

def install_packages():
    for package in dependencies:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ 成功安装: {package}")
        except subprocess.CalledProcessError:
            print(f"❌ 安装失败: {package}")

if __name__ == "__main__":
    install_packages()
```

## 平台兼容性

### Windows
- 完全支持
- 需要Visual C++ Redistributable（PyQt6依赖）

### Linux
- 需要安装系统依赖：
  ```bash
  # Ubuntu/Debian
  sudo apt-get install python3-dev libxcb-xinerama0
  
  # Fedora
  sudo dnf install python3-devel libxcb
  ```

### macOS
- 完全支持
- 可能需要安装Xcode命令行工具

## 故障排除

### 常见安装问题

#### PyQt6安装失败
```bash
# 尝试使用conda
conda install pyqt

# 或使用系统包管理器
# Ubuntu:
sudo apt-get install python3-pyqt6
```

#### API包安装问题
```bash
# 如果遇到权限问题，使用用户安装
pip install --user package-name

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install package-name
```

### 版本冲突
如果遇到版本冲突，可以尝试：
```bash
# 查看当前安装的版本
pip list

# 升级特定包
pip install --upgrade package-name

# 安装特定版本
pip install package-name==version
```

## 开发依赖管理

### 生成requirements.txt
```bash
pip freeze > requirements.txt
```

### 从requirements.txt安装
```bash
pip install -r requirements.txt
```

### 开发依赖分离
建议将开发依赖分开：
```bash
# 生产依赖
pip install PyQt6 PyYAML requests aiohttp

# 开发依赖  
pip install black pylint pytest
```

## 更新日志

### v0.1.0
- 初始依赖配置
- 支持PyQt6界面开发
- 集成主流AI API服务
- 配置YAML文件管理