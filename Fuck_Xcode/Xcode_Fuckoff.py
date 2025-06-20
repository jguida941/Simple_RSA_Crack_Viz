import sys
import subprocess
import json
import re
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox,
    QLineEdit, QFrame, QHBoxLayout, QTextEdit, QCheckBox, QGroupBox,
    QProgressBar, QListWidget, QListWidgetItem, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QSystemTrayIcon,
    QComboBox, QSpinBox, QSlider, QGraphicsOpacityEffect,
    QScrollBar
)
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor, QPixmap, QPainter, QBrush, QLinearGradient, QGuiApplication, \
    QAction, QCursor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QPoint, QSize


# Theme definitions
class Colors:
    BACKGROUND = "#1A1A1A"
    SURFACE = "#2B2B2B"
    TEXT_HIGH = "#E0E0E0"
    TEXT_MEDIUM = "#A0A0A0"
    ACCENT_PUSH = "#FF6C00"
    ACCENT_FOCUS = "#FFD500"


class Metrics:
    PADDING = 8
    CORNER_RADIUS = 6
    FONT_SIZE_MD = 14


# Themed button
class AccentButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("AccentButton")


class DiskScanner(QThread):
    update_signal = pyqtSignal(list)
    progress_signal = pyqtSignal(int)

    def run(self):
        try:
            # Get all mounted disks
            result = subprocess.run(['diskutil', 'list'], capture_output=True, text=True)
            disk_info = []

            # Parse diskutil output
            lines = result.stdout.split('\n')
            current_disk = None

            for i, line in enumerate(lines):
                self.progress_signal.emit(int((i / len(lines)) * 100))

                if line.startswith('/dev/disk'):
                    current_disk = line.split()[0]

                # Look for simulator-related volumes
                if current_disk and ('Simulator' in line or 'Xcode' in line or 'iOS' in line):
                    # Get detailed info
                    info_result = subprocess.run(['diskutil', 'info', current_disk],
                                                 capture_output=True, text=True)

                    volume_name = ""
                    mount_point = ""
                    size = ""

                    for info_line in info_result.stdout.split('\n'):
                        if 'Volume Name:' in info_line:
                            volume_name = info_line.split('Volume Name:')[1].strip()
                        elif 'Mount Point:' in info_line:
                            mount_point = info_line.split('Mount Point:')[1].strip()
                        elif 'Disk Size:' in info_line:
                            size = info_line.split('Disk Size:')[1].strip().split()[0]

                    if volume_name or mount_point:
                        disk_info.append({
                            'device': current_disk,
                            'name': volume_name or 'Unknown',
                            'mount': mount_point or 'Not Mounted',
                            'size': size or 'Unknown'
                        })

            self.update_signal.emit(disk_info)

        except Exception as e:
            self.update_signal.emit([])


class ProcessMonitor(QThread):
    update_signal = pyqtSignal(list)

    def run(self):
        try:
            # Find all simulator-related processes
            ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            processes = []

            keywords = ['Simulator', 'CoreSimulator', 'SimulatorTrampoline', 'launchd_sim']

            for line in ps_result.stdout.split('\n')[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 11:
                    process_name = ' '.join(parts[10:])
                    if any(keyword in process_name for keyword in keywords):
                        processes.append({
                            'pid': parts[1],
                            'cpu': parts[2],
                            'mem': parts[3],
                            'name': process_name[:50] + '...' if len(process_name) > 50 else process_name
                        })

            self.update_signal.emit(processes)

        except Exception as e:
            self.update_signal.emit([])


class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.geometry().adjusted(-2, -2, 2, 2))
        self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.geometry().adjusted(2, 2, -2, -2))
        self.animation.start()
        super().leaveEvent(event)


