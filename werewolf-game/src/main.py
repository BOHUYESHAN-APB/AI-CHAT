#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
狼人杀游戏主程序入口
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app import WerewolfApp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / 'logs' / 'game.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """主函数"""
    try:
        # 创建必要的目录
        (project_root / 'logs').mkdir(exist_ok=True)
        (project_root / 'config').mkdir(exist_ok=True)
        
        logger.info("🐺 AI狼人杀游戏启动中...")
        logger.info(f"📁 项目根目录: {project_root}")
        
        # 创建Qt应用
        app = QApplication(sys.argv)
        app.setApplicationName("AI Werewolf Game")
        app.setApplicationVersion("0.1.0")
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        
        # 创建主应用窗口
        main_app = WerewolfApp()
        main_app.show()
        
        logger.info("✅ 应用程序初始化完成")
        logger.info("🚀 启动主事件循环...")
        
        # 运行应用
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"❌ 应用程序启动失败: {e}")
        logger.exception("详细错误信息:")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)