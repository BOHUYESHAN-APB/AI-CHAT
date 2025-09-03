# 开发指南

## 开发环境设置

### 1. 环境要求
- Python 3.8+
- PyQt6
- 其他依赖见各模块的requirements.txt

### 2. 安装开发环境
```bash
# 克隆项目
git clone https://github.com/your-username/AI-CHAT.git
cd AI-CHAT

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装基础依赖
pip install -r requirements.txt
```

### 3. 项目结构说明
```
AI-CHAT/
├── werewolf-game/          # 狼人杀游戏主模块
│   ├── src/               # 源代码目录
│   │   ├── main.py        # 程序入口点
│   │   ├── app.py         # 应用程序类
│   │   ├── config_manager.py  # 配置管理
│   │   ├── game_engine.py # 游戏引擎
│   │   ├── ai_controller.py # AI控制器
│   │   ├── ui/            # 用户界面
│   │   └── models/        # 数据模型
│   ├── config/            # 配置文件
│   ├── assets/            # 资源文件
│   └── tests/             # 测试代码
├── common/                # 公共组件
└── docs/                  # 文档
```

## 开发流程

### 1. 代码规范
- 遵循PEP 8编码规范
- 使用类型注解
- 函数和类要有docstring
- 变量命名要有意义

### 2. Git工作流
```bash
# 创建功能分支
git checkout -b feature/your-feature

# 提交更改
git add .
git commit -m "feat: 添加新功能"

# 推送到远程
git push origin feature/your-feature

# 创建Pull Request
```

### 3. 提交信息规范
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 代码重构
- test: 测试相关
- chore: 构建过程或辅助工具变动

## PyQt6开发指南

### 1. 界面设计最佳实践
```python
# 使用Qt Designer设计界面
# 保存为.ui文件，然后使用pyuic6转换为Python代码
pyuic6 main_window.ui -o main_window.py

# 在代码中继承UI类
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
```

### 2. 信号和槽机制
```python
# 连接信号和槽
button.clicked.connect(self.on_button_click)

# 自定义信号
class Worker(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(object)
    
    def run(self):
        # 执行任务
        self.finished.emit()
```

### 3. 多线程处理
```python
# 使用QThread处理耗时操作
class WorkerThread(QThread):
    def run(self):
        # 执行耗时任务
        pass

# 在主线程中创建和工作线程
worker = WorkerThread()
worker.start()
```

## AI集成开发

### 1. 添加新的AI提供商
```python
# 在common/ai_providers/中创建新文件
class NewAIProvider(BaseAIProvider):
    def __init__(self, config):
        super().__init__(config)
        
    def send_message(self, message, **kwargs):
        # 实现API调用逻辑
        pass
        
    def get_models(self):
        # 返回支持的模型列表
        pass
```

### 2. API调用模式
```python
async def call_ai_provider(provider, message):
    try:
        response = await provider.send_message(message)
        return response
    except Exception as e:
        logger.error(f"API调用失败: {e}")
        return None
```

## 游戏引擎开发

### 1. 游戏状态管理
```python
class GameState:
    def __init__(self):
        self.phase = "night"  # night/day
        self.round = 1
        self.players = []
        self.alive_players = []
        self.dead_players = []
        
    def next_phase(self):
        # 切换到下一阶段
        pass
```

### 2. 角色系统
```python
class Role:
    def __init__(self, name, team, description):
        self.name = name
        self.team = team
        self.description = description
        
    def night_action(self, game_state, target):
        # 夜晚行动逻辑
        pass
        
    def day_action(self, game_state, target):
        # 白天行动逻辑
        pass
```

## 测试开发

### 1. 单元测试
```python
import unittest
from werewolf_game.src.game_engine import GameEngine

class TestGameEngine(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        
    def test_initialization(self):
        self.assertIsNotNone(self.engine.game_state)
        
    def test_role_assignment(self):
        # 测试角色分配逻辑
        pass
```

### 2. 集成测试
```python
class TestAIIntegration(unittest.TestCase):
    def test_ai_communication(self):
        # 测试AI通信功能
        pass
```

## 调试技巧

### 1. 日志记录
```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

### 2. 调试PyQt6应用
```python
# 启用Qt调试信息
import os
os.environ['QT_DEBUG_PLUGINS'] = '1'

# 使用pdb调试
import pdb; pdb.set_trace()
```

## 性能优化

### 1. API调用优化
- 使用异步IO处理并发请求
- 实现请求缓存机制
- 批量处理相似请求

### 2. 内存管理
- 及时清理不再使用的对象
- 使用弱引用避免循环引用
- 优化数据结构选择

### 3. UI性能
- 使用QSS而不是动态样式设置
- 避免在UI线程执行耗时操作
- 使用模型-视图架构

## 部署指南

### 1. 打包应用
```bash
# 使用PyInstaller打包
pip install pyinstaller
pyinstaller --windowed --name="AI-Werewolf" main.py

# 使用cx_Freeze打包
pip install cx_Freeze
python setup.py build
```

### 2. 创建安装程序
- 使用Inno Setup (Windows)
- 使用PackageMaker (macOS)
- 使用deb/rpm包 (Linux)

## 常见问题解决

### 1. PyQt6安装问题
```bash
# 如果遇到安装问题，尝试使用conda
conda install pyqt

# 或者使用系统包管理器
# Ubuntu/Debian
sudo apt-get install python3-pyqt6

# Fedora
sudo dnf install python3-qt6
```

### 2. API密钥配置
- 确保API密钥格式正确
- 检查网络连接
- 验证API配额和权限

### 3. 界面显示问题
- 检查QSS样式表语法
- 验证资源文件路径
- 测试不同DPI设置

## 贡献指南

### 1. 代码审查标准
- 代码符合PEP 8规范
- 有适当的测试覆盖
- 文档齐全
- 性能考虑周到

### 2. 功能开发流程
1. 创建Issue描述需求
2. 讨论设计方案
3. 实现功能代码
4. 编写测试用例
5. 提交Pull Request
6. 代码审查和合并

### 3. 文档要求
- README.md保持更新
- 添加必要的代码注释
- 更新API文档
- 提供使用示例

## 资源链接

### 官方文档
- [PyQt6文档](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Python文档](https://docs.python.org/3/)
- [Qt文档](https://doc.qt.io/)

### 学习资源
- [PyQt6教程](https://www.pythonguis.com/tutorials/)
- [Qt设计模式](https://doc.qt.io/qt-6/model-view-programming.html)
- [Python并发编程](https://docs.python.org/3/library/concurrency.html)

### 工具推荐
- Qt Designer: 界面设计工具
- Black: 代码格式化工具
- Pylint: 代码质量检查
- pytest: 测试框架