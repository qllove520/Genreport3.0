# ui/bug_query_page_raw.py.backup - 重构后的历史BUG查询页面

import os
import configparser
import traceback
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QHeaderView, QMessageBox, QFileDialog,
    QProgressBar, QSplitter, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QTextCursor, QFont

from core.settings_manager import SettingsManager
from core.bug_operator_worker import BugOperatorWorker


class AdminConfigDialog(QDialog):
    """管理员配置对话框"""

    def __init__(self, current_username="", current_password="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理员账号配置")
        self.setModal(True)
        self.resize(400, 200)

        layout = QFormLayout()

        self.username_input = QLineEdit(current_username)
        self.username_input.setPlaceholderText("请输入管理员账号")
        layout.addRow("管理员账号:", self.username_input)

        self.password_input = QLineEdit(current_password)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("请输入管理员密码")
        layout.addRow("管理员密码:", self.password_input)

        # 添加说明
        info_label = QLabel("注意：管理员账号将用于BUG操作，请确保账号具有相应权限")
        info_label.setStyleSheet("color: #666; font-size: 15px;")
        info_label.setWordWrap(True)
        layout.addRow(info_label)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_config(self):
        return self.username_input.text().strip(), self.password_input.text().strip()


class BugQueryPage(QWidget):
    """历史BUG查询页面 - 重构版本"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_detailed("🚀 初始化BugQueryPage开始")

        self.settings_manager = SettingsManager("bug_query")
        self.bug_operator_worker = None
        self.user_info = None
        self.current_bugs = []
        # 初始化管理员配置变量
        self.manager_account = ""
        self.manager_password = ""

        self.log_detailed("📋 开始初始化UI组件")
        # 先初始化UI组件
        self.init_ui()

        self.log_detailed("⚙️ UI组件初始化完成，开始加载管理员配置")
        # 然后加载管理员配置（现在log_output已经存在）
        self.load_admin_config()

        self.log_detailed("📖 开始加载用户设置")
        # 最后加载设置
        self.load_settings()

        self.log_detailed("✅ BugQueryPage初始化完成")

    def log_detailed(self, message, level="INFO", is_error=False, clear=False):
        """详细日志记录方法"""
        if hasattr(self, 'log_output'):
            # 如果UI已经初始化，使用标准log方法
            self.log(f"[{level}] {message}", is_error=is_error, clear=clear)
        else:
            # 如果UI还未初始化，使用print输出
            print(f"[{datetime.now().strftime('%H:%M:%S')}][{level}] {message}")

    def load_admin_config(self):
        """加载管理员配置"""
        self.log_detailed("🔧 开始加载管理员配置文件", "CONFIG")

        try:
            config = configparser.ConfigParser()
            config_path = os.path.join(os.getcwd(), "config", "admin_account.ini")

            self.log_detailed(f"📁 配置文件路径: {config_path}", "CONFIG")

            if os.path.exists(config_path):
                self.log_detailed("✅ 配置文件存在，开始读取", "CONFIG")
                config.read(config_path, encoding='utf-8')

                if 'admin' in config:
                    self.manager_account = config['admin'].get('username', '')
                    # 只记录用户名长度，不记录实际密码
                    password_length = len(config['admin'].get('password', ''))
                    self.manager_password = config['admin'].get('password', '')

                    self.log_detailed(f"👤 管理员账号: {self.manager_account}", "CONFIG")
                    self.log_detailed(f"🔐 密码长度: {password_length} 字符", "CONFIG")
                    self.log_detailed("✅ 管理员配置加载成功", "CONFIG")
                else:
                    self.log_detailed("⚠️ 配置文件中未找到[admin]节", "CONFIG")
                    self.manager_account = ""
                    self.manager_password = ""
            else:
                self.log_detailed("⚠️ 配置文件不存在，创建默认配置", "CONFIG")
                self.manager_account = ""
                self.manager_password = ""
                self._create_default_admin_config()

            # 更新UI状态
            self.log_detailed("🔄 更新管理员状态UI", "CONFIG")
            self._update_admin_status()

        except Exception as e:
            self.log_detailed(f"❌ 加载管理员配置失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)
            self.manager_account = ""
            self.manager_password = ""
            # 确保即使出错也更新UI状态
            self._update_admin_status()

    def _create_default_admin_config(self):
        """创建默认管理员配置文件"""
        self.log_detailed("📝 开始创建默认配置文件", "CONFIG")

        try:
            config_dir = os.path.join(os.getcwd(), "config")
            self.log_detailed(f"📁 配置目录: {config_dir}", "CONFIG")

            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                self.log_detailed("✅ 配置目录创建成功", "CONFIG")

            config_path = os.path.join(config_dir, "admin_account.ini")
            self.log_detailed(f"📄 创建配置文件: {config_path}", "CONFIG")

            default_config = """[admin]
username = 
password = 

[security]
encrypted = false
last_updated = 2025-08-15

