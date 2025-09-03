#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
狼人杀游戏应用程序类
"""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QTabWidget, QStatusBar, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

from config_manager import ConfigManager
from game_engine import GameEngine
from ai_controller import AIController

logger = logging.getLogger(__name__)

class WerewolfApp(QMainWindow):
    """狼人杀游戏主应用程序"""
    
    def __init__(self):
        super().__init__()
        self.config_manager: Optional[ConfigManager] = None
        self.game_engine: Optional[GameEngine] = None
        self.ai_controller: Optional[AIController] = None
        
        self.setup_ui()
        self.load_config()
        self.setup_connections()
        
    def setup_ui(self):
        """设置用户界面"""
        # 设置窗口属性
        self.setWindowTitle("🐺 AI狼人杀游戏")
        self.setMinimumSize(1200, 800)
        
        # 设置图标
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "werewolf.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题标签
        title_label = QLabel("🐺 AI狼人杀游戏测试平台")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2E86AB; margin: 20px;")
        
        # 副标题
        subtitle_label = QLabel("测试和比较不同AI模型的推理能力")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #6C757D; margin-bottom: 30px;")
        
        # 标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setMovable(False)
        
        # 创建各个标签页
        self.setup_game_tab()
        self.setup_config_tab()
        self.setup_ai_tab()
        self.setup_stats_tab()
        
        # 添加到主布局
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 等待配置AI服务")
        
        # 应用样式
        self.apply_styles()
        
        logger.info("✅ 用户界面设置完成")
    
    def setup_game_tab(self):
        """设置游戏标签页"""
        game_tab = QWidget()
        layout = QVBoxLayout(game_tab)
        
        # 游戏控制区域
        control_layout = QHBoxLayout()
        
        # 开始游戏按钮
        self.start_button = QPushButton("🎮 开始新游戏")
        self.start_button.setMinimumHeight(50)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6C757D;
            }
        """)
        
        # 暂停游戏按钮
        self.pause_button = QPushButton("⏸️ 暂停游戏")
        self.pause_button.setMinimumHeight(50)
        self.pause_button.setEnabled(False)
        
        # 游戏设置按钮
        self.settings_button = QPushButton("⚙️ 游戏设置")
        self.settings_button.setMinimumHeight(50)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.settings_button)
        control_layout.addStretch()
        
        # 游戏状态显示
        status_label = QLabel("游戏状态: 未开始")
        status_label.setStyleSheet("font-size: 14px; color: #6C757D;")
        
        layout.addLayout(control_layout)
        layout.addWidget(status_label)
        layout.addStretch()
        
        self.tab_widget.addTab(game_tab, "🎮 游戏")
    
    def setup_config_tab(self):
        """设置配置标签页"""
        config_tab = QWidget()
        layout = QVBoxLayout(config_tab)
        
        config_label = QLabel("AI服务配置将在这里显示")
        config_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        config_label.setStyleSheet("font-size: 16px; color: #6C757D; margin: 50px;")
        
        layout.addWidget(config_label)
        
        self.tab_widget.addTab(config_tab, "⚙️ 配置")
    
    def setup_ai_tab(self):
        """设置AI标签页"""
        ai_tab = QWidget()
        layout = QVBoxLayout(ai_tab)
        
        ai_label = QLabel("AI玩家管理和设置将在这里显示")
        ai_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ai_label.setStyleSheet("font-size: 16px; color: #6C757D; margin: 50px;")
        
        layout.addWidget(ai_label)
        
        self.tab_widget.addTab(ai_tab, "🤖 AI管理")
    
    def setup_stats_tab(self):
        """设置统计标签页"""
        stats_tab = QWidget()
        layout = QVBoxLayout(stats_tab)
        
        stats_label = QLabel("游戏统计和数据分析将在这里显示")
        stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_label.setStyleSheet("font-size: 16px; color: #6C757D; margin: 50px;")
        
        layout.addWidget(stats_label)
        
        self.tab_widget.addTab(stats_tab, "📊 统计")
    
    def apply_styles(self):
        """应用全局样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F9FA;
            }
            QTabWidget::pane {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #E9ECEF;
                border: 1px solid #DEE2E6;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 20px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #007BFF;
            }
            QTabBar::tab:hover {
                background-color: #DEE2E6;
            }
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056B3;
            }
            QPushButton:disabled {
                background-color: #6C757D;
            }
        """)
    
    def load_config(self):
        """加载配置文件"""
        try:
            self.config_manager = ConfigManager()
            config_loaded = self.config_manager.load_config()
            
            if config_loaded:
                self.status_bar.showMessage("✅ 配置文件加载成功")
                logger.info("✅ 配置文件加载成功")
            else:
                self.status_bar.showMessage("⚠️ 使用默认配置，请检查配置文件")
                logger.warning("⚠️ 使用默认配置")
                
        except Exception as e:
            error_msg = f"❌ 配置加载失败: {e}"
            self.status_bar.showMessage(error_msg)
            logger.error(error_msg)
            QMessageBox.critical(self, "配置错误", f"配置文件加载失败:\n{e}")
    
    def setup_connections(self):
        """设置信号和槽连接"""
        self.start_button.clicked.connect(self.on_start_game)
        self.pause_button.clicked.connect(self.on_pause_game)
        self.settings_button.clicked.connect(self.on_game_settings)
    
    def on_start_game(self):
        """开始游戏按钮点击事件"""
        QMessageBox.information(self, "开始游戏", "开始游戏功能将在后续实现")
    
    def on_pause_game(self):
        """暂停游戏按钮点击事件"""
        QMessageBox.information(self, "暂停游戏", "暂停游戏功能将在后续实现")
    
    def on_game_settings(self):
        """游戏设置按钮点击事件"""
        QMessageBox.information(self, "游戏设置", "游戏设置功能将在后续实现")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        reply = QMessageBox.question(
            self, "确认退出",
            "确定要退出AI狼人杀游戏吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logger.info("🛑 应用程序退出")
            event.accept()
        else:
            event.ignore()