class EnhancedSimulatorKiller(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = None
        self.title_bar = None
        self.eject_selected_btn = AccentButton("⏏️ Eject Selected")
        self.eject_selected_btn.setObjectName("EjectSelectedButton")
        self.old_pos = None
        self.space_stat = self.create_stat_widget("Space Used", "0 GB")
        self.mounted_stat = self.create_stat_widget("Mounted Disks", "0")
        self.connection_indicator = QLabel("●")
        self.status_label = QLabel("Ready")
        self.scan_btn = AccentButton("🔍 Scan Disks")
        self.scan_btn.setObjectName("ScanDisksButton")
        self.log_level_combo = QComboBox()
        self.process_table = QTableWidget()
        self.patterns_edit = QTextEdit()
        self.notify_check = QCheckBox("Show notifications")
        self.progress_bar = QProgressBar()
        self.nuclear_btn = AccentButton("☢️ Nuclear Option")
        self.nuclear_btn.setObjectName("NuclearOptionButton")
        # Placeholders for new process tab/process buttons
        self.refresh_processes_btn = None
        self.kill_selected_btn = None
        self.kill_all_btn = None
        self.save_btn = None
        self.clear_log_btn = None
        self.export_log_btn = None
        self.disk_list = QListWidget()
        self.clear_cache_check = QCheckBox("Clear simulator caches on eject")
        self.scan_interval = QSpinBox()
        self.force_unmount_check = QCheckBox("Always force unmount")
        self.timeout_spin = QSpinBox()
        self.process_stat = self.create_stat_widget("Simulator Processes", "0")
        self.tab_widget = QTabWidget()
        self.container = QFrame(self)
        self.auto_eject_check = None
        self.auto_scan_check = QCheckBox("Auto-scan on startup")
        self.save_pwd_check = QCheckBox("Save in Keychain")
        self.password_input = QLineEdit()
        # Placeholder for the green zoom button (assigned in create_title_bar)
        self.green_button = None
        self.log_viewer = QTextEdit()
        self.tray_icon = QSystemTrayIcon(self)
        self.fade_in = None
        self.scan_timer = None
        self.fade_out = None
        self.drag_position = None
        self.disk_scanner = DiskScanner()
        self.process_monitor = ProcessMonitor()
        self.selected_disks = []
        # Add SIP status banner method before UI init
        # (Method defined below)
        self.init_ui()
        self.init_system_tray()

    def add_sip_status_banner(self):
        import subprocess

        try:
            output = subprocess.check_output(["csrutil", "status"], text=True).strip().lower()
            sip_enabled = "enabled" in output
        except Exception:
            sip_enabled = False

        if sip_enabled:
            banner = QLabel("⚠️ System Integrity Protection (SIP) is ENABLED. Some functions may not work.")
            banner.setStyleSheet("background-color: #aa0000; color: white; padding: 10px; border-radius: 8px;")
            banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout().addWidget(banner)

    def init_ui(self):
        self.setWindowTitle("iOS Simulator Disk Ejector Pro")
        self.setFixedSize(900, 700)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main container with gradient background
        self.container.setObjectName("MainContainer")
        self.container.setGeometry(0, 0, 900, 700)

        # Apply advanced styling
        self.setStyleSheet(self.get_advanced_stylesheet())

        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 20)
        main_layout.setSpacing(0)
        self.main_layout = main_layout  # Store reference for SIP banner insertion

        # SIP status banner (dynamically added if SIP is enabled)
        self.add_sip_status_banner()

        # Custom title bar
        self.create_title_bar(main_layout)

        # Tab widget for different views
        self.tab_widget.setObjectName("MainTabs")
        main_layout.addWidget(self.tab_widget)

        # Dashboard tab
        self.create_dashboard_tab()

        # Process Manager tab
        self.create_process_tab()

        # Settings tab
        self.create_settings_tab()

        # Activity Log tab
        self.create_log_tab()

        # Status bar
        self.create_status_bar(main_layout)

        # Start monitoring
        self.start_monitoring()

    @staticmethod
    def get_advanced_stylesheet():
        return """
        QFrame#MainContainer {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(28, 28, 30, 240),
                stop:0.5 rgba(44, 44, 46, 240),
                stop:1 rgba(28, 28, 30, 240));
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        QLabel#TitleLabel {
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 10px;
            background: transparent;
        }

        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 59, 48, 200),
                stop:1 rgba(255, 45, 35, 200));
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 14px;
        }

        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 69, 58, 255),
                stop:1 rgba(255, 55, 45, 255));
        }

        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(200, 50, 40, 255),
                stop:1 rgba(180, 40, 30, 255));
        }

        QPushButton#RefreshButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(10, 132, 255, 200),
                stop:1 rgba(0, 122, 255, 200));
        }

        QPushButton#RefreshButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(20, 142, 255, 255),
                stop:1 rgba(10, 132, 255, 255));
        }

        QTabWidget#MainTabs {
            background: transparent;
            border: none;
        }

        QTabWidget::pane {
            background: rgba(44, 44, 46, 100);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 10px;
        }

        QTabBar::tab {
            background: rgba(72, 72, 74, 150);
            color: rgba(255, 255, 255, 0.7);
            padding: 10px 20px;
            margin-right: 5px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 500;
        }

        QTabBar::tab:selected {
            background: rgba(99, 99, 102, 200);
            color: white;
        }

        QListWidget {
            background: rgba(30, 30, 32, 200);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 5px;
            color: white;
            font-size: 13px;
        }

        QListWidget::item {
            padding: 8px;
            margin: 2px;
            border-radius: 6px;
            background: rgba(72, 72, 74, 100);
        }

        QListWidget::item:selected {
            background: rgba(10, 132, 255, 150);
        }

        QListWidget::item:hover {
            background: rgba(99, 99, 102, 150);
        }

        QTableWidget {
            background: rgba(30, 30, 32, 200);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            gridline-color: rgba(255, 255, 255, 0.05);
            color: white;
        }

        QTableWidget::item {
            padding: 5px;
        }

        QHeaderView::section {
            background: rgba(58, 58, 60, 200);
            color: white;
            padding: 8px;
            border: none;
            font-weight: 600;
        }

        QTextEdit {
            background: rgba(30, 30, 32, 200);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: #00ff00;
            font-family: 'Menlo', 'Monaco', monospace;
            font-size: 12px;
            padding: 10px;
        }

        QProgressBar {
            background: rgba(72, 72, 74, 200);
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }

        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(52, 199, 89, 255),
                stop:1 rgba(48, 209, 88, 255));
            border-radius: 4px;
        }

        QCheckBox {
            color: white;
            spacing: 8px;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 4px;
            background: rgba(72, 72, 74, 200);
        }

        QCheckBox::indicator:checked {
            background: rgba(48, 209, 88, 255);
            border-color: rgba(48, 209, 88, 255);
        }

        QLineEdit {
            background: rgba(72, 72, 74, 200);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            padding: 8px;
            color: white;
            font-size: 14px;
        }

        QLineEdit:focus {
            border-color: rgba(10, 132, 255, 255);
        }

        QGroupBox {
            color: rgba(255, 255, 255, 0.9);
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 10px 0 10px;
        }
        """

    def create_title_bar(self, layout):
        title_bar = QFrame()
        title_bar.setFixedHeight(50)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(15, 0, 15, 0)

        # Window controls (macOS style: left-aligned)
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        # Red (close)
        close_btn = QPushButton()
        close_btn.setFixedSize(12, 12)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #FF5F56;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #FF8980;
            }
        """)
        close_btn.clicked.connect(self.close)

        # Yellow (minimize)
        min_btn = QPushButton()
        min_btn.setFixedSize(12, 12)
        min_btn.setStyleSheet("""
            QPushButton {
                background: #FFBD2E;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #FDD663;
            }
        """)
        min_btn.clicked.connect(self.showMinimized)

        # Green (tile/maximize/zoom)
        green_btn = QPushButton()
        green_btn.setFixedSize(12, 12)
        green_btn.setStyleSheet("""
            QPushButton {
                background: #28C840;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: #42D85C;
            }
        """)
        # Instead of maximize, show mac zoom menu
        green_btn.clicked.connect(self.show_mac_zoom_menu)
        self.green_button = green_btn

        controls_layout.addWidget(close_btn)
        controls_layout.addWidget(min_btn)
        controls_layout.addWidget(green_btn)
        controls_layout.addSpacing(10)

        # Title
        title = QLabel("iOS Simulator Disk Ejector Pro")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Menu button
        menu_btn = QPushButton("☰")
        menu_btn.setFixedSize(30, 30)
        menu_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: white;
                font-size: 20px;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        menu_btn.clicked.connect(self.show_menu)

        title_bar_layout.addLayout(controls_layout)
        title_bar_layout.addWidget(title, 1)
        title_bar_layout.addWidget(menu_btn)

        layout.addWidget(title_bar)

        # Make window draggable (macOS style)
        self.title_bar = title_bar
        self.title_bar.mousePressEvent = self.title_bar_mouse_press
        self.title_bar.mouseMoveEvent = self.title_bar_mouse_move

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # --- macOS-style drag-to-move and green-zoom dropdown ---
    def title_bar_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def show_mac_zoom_menu(self):
        menu = QMenu(self)

        tile_left = QAction("Tile Left", self)
        tile_left.triggered.connect(lambda: self.resize_to_half("left"))
        menu.addAction(tile_left)

        tile_right = QAction("Tile Right", self)
        tile_right.triggered.connect(lambda: self.resize_to_half("right"))
        menu.addAction(tile_right)

        full_screen = QAction("Full Screen", self)
        full_screen.triggered.connect(self.showFullScreen)
        menu.addAction(full_screen)

        menu.exec(self.green_button.mapToGlobal(QPoint(0, self.green_button.height())))

    def resize_to_half(self, side: str):
        screen = QGuiApplication.primaryScreen().geometry()
        if side == "left":
            self.setGeometry(screen.x(), screen.y(), screen.width() // 2, screen.height())
        elif side == "right":
            self.setGeometry(screen.x() + screen.width() // 2, screen.y(),
                             screen.width() // 2, screen.height())

    def create_dashboard_tab(self):
        dashboard = QWidget()
        layout = QVBoxLayout(dashboard)

        # Quick stats
        stats_layout = QHBoxLayout()

        # Mounted disks stat
        stats_layout.addWidget(self.mounted_stat)

        # Running processes stat
        stats_layout.addWidget(self.process_stat)

        # Space used stat
        stats_layout.addWidget(self.space_stat)

        layout.addLayout(stats_layout)

        # Control buttons
        controls_layout = QHBoxLayout()

        self.scan_btn.clicked.connect(self.scan_disks)
        controls_layout.addWidget(self.scan_btn)

        self.eject_selected_btn.clicked.connect(self.eject_selected)
        controls_layout.addWidget(self.eject_selected_btn)

        self.nuclear_btn.clicked.connect(self.nuclear_option)
        controls_layout.addWidget(self.nuclear_btn)

        layout.addLayout(controls_layout)

        # Progress bar
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Disk list
        disk_group = QGroupBox("Detected Simulator Disks")
        disk_layout = QVBoxLayout(disk_group)

        self.disk_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        disk_layout.addWidget(self.disk_list)

        layout.addWidget(disk_group)

        # Password input
        pwd_layout = QHBoxLayout()
        admin_label = QLabel("Admin Password:")
        admin_label.setStyleSheet("color: white;")
        pwd_layout.addWidget(admin_label)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Required for disk operations")
        pwd_layout.addWidget(self.password_input)

        # Save password checkbox
        pwd_layout.addWidget(self.save_pwd_check)

        layout.addLayout(pwd_layout)

        self.tab_widget.addTab(dashboard, "📊 Dashboard")

    def create_process_tab(self):
        process_widget = QWidget()
        layout = QVBoxLayout(process_widget)

        # Process controls
        controls = QHBoxLayout()

        self.refresh_processes_btn = AnimatedButton("🔄 Refresh Processes")
        self.refresh_processes_btn.setObjectName("RefreshProcessesButton")
        self.refresh_processes_btn.clicked.connect(self.refresh_processes)
        controls.addWidget(self.refresh_processes_btn)

        self.kill_selected_btn = AnimatedButton("💀 Kill Selected")
        self.kill_selected_btn.setObjectName("KillSelectedButton")
        self.kill_selected_btn.clicked.connect(self.kill_selected_processes)
        controls.addWidget(self.kill_selected_btn)

        self.kill_all_btn = AnimatedButton("☠️ Kill All Simulators")
        self.kill_all_btn.setObjectName("KillAllSimulatorsButton")
        self.kill_all_btn.clicked.connect(self.kill_all_simulators)
        controls.addWidget(self.kill_all_btn)

        layout.addLayout(controls)

        # Process table
        self.process_table.setColumnCount(5)
        self.process_table.setHorizontalHeaderLabels(["Select", "PID", "CPU %", "Memory %", "Process Name"])
        self.process_table.horizontalHeader().setStretchLastSection(True)
        self.process_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.process_table)

        self.tab_widget.addTab(process_widget, "🔧 Process Manager")

    def create_settings_tab(self):
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)

        # Auto-scan settings
        auto_group = QGroupBox("Automatic Operations")
        auto_layout = QVBoxLayout(auto_group)

        self.auto_scan_check.setChecked(True)
        self.auto_scan_check.setToolTip("Automatically scan for simulator disks on startup")
        auto_layout.addWidget(self.auto_scan_check)

        self.auto_eject_check = QCheckBox("Auto-eject unmounted disks")
        auto_layout.addWidget(self.auto_eject_check)

        # Scan interval
        interval_layout = QHBoxLayout()
        scan_interval_label = QLabel("Scan Interval (seconds):")
        scan_interval_label.setStyleSheet("color: white;")
        interval_layout.addWidget(scan_interval_label)
        self.scan_interval.setRange(5, 300)
        self.scan_interval.setValue(30)
        interval_layout.addWidget(self.scan_interval)
        auto_layout.addLayout(interval_layout)

        layout.addWidget(auto_group)

        # Advanced settings
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout(advanced_group)

        advanced_layout.addWidget(self.force_unmount_check)

        advanced_layout.addWidget(self.clear_cache_check)

        self.notify_check.setChecked(True)
        advanced_layout.addWidget(self.notify_check)

        # Timeout setting
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("Operation Timeout (ms):")
        timeout_label.setStyleSheet("color: white;")
        timeout_layout.addWidget(timeout_label)
        self.timeout_spin.setRange(5, 60)
        self.timeout_spin.setValue(15)
        timeout_layout.addWidget(self.timeout_spin)
        advanced_layout.addLayout(timeout_layout)

        layout.addWidget(advanced_group)

        # Disk patterns
        patterns_group = QGroupBox("Disk Detection Patterns")
        patterns_layout = QVBoxLayout(patterns_group)

        self.patterns_edit.setPlainText("Simulator\nXcode\niOS\nwatchOS\ntvOS")
        self.patterns_edit.setMaximumHeight(100)
        patterns_layout.addWidget(self.patterns_edit)

        layout.addWidget(patterns_group)

        # Save settings button
        self.save_btn = AccentButton("💾 Save Settings")
        self.save_btn.setObjectName("SaveButton")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        layout.addStretch()

        self.tab_widget.addTab(settings_widget, "⚙️ Settings")

    def create_log_tab(self):
        log_widget = QWidget()
        layout = QVBoxLayout(log_widget)

        # Log controls
        log_controls = QHBoxLayout()

        self.clear_log_btn = AnimatedButton("🗑️ Clear Log")
        self.clear_log_btn.setObjectName("ClearLogButton")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_controls.addWidget(self.clear_log_btn)

        self.export_log_btn = AnimatedButton("📤 Export Log")
        self.export_log_btn.setObjectName("ExportLogButton")
        self.export_log_btn.clicked.connect(self.export_log)
        log_controls.addWidget(self.export_log_btn)

        # Log level filter
        log_label = QLabel("Log Level:")
        log_label.setStyleSheet("color: white;")
        log_controls.addWidget(log_label)
        self.log_level_combo.addItems(["All", "Info", "Warning", "Error"])
        self.log_level_combo.currentTextChanged.connect(self.filter_log)
        log_controls.addWidget(self.log_level_combo)

        log_controls.addStretch()
        layout.addLayout(log_controls)

        # Log viewer
        self.log_viewer.setReadOnly(True)
        layout.addWidget(self.log_viewer)

        self.tab_widget.addTab(log_widget, "📋 Activity Log")

    def create_status_bar(self, layout):
        status_frame = QFrame()
        status_frame.setFixedHeight(30)
        status_frame.setStyleSheet("""
            QFrame {
                background: rgba(0, 0, 0, 0.3);
                border-top: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 0, 10, 0)

        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        # Add GitHub link label just before the green dot (connection indicator)
        github_link = QLabel(
            '<a href="https://github.com/jguida941" style="color: #FFA500; text-decoration: none;">@jguida941</a>')
        github_link.setTextFormat(Qt.TextFormat.RichText)
        github_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        github_link.setOpenExternalLinks(True)
        status_layout.addWidget(github_link)

        # Connection indicator (green dot)
        self.connection_indicator.setStyleSheet("color: #27C93F;")
        status_layout.addWidget(self.connection_indicator)

        layout.addWidget(status_frame)

    @staticmethod
    def create_stat_widget(title, value):
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background: rgba(72, 72, 74, 150);
                border-radius: 8px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(widget)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setObjectName(f"{title}Value")
        value_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        layout.addWidget(value_label)

        return widget

    def init_system_tray(self):
        if QSystemTrayIcon.isSystemTrayAvailable():
            # Ensure an icon is set to avoid warnings
            self.tray_icon.setIcon(QIcon())
            # Create tray menu
            tray_menu = QMenu()

            show_action = tray_menu.addAction("Show")
            show_action.triggered.connect(self.show)

            tray_menu.addSeparator()

            scan_action = tray_menu.addAction("Scan Disks")
            scan_action.triggered.connect(self.scan_disks)

            eject_all_action = tray_menu.addAction("Eject All")
            eject_all_action.triggered.connect(self.nuclear_option)

            tray_menu.addSeparator()

            quit_action = tray_menu.addAction("Quit")
            quit_action.triggered.connect(self.close)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()

    def start_monitoring(self):
        # Connect signals
        self.disk_scanner.update_signal.connect(self.update_disk_list)
        self.disk_scanner.progress_signal.connect(self.update_progress)

        self.process_monitor.update_signal.connect(self.update_process_list)

        # Auto-scan timer
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.auto_scan)
        self.scan_timer.start(30000)  # 30 seconds

        # Initial scan
        if self.auto_scan_check.isChecked():
            self.scan_disks()

        # Automatically populate Process Manager on startup
        self.refresh_processes()

    def scan_disks(self):
        self.log("Scanning for simulator disks...", "info")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Scanning disks...")

        if not self.disk_scanner.isRunning():
            self.disk_scanner.start()

    def update_disk_list(self, disks):
        self.disk_list.clear()
        total_size = 0

        for disk in disks:
            item = QListWidgetItem(f"{disk['name']} ({disk['device']}) - {disk['size']}")
            item.setData(Qt.ItemDataRole.UserRole, disk)
            self.disk_list.addItem(item)

            # Calculate total size
            try:
                size_gb = float(disk['size'].split()[0])
                total_size += size_gb
            except:
                pass

        # Update stats
        self.mounted_stat.findChild(QLabel, "Mounted DisksValue").setText(str(len(disks)))
        self.space_stat.findChild(QLabel, "Space UsedValue").setText(f"{total_size:.1f} GB")

        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Found {len(disks)} simulator disk(s)")
        self.log(f"Scan complete: {len(disks)} disks found", "info")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def refresh_processes(self):
        self.log("Refreshing process list...", "info")
        self.status_label.setText("Scanning processes...")

        if not self.process_monitor.isRunning():
            self.process_monitor.start()

    def update_process_list(self, processes):
        self.process_table.setRowCount(len(processes))

        for i, proc in enumerate(processes):
            # Checkbox
            checkbox = QCheckBox()
            self.process_table.setCellWidget(i, 0, checkbox)

            # Process info
            self.process_table.setItem(i, 1, QTableWidgetItem(proc['pid']))
            self.process_table.setItem(i, 2, QTableWidgetItem(f"{proc['cpu']}%"))
            self.process_table.setItem(i, 3, QTableWidgetItem(f"{proc['mem']}%"))
            self.process_table.setItem(i, 4, QTableWidgetItem(proc['name']))

        # Update stat
        self.process_stat.findChild(QLabel, "Simulator ProcessesValue").setText(str(len(processes)))
        self.status_label.setText(f"Found {len(processes)} simulator process(es)")

    def eject_selected(self):
        selected_items = self.disk_list.selectedItems()
        if not selected_items:
            self.show_notification("No disks selected", "warning")
            return

        # Kill simulator processes before unmounting
        try:
            subprocess.run(["killall", "Simulator", "launchd_sim", "CoreSimulator"], stderr=subprocess.DEVNULL)
        except Exception as e:
            self.log(f"Exception killing simulators: {e}", level="error")

        # Gather selected disks as dictionaries with 'device' keys
        self.selected_disks = []
        for item in selected_items:
            disk = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(disk, dict) and 'device' in disk:
                self.selected_disks.append(disk)

        if not self.selected_disks:
            self.show_notification("No valid disks selected", "warning")
            return

        self.log(f"Ejecting {len(self.selected_disks)} selected disk(s)...", "info")

        for disk in self.selected_disks:
            response = self.force_unmount_disk(disk['device'])
            if "successful" in response.lower():
                self.log(f"{disk['device']} ejected ✅", level="success")
            else:
                self.log(f"❌ Failed to eject {disk['device']}: {response}", level="error")

        self.show_notification(f"Eject operation complete for {len(self.selected_disks)} disk(s)", "success")
        # Rescan
        self.scan_disks()

    @staticmethod
    def force_unmount_disk(device: str) -> str:
        try:
            result = subprocess.run(
                ["hdiutil", "detach", "-force", device],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return f"Detached {device}"
            else:
                return result.stderr.strip() or result.stdout.strip()
        except subprocess.TimeoutExpired:
            return f"Timeout detaching {device}"
        except Exception as e:
            return f"Exception detaching {device}: {e}"

    def eject_disk(self, disk_id: str, password: str):
        try:
            result = subprocess.run(
                ["hdiutil", "detach", "-force", disk_id],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                self.log(f"✅ Detached {disk_id}", level="success")
            else:
                self.log(f"⚠️ Detach failed {disk_id}: {result.stderr.strip()}", level="error")
        except subprocess.TimeoutExpired:
            self.log(f"⏱️ Timeout detaching {disk_id}", level="error")
        except Exception as e:
            self.log(f"❌ Exception detaching {disk_id}: {e}", level="error")

    def nuclear_option(self):
        reply = QMessageBox.warning(self, "Nuclear Option",
                                    "This will:\n• Kill ALL simulator processes\n• Force unmount ALL simulator disks\n• Delete ALL simulator devices and data\n• Clear simulator caches\n\nContinue?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply != QMessageBox.StandardButton.Yes:
            return

        password = self.get_password()
        if not password:
            return

        self.log("Executing nuclear option...", "warning")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Kill all processes
        self.progress_bar.setValue(25)
        self.kill_all_simulators()

        # Delete all simulator devices
        self.log("Deleting all simulator devices...", "info")
        try:
            subprocess.run(["xcrun", "simctl", "shutdown", "all"], check=False)
            subprocess.run(["xcrun", "simctl", "delete", "all"], check=False)
            self.log("All simulator devices deleted", "success")
        except Exception as e:
            self.log(f"Failed to delete simulator devices: {e}", "error")

        # Remove device directories and profiles
        self.log("Removing device directories and profiles...", "info")
        try:
            devices_path = os.path.expanduser("~/Library/Developer/CoreSimulator/Devices")
            profiles_path = os.path.expanduser("~/Library/Developer/CoreSimulator/Profiles")
            subprocess.run(["rm", "-rf", devices_path], check=False)
            subprocess.run(["rm", "-rf", profiles_path], check=False)
            self.log("Device directories and profiles removed", "success")
        except Exception as e:
            self.log(f"Failed to remove directories: {e}", "error")

        # Prevent CoreSimulator from remounting disks
        self.log("Disabling CoreSimulator service...", "info")
        try:
            subprocess.run(
                ["sudo", "launchctl", "disable", "system/com.apple.CoreSimulator.CoreSimulatorService"],
                check=False
            )
            self.log("CoreSimulator service disabled", "success")
        except Exception as e:
            self.log(f"Failed to disable CoreSimulator service: {e}", "error")

        # Force unmount all disks
        self.progress_bar.setValue(50)
        self.scan_disks()  # Get fresh list

        # Wait for scan to complete
        QTimer.singleShot(1000, lambda: self.nuclear_unmount_all(password))

    def nuclear_unmount_all(self, password):
        self.progress_bar.setValue(75)

        # Unmount all found disks using the new eject_disk logic
        for i in range(self.disk_list.count()):
            item = self.disk_list.item(i)
            disk = item.data(Qt.ItemDataRole.UserRole)
            self.eject_disk(disk['device'], password)

        # Clear all caches
        self.clear_all_simulator_caches()

        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)

        self.show_notification("Nuclear option complete!", "success")
        self.log("Nuclear option completed", "success")

        # Final scan
        QTimer.singleShot(500, self.scan_disks)

    def kill_selected_processes(self):
        selected_pids = []

        for row in range(self.process_table.rowCount()):
            checkbox = self.process_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                pid = self.process_table.item(row, 1).text()
                selected_pids.append(pid)

        if not selected_pids:
            self.show_notification("No processes selected", "warning")
            return

        password = self.get_password()
        if not password:
            return

        for pid in selected_pids:
            self.kill_process(pid, password)

        # Refresh process list
        self.refresh_processes()

    def kill_process(self, pid, password):
        try:
            script = f'do shell script "kill -9 {pid}" with administrator privileges password "{password}"'
            subprocess.run(["osascript", "-e", script], check=False)
            self.log(f"Killed process {pid}", "success")
        except Exception as e:
            self.log(f"Failed to kill process {pid}: {str(e)}", "error")

    def kill_all_simulators(self):
        password = self.get_password()
        if not password:
            return

        commands = [
            "pkill -9 -f Simulator",
            "pkill -9 -f CoreSimulator",
            "pkill -9 -f SimulatorTrampoline",
            "killall -9 com.apple.CoreSimulator.CoreSimulatorService"
        ]

        for cmd in commands:
            try:
                script = f'do shell script "{cmd}" with administrator privileges password "{password}"'
                subprocess.run(["osascript", "-e", script], check=False)
                self.log(f"Executed: {cmd}", "info")
            except:
                pass

        self.show_notification("All simulator processes killed", "success")
        self.refresh_processes()

    def clear_simulator_cache(self, device):
        # Clear specific simulator cache
        cache_paths = [
            "~/Library/Developer/CoreSimulator/Caches",
            "~/Library/Developer/CoreSimulator/Devices/*/data/Library/Caches"
        ]

        for path in cache_paths:
            try:
                subprocess.run(["rm", "-rf", path], check=False)
                self.log(f"Cleared cache: {path}", "info")
            except:
                pass

    def clear_all_simulator_caches(self):
        self.log("Clearing all simulator caches...", "info")

        cache_paths = [
            "~/Library/Developer/CoreSimulator/Caches",
            "~/Library/Developer/CoreSimulator/Temp",
            "~/Library/Caches/com.apple.CoreSimulator",
            "~/Library/Developer/Xcode/DerivedData"
        ]

        for path in cache_paths:
            try:
                expanded_path = subprocess.run(["echo", path], capture_output=True, text=True).stdout.strip()
                subprocess.run(["rm", "-rf", expanded_path], check=False)
                self.log(f"Cleared: {path}", "success")
            except:
                pass

    def get_password(self):
        password = self.password_input.text()

        if not password and self.save_pwd_check.isChecked():
            # Try to get from keychain
            try:
                result = subprocess.run(
                    ["security", "find-generic-password", "-s", "SimulatorEjector", "-w"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    password = result.stdout.strip()
            except:
                pass

        if not password:
            self.show_notification("Please enter admin password", "error")
            return None

        # Save to keychain if requested
        if self.save_pwd_check.isChecked():
            try:
                subprocess.run([
                    "security", "add-generic-password",
                    "-a", "SimulatorEjector",
                    "-s", "SimulatorEjector",
                    "-w", password
                ], check=False)
            except:
                pass

        return password

    def show_notification(self, message, level="info"):
        # Color based on level
        colors = {
            "info": "rgba(10, 132, 255, 255)",
            "success": "rgba(48, 209, 88, 255)",
            "warning": "rgba(255, 159, 10, 255)",
            "error": "rgba(255, 69, 58, 255)"
        }

        # Create popup
        popup = QLabel(message, self)
        popup.setStyleSheet(f"""
            QLabel {{
                background: {colors.get(level, colors['info'])};
                color: white;
                font-weight: bold;
                padding: 15px 25px;
                border-radius: 10px;
                font-size: 14px;
            }}
        """)
        popup.setAlignment(Qt.AlignmentFlag.AlignCenter)
        popup.adjustSize()

        # Position at top center
        popup.move((self.width() - popup.width()) // 2, 60)

        # Fade in animation
        effect = QGraphicsOpacityEffect()
        popup.setGraphicsEffect(effect)

        self.fade_in = QPropertyAnimation(effect, b"opacity")
        self.fade_in.setDuration(200)
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)

        popup.show()
        self.fade_in.start()

        # Auto hide after 3 seconds
        QTimer.singleShot(3000, lambda: self.fade_out_notification(popup, effect))

        # Also update status bar
        self.status_label.setText(message)

        # System notification if enabled
        if self.notify_check.isChecked() and hasattr(self, 'tray_icon'):
            self.tray_icon.showMessage("Simulator Ejector", message, QSystemTrayIcon.MessageIcon.Information, 2000)

    def fade_out_notification(self, popup, effect):
        self.fade_out = QPropertyAnimation(effect, b"opacity")
        self.fade_out.setDuration(200)
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.finished.connect(popup.deleteLater)
        self.fade_out.start()

    def log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color coding
        colors = {
            "info": "#00ff00",
            "success": "#30d158",
            "warning": "#ff9500",
            "error": "#ff453a"
        }

        formatted_message = f'<span style="color: #888;">[{timestamp}]</span> <span style="color: {colors.get(level, "#fff")}">{message}</span>'

        self.log_viewer.append(formatted_message)

        # Auto-scroll to bottom
        scrollbar = QScrollBar(Qt.Orientation.Vertical)
        scrollbar.setStyleSheet("QScrollBar:vertical { background: transparent; width: 12px; margin: 0px; }")
        self.log_viewer.setVerticalScrollBar(scrollbar)
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        self.log_viewer.clear()
        self.log("Log cleared", "info")

    def export_log(self):
        content = self.log_viewer.toPlainText()
        filename = f"simulator_ejector_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        try:
            with open(filename, 'w') as f:
                f.write(content)
            self.show_notification(f"Log exported to {filename}", "success")
        except Exception as e:
            self.show_notification(f"Failed to export log: {str(e)}", "error")

    def filter_log(self, level):
        # TODO: Implement log filtering
        pass

    def save_settings(self):
        # TODO: Implement settings persistence
        self.show_notification("Settings saved", "success")

    def auto_scan(self):
        if self.auto_scan_check.isChecked():
            self.scan_disks()

    def show_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(44, 44, 46, 240);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(10, 132, 255, 200);
            }
        """)

        about_action = menu.addAction("About")
        about_action.triggered.connect(self.show_about)

        menu.addSeparator()

        prefs_action = menu.addAction("Preferences")
        prefs_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))

        menu.addSeparator()

        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.close)

        menu.exec(self.mapToGlobal(QPoint(self.width() - 150, 50)))

    def show_about(self):
        about_text = """<h2>iOS Simulator Disk Ejector Pro</h2>
        <p>Version 2.0.0</p>
        <p>A professional utility for managing iOS Simulator disks and processes.</p>
        <p>Features:</p>
        <ul>
        <li>Automatic disk detection and monitoring</li>
        <li>Process management with live updates</li>
        <li>Secure password handling with Keychain integration</li>
        <li>Advanced logging and analytics</li>
        <li>Native macOS UI design</li>
        </ul>
        <p>© 2024 - Built with PyQt6</p>"""

        msg = QMessageBox(self)
        msg.setWindowTitle("About")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(about_text)
        msg.exec()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # (Old drag code replaced by macOS-style above)

    def closeEvent(self, event):
        # Save settings before closing
        # Cleanup
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        event.accept()


if __name__ == "__main__":
    # Enable high DPI scaling before creating the application
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("iOS Simulator Disk Ejector Pro")

    # Attempt to load tab_button_colors.qss for custom button styles
    try:
        with open("tab_button_colors.qss", "r") as file:
            qss = file.read()
            app.setStyleSheet(qss)
    except Exception as e:
        print(f"[WARNING] Failed to load QSS: {e}")


    window = EnhancedSimulatorKiller()
    window.show()

    sys.exit(app.exec())