[permissions]
allowed_operations = bug_query,bug_edit,bug_close,bug_activate
max_session_duration = 3600
"""

            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(default_config)

            self.log_detailed("✅ 默认配置文件创建成功", "CONFIG")

        except Exception as e:
            self.log_detailed(f"❌ 创建默认配置文件失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)

    def init_ui(self):
        self.log_detailed("🎨 开始创建主界面布局", "UI")
        main_layout = QVBoxLayout(self)

        # 权限检查面板
        self.log_detailed("🔐 创建权限检查面板", "UI")
        permission_panel = self._create_permission_panel()
        main_layout.addWidget(permission_panel)

        # 查询条件面板
        self.log_detailed("🔍 创建查询条件面板", "UI")
        query_panel = self._create_query_panel()
        main_layout.addWidget(query_panel)

        # 创建水平分割器
        self.log_detailed("📐 创建水平分割器", "UI")
        content_splitter = QSplitter(Qt.Horizontal)

        # 左侧：BUG列表
        self.log_detailed("📋 创建BUG列表面板", "UI")
        bug_list_panel = self._create_bug_list_panel()
        content_splitter.addWidget(bug_list_panel)

        # 右侧：操作面板和日志
        self.log_detailed("⚙️ 创建右侧操作面板", "UI")
        right_panel = self._create_right_panel()
        content_splitter.addWidget(right_panel)

        # 设置分割比例
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 2)

        main_layout.addWidget(content_splitter)
        self.log_detailed("✅ UI界面创建完成", "UI")

    def _create_permission_panel(self):
        """创建权限检查面板"""
        panel = QGroupBox("操作权限状态")
        layout = QHBoxLayout()

        # 操作人信息
        self.operator_label = QLabel("操作人: 未登录")
        self.operator_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(self.operator_label)

        # 权限状态
        self.permission_status = QLabel("权限: 无")
        self.permission_status.setStyleSheet("color: #999;")
        layout.addWidget(self.permission_status)

        # 管理员配置状态
        self.admin_status = QLabel("管理员配置: 检查中...")
        self.admin_status.setStyleSheet("color: #999;")
        layout.addWidget(self.admin_status)

        layout.addStretch()

        # 配置管理员账号按钮
        self.config_admin_btn = QPushButton("配置管理员账号")
        self.config_admin_btn.clicked.connect(self._show_admin_config_dialog)
        self.config_admin_btn.setFixedHeight(30)
        layout.addWidget(self.config_admin_btn)

        panel.setLayout(layout)
        return panel

    def _create_query_panel(self):
        """创建查询条件面板 - 两种查询方式"""
        panel = QGroupBox("Bug查询条件")
        layout = QVBoxLayout()

        # 第一行：项目名称（必填）
        project_layout = QHBoxLayout()
        project_label = QLabel("产品名称:")
        project_label.setFixedWidth(80)
        project_label.setStyleSheet("font-weight: bold; color: #d32f2f;")  # 红色表示必填

        self.project_input = QLineEdit()
        self.project_input.setPlaceholderText("必填：输入产品名称，如：2600F")
        self.project_input.setMinimumHeight(32)
        self.project_input.textChanged.connect(self._on_query_conditions_changed)
        self.project_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 13px;
                background-color: #fff8f0;
            }
            QLineEdit:focus {
                border-color: #d32f2f;
                background-color: white;
            }
        """)

        project_layout.addWidget(project_label)
        project_layout.addWidget(self.project_input, 1)
        layout.addLayout(project_layout)

        # 分隔线
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #e0e0e0; margin: 10px 0;")
        layout.addWidget(line)

        # 查询方式说明
        info_label = QLabel("📋 查询方式（选择其一）：")
        info_label.setStyleSheet("font-weight: bold; color: #1976d2; margin: 5px 0;")
        layout.addWidget(info_label)

        # 第二行：方式一 - 指派给 + 解决方案
        method1_layout = QHBoxLayout()

        # 方式一标签
        method1_label = QLabel("方式一:")
        method1_label.setFixedWidth(60)
        method1_label.setStyleSheet("font-weight: bold; color: #4caf50;")

        # 指派给
        assigned_label = QLabel("指派给:")
        assigned_label.setFixedWidth(60)
        assigned_label.setStyleSheet("font-weight: bold; color: #333;")

        self.assigned_combo = QComboBox()
        self.assigned_combo.setEditable(True)
        self.assigned_combo.addItems([
            "全部", "张诗婉", "徐芬","江信辉", "周雪波", "袁超凡","朱双彬","何琪","刘雨鑫","邱国祥"
            , "Closed",""
        ])
        self.assigned_combo.setCurrentText("")  # 默认空白
        self.assigned_combo.setMinimumHeight(32)
        self.assigned_combo.setFixedWidth(140)
        self.assigned_combo.currentTextChanged.connect(self._on_query_conditions_changed)
        self.assigned_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 12px;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #4caf50;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)

        # + 号连接符
        plus_label = QLabel("+")
        plus_label.setFixedWidth(20)
        plus_label.setAlignment(Qt.AlignCenter)
        plus_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #4caf50;")

        # 解决方案
        solution_label = QLabel("解决方案:")
        solution_label.setFixedWidth(70)
        solution_label.setStyleSheet("font-weight: bold; color: #333;")

        self.solution_combo = QComboBox()
        self.solution_combo.setEditable(True)
        self.solution_combo.addItems([
            "全部", "设计如此", "重复Bug", "外部原因", "已解决",
            "无法重现", "延期处理", "不予解决", "评审通过", "项目终止"
        ])
        self.solution_combo.setCurrentText("")  # 默认空白
        self.solution_combo.setMinimumHeight(32)
        self.solution_combo.setFixedWidth(140)
        self.solution_combo.currentTextChanged.connect(self._on_query_conditions_changed)
        self.solution_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 12px;
                background-color: white;
            }
            QComboBox:focus {
                border-color: #4caf50;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)

        # 方式一状态指示器
        self.method1_status = QLabel("❌")
        self.method1_status.setFixedWidth(30)
        self.method1_status.setAlignment(Qt.AlignCenter)
        self.method1_status.setToolTip("需要同时填写指派给和解决方案")

        method1_layout.addWidget(method1_label)
        method1_layout.addWidget(assigned_label)
        method1_layout.addWidget(self.assigned_combo)
        method1_layout.addWidget(plus_label)
        method1_layout.addWidget(solution_label)
        method1_layout.addWidget(self.solution_combo)
        method1_layout.addWidget(self.method1_status)
        method1_layout.addStretch()

        layout.addLayout(method1_layout)

        # OR分隔符
        or_layout = QHBoxLayout()
        or_line1 = QLabel()
        or_line1.setFixedHeight(1)
        or_line1.setStyleSheet("background-color: #ff9800;")

        or_label = QLabel("OR")
        or_label.setFixedWidth(40)
        or_label.setAlignment(Qt.AlignCenter)
        or_label.setStyleSheet("""
            QLabel {
                background-color: #ff9800;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border-radius: 20px;
                padding: 6px 8px;
                margin: 0 10px;
            }
        """)

        or_line2 = QLabel()
        or_line2.setFixedHeight(1)
        or_line2.setStyleSheet("background-color: #ff9800;")

        or_layout.addWidget(or_line1, 1)
        or_layout.addWidget(or_label)
        or_layout.addWidget(or_line2, 1)
        layout.addLayout(or_layout)

        # 第三行：方式二 - Bug ID
        method2_layout = QHBoxLayout()

        # 方式二标签
        method2_label = QLabel("方式二:")
        method2_label.setFixedWidth(60)
        method2_label.setStyleSheet("font-weight: bold; color: #ff5722;")

        # Bug ID
        bug_id_label = QLabel("Bug ID:")
        bug_id_label.setFixedWidth(60)
        bug_id_label.setStyleSheet("font-weight: bold; color: #333;")

        self.bug_id_input = QLineEdit()
        self.bug_id_input.setPlaceholderText("输入具体的Bug ID，如：12345")
        self.bug_id_input.setMinimumHeight(32)
        self.bug_id_input.setFixedWidth(200)
        self.bug_id_input.textChanged.connect(self._on_query_conditions_changed)
        self.bug_id_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #ff5722;
            }
        """)

        # 方式二状态指示器
        self.method2_status = QLabel("❌")
        self.method2_status.setFixedWidth(30)
        self.method2_status.setAlignment(Qt.AlignCenter)
        self.method2_status.setToolTip("需要填写Bug ID")

        method2_layout.addWidget(method2_label)
        method2_layout.addWidget(bug_id_label)
        method2_layout.addWidget(self.bug_id_input)
        method2_layout.addWidget(self.method2_status)
        method2_layout.addStretch()

        layout.addLayout(method2_layout)

        # 分隔线
        line2 = QLabel()
        line2.setFixedHeight(1)
        line2.setStyleSheet("background-color: #e0e0e0; margin: 10px 0;")
        layout.addWidget(line2)

        # 操作按钮
        button_layout = QHBoxLayout()

        # 查询状态指示
        self.query_status_label = QLabel("❌ 请完善查询条件")
        self.query_status_label.setStyleSheet("color: #f44336; font-weight: bold; margin-right: 20px;")

        # 查询按钮
        self.query_btn = QPushButton("🔍 查询Bug列表")
        self.query_btn.setFixedHeight(40)
        self.query_btn.setFixedWidth(150)
        self.query_btn.clicked.connect(self.query_bugs)
        self.query_btn.setEnabled(False)
        self.query_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
            QPushButton:pressed:enabled {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新列表")
        self.refresh_btn.setFixedHeight(40)
        self.refresh_btn.setFixedWidth(120)
        self.refresh_btn.clicked.connect(self.refresh_bug_list)
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #1976D2;
            }
            QPushButton:pressed:enabled {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)

        # 清空条件按钮
        clear_btn = QPushButton("🗑️ 清空条件")
        clear_btn.setFixedHeight(40)
        clear_btn.setFixedWidth(120)
        clear_btn.clicked.connect(self.clear_query_conditions)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #EF6C00;
            }
        """)

        button_layout.addWidget(self.query_status_label)
        button_layout.addWidget(self.query_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addSpacing(10)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # 设置面板样式
        panel.setLayout(layout)
        panel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 10px 0 10px;
                color: #333;
                font-size: 15px;
            }
        """)

        return panel

    def _on_query_conditions_changed(self):
        """查询条件变化时的处理"""
        try:
            project_name = self.project_input.text().strip()
            assigned_to = self.assigned_combo.currentText().strip()
            solution = self.solution_combo.currentText().strip()
            bug_id = self.bug_id_input.text().strip()

            # 检查项目名称（必填）
            has_project = bool(project_name)

            # 检查方式一：指派给 + 解决方案
            method1_complete = bool(assigned_to and solution)

            # 检查方式二：Bug ID
            method2_complete = bool(bug_id)

            self.bugs_list = self._parse_bug_list(method1_complete, method2_complete)

            # 更新方式一状态指示器
            if method1_complete:
                self.method1_status.setText("✅")
                self.method1_status.setStyleSheet("color: #4caf50;")
                self.method1_status.setToolTip("方式一：条件完整")
            else:
                self.method1_status.setText("❌")
                self.method1_status.setStyleSheet("color: #f44336;")
                self.method1_status.setToolTip("需要同时填写指派给和解决方案")

            # 更新方式二状态指示器
            if method2_complete:
                self.method2_status.setText("✅")
                self.method2_status.setStyleSheet("color: #ff5722;")
                self.method2_status.setToolTip("方式二：Bug ID已填写")
            else:
                self.method2_status.setText("❌")
                self.method2_status.setStyleSheet("color: #f44336;")
                self.method2_status.setToolTip("需要填写Bug ID")

            # 判断整体查询条件是否可用
            can_query = has_project and (method1_complete or method2_complete)

            # 更新查询状态和按钮
            if not has_project:
                self.query_status_label.setText("❌ 请先填写项目名称")
                self.query_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            elif method1_complete and method2_complete:
                self.query_status_label.setText("⚠️ 两种方式都已填写，将优先使用Bug ID查询")
                self.query_status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            elif method1_complete:
                self.query_status_label.setText("✅ 方式一：可按指派给+解决方案查询")
                self.query_status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            elif method2_complete:
                self.query_status_label.setText("✅ 方式二：可按Bug ID查询")
                self.query_status_label.setStyleSheet("color: #ff5722; font-weight: bold;")
            else:
                self.query_status_label.setText("❌ 请选择一种查询方式并完善条件")
                self.query_status_label.setStyleSheet("color: #f44336; font-weight: bold;")

            # 更新按钮状态
            self.query_btn.setEnabled(can_query)
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(can_query)

            # 记录状态变化
            if hasattr(self, 'log_detailed'):
                self.log_detailed(
                    f"🔄 查询条件变化: 项目={bool(project_name)}, 方式一={method1_complete}, 方式二={method2_complete}, 可查询={can_query}",
                    "UI")

        except Exception as e:
            if hasattr(self, 'log_detailed'):
                self.log_detailed(f"❌ 查询条件检查失败: {str(e)}", "ERROR", is_error=True)

    def clear_query_conditions(self):
        """清空查询条件"""
        self.log_detailed("🗑️ 开始清空查询条件", "UI")

        try:
            self.project_input.clear()
            self.assigned_combo.setCurrentText("")
            self.solution_combo.setCurrentText("")
            self.bug_id_input.clear()

            # 清空结果列表
            if hasattr(self, 'bug_table'):
                self.bug_table.setRowCount(0)
                self.bug_count_label.setText("Bug总数: 0")

            self.log_detailed("✅ 查询条件已清空", "UI")

        except Exception as e:
            self.log_detailed(f"❌ 清空查询条件失败: {str(e)}", "ERROR", is_error=True)

    def _create_bug_list_panel(self):
        """创建BUG列表面板"""
        panel = QGroupBox("BUG列表")
        layout = QVBoxLayout()

        # BUG列表表格
        self.bug_table = QTableWidget()
        self.bug_table.setColumnCount(6)
        self.bug_table.setHorizontalHeaderLabels([
            "BUG ID", "Bug标题", "严重程度", "创建人", "指派给", "解决方案"
        ])

        # 设置表格属性
        header = self.bug_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 标题列自适应

        self.bug_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bug_table.setAlternatingRowColors(True)
        self.bug_table.setSelectionMode(QTableWidget.SingleSelection)

        # 连接选择事件
        self.bug_table.itemSelectionChanged.connect(self.on_bug_selected)

        layout.addWidget(self.bug_table)

        # 统计信息和导出按钮布局
        bottom_layout = QHBoxLayout()

        # 统计信息
        self.bug_count_label = QLabel("BUG总数: 0")
        self.bug_count_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        bottom_layout.addWidget(self.bug_count_label)

        # 导出按钮
        self.export_button = QPushButton("导出Bug列表")
        self.export_button.clicked.connect(self.export_bug_list)
        bottom_layout.addWidget(self.export_button)

        layout.addLayout(bottom_layout)

        panel.setLayout(layout)
        return panel

    def export_bug_list(self):
        """导出Bug列表"""
        self.log_detailed("📥 开始导出Bug列表...", "EXPORT")
        if not self.bug_table.rowCount():
            QMessageBox.warning(self, "警告", "没有BUG列表可供导出。")
            self.log_detailed("❌ 导出失败: BUG列表为空", "EXPORT")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "导出Bug列表", "Bug列表.csv", "CSV Files (*.csv)")
        if not file_path:
            self.log_detailed("❌ 导出操作已取消", "EXPORT")
            return

        try:
            with open(file_path, 'w', encoding='utf-8-sig') as f:
                # 写入表头
                headers = [self.bug_table.horizontalHeaderItem(i).text() for i in range(self.bug_table.columnCount())]
                f.write(','.join(headers) + '\n')

                # 写入数据
                for row in range(self.bug_table.rowCount()):
                    row_data = []
                    for col in range(self.bug_table.columnCount()):
                        item = self.bug_table.item(row, col)
                        if item:
                            data = item.text().replace(',', '，').replace('\n', ' ').strip()
                            row_data.append(data)
                        else:
                            row_data.append('')
                    f.write(','.join(row_data) + '\n')

            self.log_detailed("✅ Bug列表导出成功", "EXPORT")
            QMessageBox.information(self, "成功", f"Bug列表已成功导出到:\n{file_path}")

        except Exception as e:
            self.log_detailed(f"❌ 导出失败: {str(e)}", "ERROR", is_error=True)
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}\n请检查文件路径是否有效或文件是否被占用。")

    def _create_right_panel(self):
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout()

        # BUG详情和操作面板
        detail_panel = self._create_bug_detail_panel()
        layout.addWidget(detail_panel)

        # 操作日志
        log_panel = self._create_log_panel()
        layout.addWidget(log_panel)

        panel.setLayout(layout)
        return panel

    def _create_bug_detail_panel(self):
        """创建BUG详情和操作面板"""
        panel = QGroupBox("BUG详情与操作")
        layout = QVBoxLayout()

        # BUG详细信息
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("BUG ID:"), 0, 0)
        self.bug_id_label = QLabel("未选择")
        self.bug_id_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.bug_id_label, 0, 1)

        info_layout.addWidget(QLabel("标题:"), 1, 0)
        self.bug_title_label = QLabel("未选择")
        self.bug_title_label.setWordWrap(True)
        info_layout.addWidget(self.bug_title_label, 1, 1)

        info_layout.addWidget(QLabel("当前状态:"), 2, 0)
        self.bug_status_label = QLabel("未选择")
        info_layout.addWidget(self.bug_status_label, 2, 1)

        layout.addLayout(info_layout)

        # 操作区域
        operation_group = QGroupBox("BUG操作")
        operation_layout = QVBoxLayout()

        # 操作类型选择
        action_layout = QHBoxLayout()
        action_layout.addWidget(QLabel("操作类型:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["选择操作", "关闭BUG", "激活BUG", "解决BUG", "指派BUG"])
        self.action_combo.currentTextChanged.connect(self.on_action_changed)
        action_layout.addWidget(self.action_combo)
        operation_layout.addLayout(action_layout)

        # 备注输入
        operation_layout.addWidget(QLabel("操作备注 (将自动添加操作人姓名):"))
        self.comment_input = QTextEdit()
        self.comment_input.setMaximumHeight(100)
        self.comment_input.setPlaceholderText("请输入操作备注...")
        operation_layout.addWidget(self.comment_input)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.execute_btn = QPushButton("执行操作")
        self.execute_btn.setFixedHeight(35)
        self.execute_btn.clicked.connect(self.execute_bug_operation)
        self.execute_btn.setEnabled(False)
        button_layout.addWidget(self.execute_btn)

        self.preview_btn = QPushButton("预览操作")
        self.preview_btn.setFixedHeight(35)
        self.preview_btn.clicked.connect(self.preview_operation)
        self.preview_btn.setEnabled(False)
        button_layout.addWidget(self.preview_btn)

        operation_layout.addLayout(button_layout)

        operation_group.setLayout(operation_layout)
        layout.addWidget(operation_group)

        panel.setLayout(layout)
        return panel

    def _create_log_panel(self):
        """创建日志面板"""
        self.log_detailed("📝 创建日志面板", "UI")
        panel = QGroupBox("操作日志")
        layout = QVBoxLayout()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                border: 1px solid #ddd;
            }
        """)
        layout.addWidget(self.log_output)

        # 日志操作按钮
        log_button_layout = QHBoxLayout()

        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.clear_log)
        log_button_layout.addWidget(clear_log_btn)

        export_log_btn = QPushButton("导出日志")
        export_log_btn.clicked.connect(self.export_log)
        log_button_layout.addWidget(export_log_btn)

        log_button_layout.addStretch()
        layout.addLayout(log_button_layout)

        panel.setLayout(layout)
        self.log_detailed("✅ 日志面板创建完成", "UI")
        return panel

    def set_user_info(self, user_info):
        """设置当前登录用户信息"""
        self.log_detailed("👤 开始设置用户信息", "USER")

        self.user_info = user_info
        if user_info:
            self.log_detailed(f"📋 用户信息: 姓名={user_info.real_name}, 账号={user_info.account}", "USER")
            self.operator_label.setText(f"操作人: {user_info.real_name} ({user_info.account})")
            self.permission_status.setText("已登录：有权限，可操作项目BUG")
            self.permission_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

            # 检查管理员配置状态
            self.log_detailed("🔧 更新管理员配置状态", "USER")
            self._update_admin_status()

            self.log_detailed(f"✅ 操作人设置成功: {user_info.real_name}", "USER")
        else:
            self.log_detailed("⚠️ 用户信息为空，设置为未登录状态", "USER")
            self.operator_label.setText("操作人: 未登录")
            self.permission_status.setText("权限: 请先登录")
            self.permission_status.setStyleSheet("color: #999;")
            self._disable_all_operations()

    def _update_admin_status(self):
        """更新管理员配置状态"""
        self.log_detailed("🔄 检查管理员配置状态", "CONFIG")

        if self.manager_account and self.manager_password:
            self.log_detailed(f"✅ 管理员配置完整: 账号={self.manager_account}", "CONFIG")
            self.admin_status.setText("管理员配置: 已配置")
            self.admin_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

            # 启用查询功能
            if self.user_info:
                self.log_detailed("🚀 启用查询和刷新功能", "CONFIG")
                self.query_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
            else:
                self.log_detailed("⚠️ 用户未登录，无法启用查询功能", "CONFIG")
        else:
            self.log_detailed("❌ 管理员配置不完整，禁用操作", "CONFIG")
            self.admin_status.setText("管理员配置: 未配置")
            self.admin_status.setStyleSheet("color: #FF5722; font-weight: bold;")
            self._disable_all_operations()

    def _disable_all_operations(self):
        """禁用所有操作"""
        self.log_detailed("🔒 禁用所有操作按钮", "UI")
        self.query_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)

    def _show_admin_config_dialog(self):
        """显示管理员配置对话框"""
        self.log_detailed("⚙️ 显示管理员配置对话框", "CONFIG")

        dialog = AdminConfigDialog(self.manager_account, self.manager_password, self)
        if dialog.exec_() == dialog.Accepted:
            username, password = dialog.get_config()
            if username and password:
                self.log_detailed(f"✅ 管理员配置已更新: 账号={username}", "CONFIG")
                self.manager_account = username
                self.manager_password = password
                self._save_admin_config()
                self._update_admin_status()
                self.log_detailed("✅ 管理员配置已保存并更新UI", "CONFIG")
            else:
                self.log_detailed("❌ 配置无效: 用户名或密码为空", "CONFIG", is_error=True)
                QMessageBox.warning(self, "配置错误", "用户名和密码不能为空")
        else:
            self.log_detailed("❌ 用户取消了配置", "CONFIG")

    def _save_admin_config(self):
        """保存管理员配置"""
        self.log_detailed("💾 开始保存管理员配置", "CONFIG")

        try:
            config = configparser.ConfigParser()
            config_dir = os.path.join(os.getcwd(), "config")
            config_path = os.path.join(config_dir, "admin_account.ini")

            self.log_detailed(f"📁 保存路径: {config_path}", "CONFIG")

            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                self.log_detailed("✅ 配置目录创建成功", "CONFIG")

            config['admin'] = {
                'username': self.manager_account,
                'password': self.manager_password
            }
            config['security'] = {
                'encrypted': 'false',
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            config['permissions'] = {
                'allowed_operations': 'bug_query,bug_edit,bug_close,bug_activate',
                'max_session_duration': '3600'
            }

            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)

            self.log_detailed("✅ 管理员配置保存成功", "CONFIG")

        except Exception as e:
            self.log_detailed(f"❌ 保存管理员配置失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)

    def query_bugs(self):
        """查询Bug列表 - 支持两种查询方式"""
        self.log_detailed("🔍 开始Bug查询流程", "QUERY", clear=True)

        if not self._check_operation_permission():
            return

        # 获取基本参数
        project_name = self.project_input.text().strip()
        bug_id = self.bug_id_input.text().strip()
        assigned_to = self.assigned_combo.currentText().strip()
        solution = self.solution_combo.currentText().strip()

        # 验证项目名称
        if not project_name:
            self.log_detailed("❌ 查询失败: 项目名称为空", "QUERY", is_error=True)
            QMessageBox.warning(self, "参数错误", "请先输入项目名称")
            return

        # 确定查询方式和参数
        if bug_id:
            # 方式二：优先使用Bug ID查询
            self.log_detailed(f"🎯 使用方式二：Bug ID查询 - ID: {bug_id}, 项目: {project_name}", "QUERY")
            query_params = {
                'query_type': 'by_id',
                'project_name': project_name,
                'bug_id': bug_id
            }
        elif assigned_to and solution:
            # 方式一：指派给 + 解决方案查询
            self.log_detailed(
                f"🎯 使用方式一：条件查询 - 项目: {project_name}, 指派给: {assigned_to}, 解决方案: {solution}", "QUERY")
            query_params = {
                'query_type': 'by_conditions',
                'project_name': project_name,
                'assigned_to': assigned_to,
                'solution': solution
            }
        else:
            self.log_detailed("❌ 查询失败: 查询条件不完整", "QUERY", is_error=True)
            QMessageBox.warning(self, "查询条件不完整",
                                "请选择一种查询方式并完善所有条件：\n\n方式一：指派给 + 解决方案\n方式二：Bug ID")
            return

        self.log_detailed(f"📋 完整查询参数: {query_params}", "QUERY")
        self.log_detailed("🔒 禁用查询按钮，防止重复查询", "QUERY")
        self.query_btn.setEnabled(False)

        # 创建Bug操作工作线程
        self.log_detailed("🔧 创建Bug操作工作线程", "WORKER")
        try:
            self.bug_operator_worker = BugOperatorWorker(
                manager_account=self.manager_account,
                manager_password=self.manager_password,
                operator_name=self.user_info.real_name,
                operation_type='query',
                query_params=query_params
            )
            self.log_detailed("✅ 工作线程创建成功", "WORKER")
        except Exception as e:
            self.log_detailed(f"❌ 创建工作线程失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)
            self.query_btn.setEnabled(True)
            return

        # 连接信号
        self.log_detailed("🔗 连接工作线程信号", "WORKER")
        self.bug_operator_worker.log_signal.connect(self._on_worker_log)
        self.bug_operator_worker.bugs_data_signal.connect(self.display_bugs)
        self.bug_operator_worker.finished_signal.connect(self.on_query_finished)

        # 启动工作线程
        self.log_detailed("🚀 启动工作线程开始查询", "WORKER")
        self.bug_operator_worker.start()

    def _on_worker_log(self, message, is_error=False):
        """处理工作线程的日志"""
        level = "ERROR" if is_error else "WORKER"
        self.log_detailed(message, level, is_error=is_error)

    def _check_operation_permission(self):
        """检查操作权限"""
        self.log_detailed("🔐 开始检查操作权限", "PERMISSION")

        if not self.user_info:
            self.log_detailed("❌ 权限检查失败: 用户未登录", "PERMISSION", is_error=True)
            QMessageBox.warning(self, "权限不足", "请先在主页面登录禅道系统")
            return False

        self.log_detailed(f"✅ 用户权限检查通过: {self.user_info.real_name}", "PERMISSION")

        if not self.manager_account or not self.manager_password:
            self.log_detailed("❌ 权限检查失败: 管理员配置不完整", "PERMISSION", is_error=True)
            QMessageBox.warning(self, "配置错误", "请先配置管理员账号")
            return False

        self.log_detailed("✅ 管理员配置检查通过", "PERMISSION")
        self.log_detailed("✅ 所有权限检查通过", "PERMISSION")
        return True

    def _get_status_value(self):
        """获取状态值 - 更新为支持新的查询逻辑"""
        # 优先检查BUG ID查询
        bug_id = self.bug_id_input.text().strip()
        if bug_id:
            self.log_detailed(f"📊 使用BUG ID查询: {bug_id}", "QUERY")
            return "by_id"

        # 否则使用指派给条件
        assigned_text = self.assigned_combo.currentText()
        if assigned_text and assigned_text != "全部":
            self.log_detailed(f"📊 指派给查询: {assigned_text}", "QUERY")
            return "by_assigned"

        # 默认返回全部
        self.log_detailed("📊 使用全部状态查询", "QUERY")
        return "all"

    def _get_severity_value(self):
        """获取严重程度值 - 更新为支持解决方案查询"""
        # 优先检查BUG ID查询
        bug_id = self.bug_id_input.text().strip()
        if bug_id:
            return "by_id"

        # 否则使用解决方案条件
        solution_text = self.solution_combo.currentText()
        if solution_text and solution_text != "全部":
            self.log_detailed(f"📊 解决方案查询: {solution_text}", "QUERY")
            return "by_solution"

        # 默认返回全部
        self.log_detailed("📊 使用全部解决方案查询", "QUERY")
        return "all"

    def display_bugs(self, bugs_data):
        """显示BUG数据"""
        self.log_detailed(f"📋 开始显示BUG数据，共{len(bugs_data)}条记录", "DISPLAY")

        try:
            self.current_bugs = bugs_data
            self.bug_table.setRowCount(len(bugs_data))

            self.log_detailed("🔄 开始填充表格数据", "DISPLAY")

            for row, bug in enumerate(bugs_data):
                try:
                    # 填充基本信息
                    bug_id = str(bug.get('id', ''))
                    title = bug.get('title', '')
                    status = bug.get('status', '')
                    # severity = bug.get('severity', '')
                    opened_by = bug.get('opened_by', '')
                    assigned_to = bug.get('assigned_to', '')
                    solution = bug.get('solution', '')

                    self.bug_table.setItem(row, 0, QTableWidgetItem(bug_id))
                    self.bug_table.setItem(row, 1, QTableWidgetItem(title))

                    # 状态着色
                    status_item = QTableWidgetItem(status)
                    if status == '激活':
                        status_item.setBackground(Qt.red)
                        self.log_detailed(f"🔴 BUG {bug_id} 状态为激活，设置红色背景", "DISPLAY")
                    elif status == '已解决':
                        status_item.setBackground(Qt.yellow)
                        self.log_detailed(f"🟡 BUG {bug_id} 状态为已解决，设置黄色背景", "DISPLAY")
                    elif status == '已关闭':
                        status_item.setBackground(Qt.green)
                        self.log_detailed(f"🟢 BUG {bug_id} 状态为已关闭，设置绿色背景", "DISPLAY")

                    self.bug_table.setItem(row, 2, status_item)
                    # self.bug_table.setItem(row, 3, QTableWidgetItem(severity))
                    self.bug_table.setItem(row, 3, QTableWidgetItem(opened_by))
                    self.bug_table.setItem(row, 4, QTableWidgetItem(assigned_to))
                    self.bug_table.setItem(row, 5, QTableWidgetItem(solution))

                    if row < 3:  # 只记录前3条详细信息避免日志过多
                        self.log_detailed(f"📄 第{row + 1}行数据: ID={bug_id}, 标题={title[:20]}..., 状态={status}",
                                          "DISPLAY")

                except Exception as e:
                    self.log_detailed(f"❌ 填充第{row + 1}行数据失败: {str(e)}", "ERROR", is_error=True)
                    continue

            self.bug_count_label.setText(f"BUG总数: {len(bugs_data)}")
            self.log_detailed(f"✅ 表格数据显示完成，总计 {len(bugs_data)} 个BUG", "DISPLAY")

        except Exception as e:
            self.log_detailed(f"❌ 显示BUG数据失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)

    def on_bug_selected(self):
        """BUG选择事件处理"""
        try:
            current_row = self.bug_table.currentRow()
            self.log_detailed(f"🖱️ 用户选择了第{current_row + 1}行BUG", "SELECTION")

            if current_row >= 0 and current_row < len(self.current_bugs):
                bug = self.current_bugs[current_row]
                bug_id = bug.get('id', '')
                title = bug.get('title', '')
                status = bug.get('status', '')

                self.log_detailed(f"📋 选择的BUG详情: ID={bug_id}, 标题={title[:30]}..., 状态={status}", "SELECTION")

                # 更新详情显示
                self.bug_id_label.setText(str(bug_id))
                self.bug_title_label.setText(title)
                self.bug_status_label.setText(status)

                # 启用操作按钮
                self.preview_btn.setEnabled(True)
                self.log_detailed("✅ 已启用预览操作按钮", "SELECTION")

                self.log_detailed(f"✅ BUG选择处理完成: {bug_id}", "SELECTION")
            else:
                self.log_detailed(f"❌ 选择的行索引无效: {current_row}, 总行数: {len(self.current_bugs)}", "SELECTION",
                                  is_error=True)

        except Exception as e:
            self.log_detailed(f"❌ BUG选择处理失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)

    def on_action_changed(self):
        """操作类型改变处理"""
        action = self.action_combo.currentText()
        self.log_detailed(f"⚙️ 操作类型改变为: {action}", "OPERATION")

        if action != "选择操作":
            self.execute_btn.setEnabled(True)
            self.log_detailed("✅ 已启用执行操作按钮", "OPERATION")
        else:
            self.execute_btn.setEnabled(False)
            self.log_detailed("🔒 已禁用执行操作按钮", "OPERATION")

    def preview_operation(self):
        """预览操作"""
        self.log_detailed("👁️ 开始预览操作", "PREVIEW")

        try:
            current_row = self.bug_table.currentRow()
            if current_row < 0:
                self.log_detailed("❌ 预览失败: 未选择BUG", "PREVIEW", is_error=True)
                QMessageBox.warning(self, "未选择BUG", "请先选择要操作的BUG")
                return

            bug = self.current_bugs[current_row]
            action = self.action_combo.currentText()
            comment = self.comment_input.toPlainText().strip()

            self.log_detailed(f"📋 预览参数: BUG ID={bug.get('id')}, 操作={action}, 备注长度={len(comment)}", "PREVIEW")

            # 自动添加操作人姓名到备注
            final_comment = self._prepare_comment(comment)
            self.log_detailed(f"📝 处理后的备注: {final_comment[:50]}...", "PREVIEW")

            preview_text = f"""操作预览:
---------
BUG ID: {bug.get('id')}
BUG标题: {bug.get('title')}
当前状态: {bug.get('status')}
操作类型: {action}
操作人: {self.user_info.real_name if self.user_info else '未知'}
操作备注: {final_comment}
操作时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """

            self.log_detailed("✅ 预览信息生成完成，显示对话框", "PREVIEW")
            QMessageBox.information(self, "操作预览", preview_text.strip())

        except Exception as e:
            self.log_detailed(f"❌ 操作预览失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)

    def _prepare_comment(self, comment):
        """准备备注内容，自动添加操作人姓名"""
        if not self.user_info:
            self.log_detailed("⚠️ 用户信息为空，无法添加操作人姓名", "COMMENT")
            return comment

        operator_name = self.user_info.real_name
        self.log_detailed(f"👤 操作人: {operator_name}", "COMMENT")

        if operator_name not in comment:
            if comment.strip():
                result = f"[操作人: {operator_name}] {comment.strip()}"
                self.log_detailed("✅ 已在现有备注前添加操作人信息", "COMMENT")
            else:
                result = f"[操作人: {operator_name}] 执行{self.action_combo.currentText()}操作"
                self.log_detailed("✅ 已生成默认操作备注", "COMMENT")
        else:
            result = comment
            self.log_detailed("ℹ️ 备注中已包含操作人信息，无需添加", "COMMENT")

        return result

    def execute_bug_operation(self):
        """执行BUG操作"""
        self.log_detailed("🚀 开始执行BUG操作", "EXECUTE")

        if not self._check_operation_permission():
            return

        try:
            current_row = self.bug_table.currentRow()
            if current_row < 0:
                self.log_detailed("❌ 执行失败: 未选择BUG", "EXECUTE", is_error=True)
                QMessageBox.warning(self, "未选择BUG", "请先选择要操作的BUG")
                return

            action = self.action_combo.currentText()
            if action == "选择操作":
                self.log_detailed("❌ 执行失败: 未选择操作类型", "EXECUTE", is_error=True)
                QMessageBox.warning(self, "未选择操作", "请选择要执行的操作类型")
                return

            bug = self.current_bugs[current_row]
            comment = self.comment_input.toPlainText().strip()

            self.log_detailed(f"📋 操作参数: BUG ID={bug.get('id')}, 操作类型={action}", "EXECUTE")

            # 自动添加操作人姓名到备注
            final_comment = self._prepare_comment(comment)

            # 确认操作
            self.log_detailed("❓ 显示操作确认对话框", "EXECUTE")
            reply = QMessageBox.question(
                self, "确认操作",
                f"确定要对BUG {bug.get('id')} 执行 {action} 操作吗？\n\n备注: {final_comment}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                self.log_detailed("❌ 用户取消了操作", "EXECUTE")
                return

            self.log_detailed("✅ 用户确认操作，开始执行", "EXECUTE")
            self.log_detailed("🔒 禁用执行按钮，防止重复操作", "EXECUTE")
            self.execute_btn.setEnabled(False)

            # 准备操作参数
            operation_params = {
                'bug_id': bug.get('id'),
                'action': action,
                'comment': final_comment,
                'operator': self.user_info.real_name
            }

            self.log_detailed(f"📦 完整操作参数: {operation_params}", "EXECUTE")

            # 创建操作工作线程
            self.log_detailed("🔧 创建操作工作线程", "WORKER")
            self.bug_operator_worker = BugOperatorWorker(
                manager_account=self.manager_account,
                manager_password=self.manager_password,
                operator_name=self.user_info.real_name,
                operation_type='execute',
                operation_params=operation_params
            )
            self.log_detailed("✅ 操作工作线程创建成功", "WORKER")

            # 连接信号
            self.log_detailed("🔗 连接操作工作线程信号", "WORKER")
            self.bug_operator_worker.log_signal.connect(self._on_worker_log)
            self.bug_operator_worker.operation_result_signal.connect(self.on_operation_result)
            self.bug_operator_worker.finished_signal.connect(self.on_operation_finished)

            # 启动工作线程
            self.log_detailed("🚀 启动操作工作线程", "WORKER")
            self.bug_operator_worker.start()

        except Exception as e:
            self.log_detailed(f"❌ 执行BUG操作失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)
            self.execute_btn.setEnabled(True)

    def on_operation_result(self, success, message):
        """操作结果处理"""
        if success:
            self.log_detailed(f"✅ 操作成功: {message}", "RESULT")
            QMessageBox.information(self, "操作成功", message)

            # 清空备注和重置操作类型
            self.log_detailed("🔄 清空备注和重置操作类型", "RESULT")
            self.comment_input.clear()
            self.action_combo.setCurrentIndex(0)

            # 自动刷新列表
            self.log_detailed("⏰ 2秒后自动刷新BUG列表", "RESULT")
            QTimer.singleShot(2000, self.refresh_bug_list)

        else:
            self.log_detailed(f"❌ 操作失败: {message}", "RESULT", is_error=True)
            QMessageBox.critical(self, "操作失败", message)

    def on_operation_finished(self, success, message):
        """操作完成处理"""
        status = "成功" if success else "失败"
        self.log_detailed(f"🏁 操作完成: {status} - {message}", "RESULT", is_error=not success)
        self.log_detailed("🔓 重新启用执行按钮", "RESULT")
        self.execute_btn.setEnabled(True)

    def refresh_bug_list(self):
        """刷新BUG列表"""
        self.log_detailed("🔄 请求刷新BUG列表", "REFRESH")

        if self.project_input.text().strip():
            self.log_detailed("✅ 项目名称存在，开始重新查询", "REFRESH")
            self.query_bugs()
        else:
            self.log_detailed("❌ 刷新失败: 项目名称为空", "REFRESH", is_error=True)

    def on_query_finished(self, success, message):
        """查询完成处理"""
        status = "成功" if success else "失败"
        self.log_detailed(f"🏁 查询完成: {status} - {message}", "QUERY", is_error=not success)
        self.log_detailed("🔓 重新启用查询按钮", "QUERY")
        self.query_btn.setEnabled(True)

        if not success:
            QMessageBox.critical(self, "查询失败", message)

    def clear_log(self):
        """清空日志"""
        self.log_output.clear()
        self.log_detailed("🗑️ 日志已清空", "LOG")

    def export_log(self):
        """导出日志"""
        self.log_detailed("📤 开始导出日志", "EXPORT")

        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出日志",
                f"bug_operation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt);;All Files (*)"
            )

            if file_path:
                self.log_detailed(f"📁 导出路径: {file_path}", "EXPORT")

                log_content = self.log_output.toPlainText()
                self.log_detailed(f"📄 日志内容长度: {len(log_content)} 字符", "EXPORT")

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)

                self.log_detailed(f"✅ 日志导出成功: {file_path}", "EXPORT")
                QMessageBox.information(self, "导出成功", f"日志已保存到:\n{file_path}")
            else:
                self.log_detailed("❌ 用户取消了导出", "EXPORT")

        except Exception as e:
            self.log_detailed(f"❌ 导出日志失败: {str(e)}", "ERROR", is_error=True)
            self.log_detailed(f"📋 错误详情: {traceback.format_exc()}", "ERROR", is_error=True)
            QMessageBox.critical(self, "导出失败", f"导出日志失败:\n{e}")

    def log(self, message, is_error=False, clear=False):
        """添加日志"""
        if clear:
            self.log_output.clear()

        timestamp = datetime.now().strftime("[%H:%M:%S]")
        formatted_message = f"{timestamp} {message}"

        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.End)

        # 设置文本格式
        format = cursor.charFormat()
        if is_error:
            format.setForeground(Qt.red)
        else:
            format.setForeground(Qt.black)
        cursor.setCharFormat(format)

        self.log_output.append(formatted_message)
        self.log_output.ensureCursorVisible()

    def save_settings(self):
        """保存设置 - 更新为新的查询条件"""
        self.log_detailed("💾 开始保存用户设置", "SETTINGS")

        try:
            settings = {
                "project_name": self.project_input.text(),
                "assigned_to": self.assigned_combo.currentText(),
                "solution": self.solution_combo.currentText(),
                "bug_id": self.bug_id_input.text()
            }

            self.log_detailed(f"📋 保存的设置: {settings}", "SETTINGS")
            self.settings_manager.save_settings("bug_query", settings, self.log)
            self.log_detailed("✅ 用户设置保存成功", "SETTINGS")

        except Exception as e:
            self.log_detailed(f"❌ 保存设置失败: {str(e)}", "ERROR", is_error=True)

    def load_settings(self):
        """加载设置 - 更新为新的查询条件"""
        self.log_detailed("📖 开始加载用户设置", "SETTINGS")

        try:
            default_settings = {
                "project_name": "",
                "assigned_to": "全部",
                "solution": "全部",
                "bug_id": ""
            }

            loaded_settings = self.settings_manager.load_settings(
                "bug_query", default_settings, self.log
            )

            self.log_detailed(f"📋 加载的设置: {loaded_settings}", "SETTINGS")

            # 应用设置
            self.project_input.setText(loaded_settings.get("project_name", ""))
            self.bug_id_input.setText(loaded_settings.get("bug_id", ""))

            # 设置下拉框选项
            assigned_to = loaded_settings.get("assigned_to", "全部")
            index = self.assigned_combo.findText(assigned_to)
            if index >= 0:
                self.assigned_combo.setCurrentIndex(index)
                self.log_detailed(f"📊 设置指派给选择: {assigned_to}", "SETTINGS")

            solution = loaded_settings.get("solution", "全部")
            index = self.solution_combo.findText(solution)
            if index >= 0:
                self.solution_combo.setCurrentIndex(index)
                self.log_detailed(f"📊 设置解决方案选择: {solution}", "SETTINGS")

            self.log_detailed("✅ 用户设置加载完成", "SETTINGS")

        except Exception as e:
            self.log_detailed(f"❌ 加载设置失败: {str(e)}", "ERROR", is_error=True)

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.log_detailed("🚪 窗口关闭事件触发", "CLOSE")

        try:
            if self.bug_operator_worker and self.bug_operator_worker.isRunning():
                self.log_detailed("🛑 检测到工作线程运行中，开始终止", "CLOSE")
                self.bug_operator_worker.terminate()
                wait_result = self.bug_operator_worker.wait(3000)
                if wait_result:
                    self.log_detailed("✅ 工作线程已正常终止", "CLOSE")
                else:
                    self.log_detailed("⚠️ 工作线程终止超时", "CLOSE")

            self.save_settings()
            self.log_detailed("✅ 窗口关闭处理完成", "CLOSE")

        except Exception as e:
            self.log_detailed(f"❌ 窗口关闭处理失败: {str(e)}", "ERROR", is_error=True)

        event.accept()
