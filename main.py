import sys, time, math
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QColor, QAction
from PyQt6.QtCore import QTimer
from generated import main_ui
from services.hvpm import HvpmService
from services.auto_test import AutoTestService
from services.test_scenario_engine import TestScenarioEngine
from services.ni_daq import create_ni_service
from services import theme
from services.adaptive_ui import get_adaptive_ui
from services.responsive_layout import get_responsive_manager
from ui.test_settings_dialog import TestSettingsDialog
from ui.multi_channel_monitor import MultiChannelMonitorDialog
from collections import deque
import pyqtgraph as pg

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize adaptive UI system
        self.adaptive_ui = get_adaptive_ui()
        self.responsive_manager = get_responsive_manager()
        
        # Setup UI
        self.ui = main_ui.Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Apply adaptive window sizing
        self._apply_adaptive_window_sizing()

        # Apply modern theme with adaptive sizing
        theme.apply_theme(self)

        # HVPM 서비스
        self.hvpm_service = HvpmService(
            combo=self.ui.hvpm_CB,
            status_label=getattr(self.ui, 'hvpmStatus_LB', None),
            volt_label=getattr(self.ui, 'hvpmVolt_LB', None),
            volt_entry=getattr(self.ui, 'hvpmVolt_LE', None)
        )

        # Auto Test 서비스
        self.auto_test_service = AutoTestService(
            hvpm_service=self.hvpm_service,
            log_callback=self._log
        )
        
        # NI DAQ 서비스
        self._setup_nidaq_environment()
        self.ni_service = create_ni_service()
        self.ni_service.connection_changed.connect(self._on_ni_connection_changed)
        self.ni_service.error_occurred.connect(self._on_ni_error)
        
        # Multi-channel monitoring
        self.multi_channel_dialog = None
        
        # Initialize test scenario engine after ni_service is created
        self.test_scenario_engine = TestScenarioEngine(
            hvpm_service=self.hvpm_service,
            daq_service=self.ni_service,
            log_callback=None  # Use default signal-based logging (thread-safe)
        )
        
        # Connect test scenario engine signals
        self.test_scenario_engine.connect_progress_callback(self._on_auto_test_progress)
        self.test_scenario_engine.test_completed.connect(self._on_auto_test_completed)
        # Use QueuedConnection to ensure _log runs in main thread
        from PyQt6.QtCore import Qt
        self.test_scenario_engine.log_message.connect(self._log, Qt.ConnectionType.QueuedConnection)
        
        # 측정 모드 추적 (독립적 제어)
        self._hvpm_monitoring = False
        self._ni_monitoring = False
        self._show_conflict_warning = True
        
        # Test configuration settings
        self.test_config = {
            'stabilization_voltage': 4.8,
            'test_voltage': 4.0,
            'test_cycles': 5,
            'test_duration': 10,
            'stabilization_time': 10,
            'sampling_interval': 1.0,
            'skip_stabilization_data': True
        }
        
        # Data collection state
        self.test_data_collection_active = False
        self.last_timestamp_log = 0

        # 버퍼/타이머 초기화 (그래프용 - 비활성화)
        self._t0 = None
        self._tbuf = deque(maxlen=600)   # 10Hz*60s = 최근 1분
        self._vbuf = deque(maxlen=600)
        self._ibuf = deque(maxlen=600)
        self._graphActive = False
        self._graphTimer = QTimer(self)
        self._graphTimer.setInterval(100)        # 10 Hz UI 업데이트
        self._graphTimer.timeout.connect(self._on_graph_tick)
        
        # HVPM 간단 모니터링용
        self._hvpm_monitoring_active = False
        self._hvpm_monitor_timer = QTimer(self)
        self._hvpm_monitor_timer.setInterval(1000)  # 1초마다
        self._hvpm_monitor_timer.timeout.connect(self._on_hvpm_monitor_tick)

        # ADB 상태 초기화
        self.selected_device = None
        self._refreshing_adb = False
        self._cfg_refresh_reads_voltage = False

        # Setup enhanced UI components
        # self.setup_graphs()  # 그래프 기능 비활성화
        self.setup_status_indicators()
        self.setup_menu_actions()
        
        # Debug: Check UI elements first
        self._check_ui_elements()
        
        # Setup connections after UI check
        self.setup_connections()
        self.setup_auto_test_ui()
        
        # 초기화 - UI 설정 완료 후 실행
        self.refresh_connections()
        
        # Initialize NI devices
        self.refresh_ni_devices()
        self._update_ni_status()
        
        # Initialize voltage configuration from settings
        self._on_voltage_config_changed()
        
        # Reload test scenarios after full initialization
        self._log("Reloading test scenarios after full UI initialization...", "info")
        self.setup_auto_test_ui()
        
        # Apply adaptive sizing to UI elements
        self._apply_adaptive_ui_sizing()
        
        # Apply responsive layout management
        self._apply_responsive_layout()
        
        # Status bar 메시지
        self.ui.statusbar.showMessage("Ready - Connect devices to start monitoring and testing", 5000)

    def _apply_adaptive_window_sizing(self):
        """Apply adaptive window sizing based on screen resolution and DPI"""
        # Get responsive window size - minimize width
        responsive_width = max(1000, self.adaptive_ui.get_responsive_width(0.7))  # 70% of screen width, minimum 1000
        responsive_height = self.adaptive_ui.get_responsive_height(0.85)  # 85% of screen height
        
        # Set initial window size (minimized width)
        self.resize(responsive_width, responsive_height)
        
        # Set minimum size that works on all screens
        min_size = self.adaptive_ui.get_minimum_window_size()
        self.setMinimumSize(min_size)
        
        # Center window on screen
        screen = QtWidgets.QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = (screen_geometry.width() - responsive_width) // 2
            y = (screen_geometry.height() - responsive_height) // 2
            self.move(max(0, x), max(0, y))
        
        print(f"[AdaptiveUI] Window sized to {responsive_width}x{responsive_height}, min: {min_size.width()}x{min_size.height()}")

    def _apply_adaptive_ui_sizing(self):
        """Apply adaptive sizing to specific UI elements that need manual adjustment"""
        # Remove hardcoded font sizes from inline styles and let theme handle it
        self._remove_hardcoded_font_sizes()
        
        # Apply responsive layout adjustments
        self._apply_responsive_layout_adjustments()
        
    def _remove_hardcoded_font_sizes(self):
        """Remove hardcoded font sizes from UI elements"""
        # Get scaled font sizes
        small_font = self.adaptive_ui.get_scaled_font_size(9)
        base_font = self.adaptive_ui.get_scaled_font_size(11)
        large_font = self.adaptive_ui.get_scaled_font_size(14)
        display_font = self.adaptive_ui.get_scaled_font_size(16)
        
        # Update status labels with adaptive font sizes
        status_elements = [
            (getattr(self.ui, 'hvpmStatus_LB', None), base_font),
            (getattr(self.ui, 'niStatus_LB', None), base_font),
            (getattr(self.ui, 'testStatus_LB', None), base_font),
        ]
        
        for element, font_size in status_elements:
            if element:
                current_style = element.styleSheet()
                # Remove old font-size declarations and add adaptive one
                import re
                new_style = re.sub(r'font-size:\s*\d+pt;?', f'font-size: {font_size}pt;', current_style)
                element.setStyleSheet(new_style)
        
        # Update display labels (voltage, current, power)
        display_elements = [
            (getattr(self.ui, 'hvpmVolt_LB', None), display_font),
            (getattr(self.ui, 'hvpmCurrent_LB', None), display_font),
            (getattr(self.ui, 'hvpmPower_LB', None), display_font),
        ]
        
        for element, font_size in display_elements:
            if element:
                current_style = element.styleSheet()
                new_style = re.sub(r'font-size:\s*\d+pt;?', f'font-size: {font_size}pt;', current_style)
                element.setStyleSheet(new_style)
    
    def _apply_responsive_layout_adjustments(self):
        """Apply responsive layout adjustments"""
        # Adjust GroupBox minimum sizes based on screen size
        screen_width = self.adaptive_ui.get_responsive_width(1.0)
        
        # Calculate responsive widths for main sections
        if screen_width < 1200:
            # Compact layout for smaller screens
            control_width = self.adaptive_ui.get_scaled_value(320)
            test_width = self.adaptive_ui.get_scaled_value(300)
            ni_width = self.adaptive_ui.get_scaled_value(260)
        else:
            # Standard layout for larger screens
            control_width = self.adaptive_ui.get_scaled_value(350)
            test_width = self.adaptive_ui.get_scaled_value(350)
            ni_width = self.adaptive_ui.get_scaled_value(280)
        
        # Apply responsive widths
        responsive_elements = [
            (getattr(self.ui, 'controlGroupBox', None), control_width),
            (getattr(self.ui, 'autoTestGroupBox', None), test_width),
            (getattr(self.ui, 'niCurrentGroupBox', None), ni_width),
        ]
        
        for element, width in responsive_elements:
            if element:
                element.setMinimumWidth(width)
                # Remove maximum width constraints for better responsiveness
                element.setMaximumWidth(16777215)
    
    def _apply_responsive_layout(self):
        """Apply responsive layout management to UI elements"""
        # Setup responsive GroupBoxes
        self.responsive_manager.setup_responsive_groupbox(
            getattr(self.ui, 'connectionGroupBox', None), 1.0
        )
        self.responsive_manager.setup_responsive_groupbox(
            getattr(self.ui, 'controlGroupBox', None), 0.35
        )
        self.responsive_manager.setup_responsive_groupbox(
            getattr(self.ui, 'autoTestGroupBox', None), 0.35
        )
        self.responsive_manager.setup_responsive_groupbox(
            getattr(self.ui, 'niCurrentGroupBox', None), 0.25
        )
        self.responsive_manager.setup_responsive_groupbox(
            getattr(self.ui, 'logGroupBox', None), 1.0
        )
        
        # Setup responsive buttons
        buttons = [
            getattr(self.ui, 'port_PB', None),
            getattr(self.ui, 'daqConnect_PB', None),
            getattr(self.ui, 'readVoltCurrent_PB', None),
            getattr(self.ui, 'setVolt_PB', None),
            getattr(self.ui, 'startMonitoring_PB', None),
            getattr(self.ui, 'startAutoTest_PB', None),
            getattr(self.ui, 'stopAutoTest_PB', None),
            # testSettings_PB removed
        ]
        self.responsive_manager.setup_responsive_buttons(*[b for b in buttons if b])
        
        # Setup responsive combo boxes
        combos = [
            getattr(self.ui, 'hvpm_CB', None),
            getattr(self.ui, 'comport_CB', None),
            getattr(self.ui, 'daqDevice_CB', None),
            getattr(self.ui, 'daqChannel_CB', None),
            getattr(self.ui, 'testScenario_CB', None),
        ]
        self.responsive_manager.setup_responsive_combobox(*[c for c in combos if c])
        
        # Apply responsive margins to main layouts
        layouts = [
            getattr(self.ui, 'mainVerticalLayout', None),
            getattr(self.ui, 'connectionLayout', None),
            getattr(self.ui, 'mainContentLayout', None),
        ]
        for layout in layouts:
            if layout:
                self.responsive_manager.apply_responsive_margins(layout)

    def _setup_nidaq_environment(self):
        """Setup NI-DAQmx environment paths"""
        import os
        
        # NI-DAQmx 런타임 경로 추가 시도
        possible_paths = [
            # Windows 표준 경로
            r"C:\Program Files (x86)\National Instruments\Shared\ExternalCompilerSupport\C\lib64\msvc",
            r"C:\Program Files\National Instruments\Shared\ExternalCompilerSupport\C\lib64\msvc", 
            r"C:\Windows\System32",
            r"C:\Program Files (x86)\National Instruments\RT\NIDAQmx\bin",
            r"C:\Program Files\National Instruments\RT\NIDAQmx\bin",
            r"C:\Program Files (x86)\National Instruments\Shared\CVI\Bin",
            r"C:\Program Files\National Instruments\Shared\CVI\Bin",
            
            # 로컬 NIDAQ 런타임 폴더들
            "./NIDAQ1610Runtime",
            "../NIDAQ1610Runtime", 
            "../../NIDAQ1610Runtime",
            "./NIDAQ1610Runtime/bin",
            "../NIDAQ1610Runtime/bin",
            "../../NIDAQ1610Runtime/bin",
            
            # 상대 경로들
            os.path.join(os.getcwd(), "NIDAQ1610Runtime"),
            os.path.join(os.path.dirname(os.getcwd()), "NIDAQ1610Runtime"),
            os.path.join(os.getcwd(), "NIDAQ1610Runtime", "bin"),
            os.path.join(os.path.dirname(os.getcwd()), "NIDAQ1610Runtime", "bin"),
        ]

        # 사용자 정의 NIDAQ 경로 확인
        custom_nidaq_path = os.environ.get('NIDAQ_RUNTIME_PATH')
        if custom_nidaq_path:
            possible_paths.insert(0, custom_nidaq_path)
            possible_paths.insert(0, os.path.join(custom_nidaq_path, 'bin'))
            print(f"Using custom NIDAQ path: {custom_nidaq_path}")

        # 환경 변수에 경로 추가
        found_paths = []
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found NI path: {path}")
                found_paths.append(path)
                if path not in os.environ.get('PATH', ''):
                    os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')

        if found_paths:
            print(f"Added {len(found_paths)} NI paths to environment")
            self._log(f"NI-DAQmx environment setup: {len(found_paths)} paths added", "info")
        else:
            print("No NI-DAQmx paths found")
            self._log("WARNING: No NI-DAQmx runtime paths found", "warn")

    def setup_graphs(self):
        """Setup enhanced graph widgets"""
        # Voltage plot with enhanced styling
        self._plot_v = pg.PlotWidget(title="HVPM Voltage Monitor")
        self._plot_v.setLabel("bottom", "Time", units="s")
        self._plot_v.setLabel("left", "Voltage", units="V")
        self._plot_v.showGrid(x=True, y=True, alpha=0.3)
        
        # Voltage curve with enhanced styling
        self._curve_v = self._plot_v.plot(
            pen=pg.mkPen(color=theme.get_color('success'), width=3),
            name="Voltage"
        )
        
        # Current plot with enhanced styling
        self._plot_i = pg.PlotWidget(title="HVPM Current Monitor")
        self._plot_i.setLabel("bottom", "Time", units="s")
        self._plot_i.setLabel("left", "Current", units="A")
        self._plot_i.showGrid(x=True, y=True, alpha=0.3)
        
        # Current curve with enhanced styling
        self._curve_i = self._plot_i.plot(
            pen=pg.mkPen(color=theme.get_color('warning'), width=3),
            name="Current"
        )

        # Add plots to layout
        self.ui.graphLayout.addWidget(self._plot_v)
        self.ui.graphLayout.addWidget(self._plot_i)

        # Apply theme to plots
        theme.apply_theme(self, [self._plot_v, self._plot_i])
        
        # Enable auto-range
        self._plot_v.enableAutoRange('y', True)
        self._plot_i.enableAutoRange('y', True)

    def setup_connections(self):
        """Setup signal connections"""
        # Button connections
        if hasattr(self.ui, 'port_PB') and self.ui.port_PB:
            self.ui.port_PB.clicked.connect(self.refresh_connections)
        if hasattr(self.ui, 'readVoltCurrent_PB') and self.ui.readVoltCurrent_PB:
            self.ui.readVoltCurrent_PB.clicked.connect(self.handle_read_voltage_current)
        if hasattr(self.ui, 'setVolt_PB') and self.ui.setVolt_PB:
            self.ui.setVolt_PB.clicked.connect(self.handle_set_voltage)
        if hasattr(self.ui, 'startMonitoring_PB') and self.ui.startMonitoring_PB:
            self.ui.startMonitoring_PB.clicked.connect(self.toggle_monitoring)
        
        # NI DAQ connections (Connection Settings)
        if hasattr(self.ui, 'daqConnect_PB') and self.ui.daqConnect_PB:
            self.ui.daqConnect_PB.clicked.connect(self.toggle_ni_connection)
        
        # Multi-Channel Monitor button
        if hasattr(self.ui, 'multiChannelMonitor_PB') and self.ui.multiChannelMonitor_PB:
            self.ui.multiChannelMonitor_PB.clicked.connect(self.open_multi_channel_monitor)
        
        # NI DAQ monitoring connections
        if hasattr(self.ui, 'niMonitor_PB') and self.ui.niMonitor_PB:
            self.ui.niMonitor_PB.clicked.connect(self.toggle_ni_monitoring)
        
        # Auto test connections (check if they exist)
        if hasattr(self.ui, 'startAutoTest_PB') and self.ui.startAutoTest_PB:
            self.ui.startAutoTest_PB.clicked.connect(self._on_start_test_button_clicked)
        if hasattr(self.ui, 'stopAutoTest_PB') and self.ui.stopAutoTest_PB:
            self.ui.stopAutoTest_PB.clicked.connect(self.stop_auto_test)
        # testSettings_PB removed
        
        # Combo box connections
        if hasattr(self.ui, 'comport_CB') and self.ui.comport_CB:
            self.ui.comport_CB.currentIndexChanged.connect(self._on_device_selected)
        
        # Enter key for voltage input
        if hasattr(self.ui, 'hvpmVolt_LE') and self.ui.hvpmVolt_LE:
            self.ui.hvpmVolt_LE.returnPressed.connect(self.handle_set_voltage)
        
        # Auto test service signals
        self.auto_test_service.progress_updated.connect(self._on_auto_test_progress)
        self.auto_test_service.test_completed.connect(self._on_auto_test_completed)
        self.auto_test_service.voltage_stabilized.connect(self._on_voltage_stabilized)
        
        # System log copy/paste functionality
        if hasattr(self.ui, 'log_LW') and self.ui.log_LW:
            self.setup_log_context_menu()

    def setup_log_context_menu(self):
        """Setup context menu for System log with copy/paste functionality"""
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        # Enable context menu
        self.ui.log_LW.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.log_LW.customContextMenuRequested.connect(self.show_log_context_menu)
        
        # Enable keyboard shortcuts
        self.ui.log_LW.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Add keyboard shortcuts
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # Ctrl+C for copy
        copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self.ui.log_LW)
        copy_shortcut.activated.connect(self.copy_selected_logs)
        
        # Ctrl+A for select all
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self.ui.log_LW)
        select_all_shortcut.activated.connect(self.select_all_logs)
        
    def show_log_context_menu(self, position):
        """Show context menu for System log"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        from PyQt6.QtCore import QPoint
        
        # Get selected items
        selected_items = self.ui.log_LW.selectedItems()
        
        if not selected_items:
            return
            
        # Create context menu
        context_menu = QMenu(self)
        
        # Copy action
        copy_action = QAction("복사 (Copy)", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_selected_logs)
        context_menu.addAction(copy_action)
        
        # Copy all action
        copy_all_action = QAction("모두 복사 (Copy All)", self)
        copy_all_action.triggered.connect(self.copy_all_logs)
        context_menu.addAction(copy_all_action)
        
        # Separator
        context_menu.addSeparator()
        
        # Select all action
        select_all_action = QAction("모두 선택 (Select All)", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.select_all_logs)
        context_menu.addAction(select_all_action)
        
        # Clear logs action
        context_menu.addSeparator()
        clear_action = QAction("로그 지우기 (Clear Logs)", self)
        clear_action.triggered.connect(self.clear_logs)
        context_menu.addAction(clear_action)
        
        # Show menu
        context_menu.exec(self.ui.log_LW.mapToGlobal(position))
        
    def copy_selected_logs(self):
        """Copy selected log entries to clipboard"""
        try:
            selected_items = self.ui.log_LW.selectedItems()
            if not selected_items:
                return
                
            # Get text from selected items
            log_texts = []
            for item in selected_items:
                log_texts.append(item.text())
            
            # Join with newlines and copy to clipboard
            clipboard_text = '\n'.join(log_texts)
            
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)
            
            self._log(f"복사됨: {len(selected_items)}개 로그 항목", "info")
            
        except Exception as e:
            self._log(f"로그 복사 중 오류: {e}", "error")
            
    def copy_all_logs(self):
        """Copy all log entries to clipboard"""
        try:
            log_texts = []
            for i in range(self.ui.log_LW.count()):
                item = self.ui.log_LW.item(i)
                if item:
                    log_texts.append(item.text())
            
            if not log_texts:
                self._log("복사할 로그가 없습니다", "warn")
                return
                
            # Join with newlines and copy to clipboard
            clipboard_text = '\n'.join(log_texts)
            
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(clipboard_text)
            
            self._log(f"모든 로그 복사됨: {len(log_texts)}개 항목", "info")
            
        except Exception as e:
            self._log(f"전체 로그 복사 중 오류: {e}", "error")
            
    def select_all_logs(self):
        """Select all log entries"""
        try:
            self.ui.log_LW.selectAll()
            selected_count = len(self.ui.log_LW.selectedItems())
            self._log(f"모든 로그 선택됨: {selected_count}개 항목", "info")
        except Exception as e:
            self._log(f"로그 선택 중 오류: {e}", "error")
            
    def clear_logs(self):
        """Clear all log entries"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # Confirmation dialog
            reply = QMessageBox.question(
                self, 
                "로그 지우기", 
                "모든 로그를 지우시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.ui.log_LW.clear()
                self._log("로그가 지워졌습니다", "info")
                
        except Exception as e:
            self._log(f"로그 지우기 중 오류: {e}", "error")

    def setup_status_indicators(self):
        """Setup status indicators and tooltips"""
        # Add tooltips
        self.ui.hvpm_CB.setToolTip("Select HVPM device")
        self.ui.comport_CB.setToolTip("Select ADB device")
        self.ui.port_PB.setToolTip("Refresh device connections")
        self.ui.hvpmVolt_LE.setToolTip("Enter target voltage (V)")
        
        # HVPM control tooltips (check if elements exist)
        if hasattr(self.ui, 'readVoltCurrent_PB') and self.ui.readVoltCurrent_PB:
            self.ui.readVoltCurrent_PB.setToolTip("Read current voltage and current from HVPM device")
        if hasattr(self.ui, 'setVolt_PB') and self.ui.setVolt_PB:
            self.ui.setVolt_PB.setToolTip("Set voltage to specified value")
        if hasattr(self.ui, 'startMonitoring_PB') and self.ui.startMonitoring_PB:
            self.ui.startMonitoring_PB.setToolTip("Start/stop continuous monitoring")
        
        # Graph tooltips (check if elements exist)
        if hasattr(self.ui, 'startGraph_PB') and self.ui.startGraph_PB:
            self.ui.startGraph_PB.setToolTip("Start real-time monitoring")
        if hasattr(self.ui, 'stopGraph_PB') and self.ui.stopGraph_PB:
            self.ui.stopGraph_PB.setToolTip("Stop real-time monitoring")
        
        # NI DAQ tooltips (check if elements exist)
        if hasattr(self.ui, 'daqDevice_CB') and self.ui.daqDevice_CB:
            self.ui.daqDevice_CB.setToolTip("Select NI DAQ device")
        if hasattr(self.ui, 'daqChannel_CB') and self.ui.daqChannel_CB:
            self.ui.daqChannel_CB.setToolTip("Select analog input channel")
        if hasattr(self.ui, 'daqConnect_PB') and self.ui.daqConnect_PB:
            self.ui.daqConnect_PB.setToolTip("Connect/disconnect NI DAQ device")
        if hasattr(self.ui, 'niMonitor_PB') and self.ui.niMonitor_PB:
            self.ui.niMonitor_PB.setToolTip("Start/stop NI current monitoring")
        
        # Auto test tooltips (check if elements exist)
        if hasattr(self.ui, 'testScenario_CB') and self.ui.testScenario_CB:
            self.ui.testScenario_CB.setToolTip("Select test scenario to run")
        # testSettings_PB removed
        if hasattr(self.ui, 'startAutoTest_PB') and self.ui.startAutoTest_PB:
            self.ui.startAutoTest_PB.setToolTip("Start automated test with voltage control")
        if hasattr(self.ui, 'stopAutoTest_PB') and self.ui.stopAutoTest_PB:
            self.ui.stopAutoTest_PB.setToolTip("Stop current automated test")
        
        # Add progress tracking tooltip
        if hasattr(self.ui, 'testProgress_PB') and self.ui.testProgress_PB:
            self.ui.testProgress_PB.setToolTip("Test progress: Shows current completion percentage")
        if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
            self.ui.testStatus_LB.setToolTip("Current test status and progress details")

    def setup_menu_actions(self):
        """Setup menu actions"""
        # File menu actions
        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionExport_Data.triggered.connect(self.export_data)
        
        # View menu actions
        self.ui.actionToggle_Theme.triggered.connect(self.toggle_theme)
        self.ui.actionReset_Layout.triggered.connect(self.reset_layout)
        
        # Test menu actions
        self.ui.actionQuick_Test.triggered.connect(self.quick_test)
        self.ui.actionTest_Settings.triggered.connect(self.test_settings)
        
        # Tools menu actions (if exists)
        if hasattr(self.ui, 'actionMulti_Channel_Monitor'):
            self.ui.actionMulti_Channel_Monitor.triggered.connect(self.open_multi_channel_monitor)
        
        # Help menu actions
        self.ui.actionAbout.triggered.connect(self.show_about)

    def setup_auto_test_ui(self):
        """Setup auto test UI components"""
        # Check if auto test UI elements exist
        try:
            combo_box = getattr(self.ui, 'testScenario_CB', None)
            if combo_box is None:
                self._log("WARNING: testScenario_CB not found in UI - auto test features disabled", "warn")
                return
            
            self._log(f"Setting up auto test UI. Current combo items: {combo_box.count()}", "info")
                
            # Clear existing scenarios and load from test scenario engine
            combo_box.clear()
            
        except Exception as e:
            self._log(f"ERROR: Failed to access testScenario_CB: {e}", "error")
            return
        
        # Load available scenarios from test scenario engine
        try:
            self._log("Attempting to load test scenarios...", "info")
            scenarios = self.test_scenario_engine.get_available_scenarios()
            self._log(f"Retrieved scenarios: {list(scenarios.keys()) if scenarios else 'None'}", "info")
            
            if scenarios:
                for scenario_key, scenario_config in scenarios.items():
                    combo_box.addItem(scenario_config.name, scenario_key)
                    self._log(f"Added scenario: {scenario_config.name} (key: {scenario_key})", "info")
                self._log(f"Successfully loaded {len(scenarios)} test scenarios", "info")
            else:
                combo_box.addItem("No test scenarios available")
                self._log("No test scenarios available", "warn")
        except Exception as e:
            import traceback
            self._log(f"Error loading test scenarios: {e}", "error")
            self._log(f"Traceback: {traceback.format_exc()}", "error")
            combo_box.addItem("Error loading scenarios")
        
        # Enable combo box
        combo_box.setEnabled(True)
        
        # Connect scenario selection change
        try:
            combo_box.currentIndexChanged.connect(self._on_scenario_changed)
            self._log("Connected scenario selection change handler", "info")
        except Exception as e:
            self._log(f"Error connecting scenario change handler: {e}", "error")
        
        # Debug: Check combo box contents
        combo_count = combo_box.count()
        self._log(f"Final combo box item count: {combo_count}", "info")
        for i in range(combo_count):
            item_text = combo_box.itemText(i)
            item_data = combo_box.itemData(i)
            self._log(f"  [{i}] Text: '{item_text}', Data: {item_data}", "info")

    def _update_groupbox_colors(self, hvpm_connected: bool, ni_connected: bool):
        """Update GroupBox title colors based on connection status"""
        try:
            # HVPM Control color
            if hasattr(self.ui, 'controlGroupBox') and self.ui.controlGroupBox:
                hvpm_color = "#4CAF50" if hvpm_connected else "#ff6b6b"  # Green if connected, red if not
                self.ui.controlGroupBox.setStyleSheet(f"""
                    QGroupBox::title {{
                        color: {hvpm_color};
                        font-weight: bold;
                        font-size: 9pt;
                    }}
                """)
            
            # NI DAQ Control color  
            if hasattr(self.ui, 'niCurrentGroupBox') and self.ui.niCurrentGroupBox:
                ni_color = "#4CAF50" if ni_connected else "#ff6b6b"  # Green if connected, red if not
                self.ui.niCurrentGroupBox.setStyleSheet(f"""
                    QGroupBox::title {{
                        color: {ni_color};
                        font-weight: bold;
                        font-size: 9pt;
                    }}
                """)
                
        except Exception as e:
            self._log(f"Error updating groupbox colors: {e}", "error")

    def refresh_connections(self):
        """Enhanced connection refresh with better feedback"""
        self.ui.port_PB.setEnabled(False)
        self.ui.port_PB.setText("Refreshing...")
        
        # Refresh ADB
        self.refresh_adb_ports()
        
        # Refresh HVPM
        self.hvpm_service.refresh_ports(log_callback=self._log)
        
        # Refresh NI DAQ devices
        self.refresh_ni_devices()
        
        # Update status
        self.update_connection_status()
        
        self.ui.port_PB.setEnabled(True)
        self.ui.port_PB.setText("Refresh")
        
        # Read initial voltage if configured
        if self._cfg_refresh_reads_voltage and self.hvpm_service.is_connected():
            self.handle_read_voltage()

    def update_connection_status(self):
        """Update connection status indicators"""
        try:
            # Update HVPM status
            hvpm_status_label = getattr(self.ui, 'hvpmStatus_LB', None)
            if hvpm_status_label:
                if hasattr(self.hvpm_service, 'pm') and self.hvpm_service.pm:
                    hvpm_status_label.setText("Connected")
                    hvpm_status_label.setStyleSheet(f"color: {theme.get_status_color('connected')}; font-weight: bold;")
                else:
                    hvpm_status_label.setText("Disconnected")
                    hvpm_status_label.setStyleSheet(f"color: {theme.get_status_color('disconnected')}; font-weight: bold;")
            
            # Update auto test button availability (safely)
            self._update_auto_test_buttons()
            
        except Exception as e:
            self._log(f"Error updating connection status: {e}", "error")

    def _update_auto_test_buttons(self):
        """Update auto test button states"""
        # Don't update if test is running (let _set_ui_test_mode handle it)
        try:
            if hasattr(self, 'test_scenario_engine') and self.test_scenario_engine.is_running():
                self._log("Skipping _update_auto_test_buttons - test is running", "debug")
                return
        except Exception:
            pass
            
        # Check if auto test UI elements exist and are not None
        try:
            start_button = getattr(self.ui, 'startAutoTest_PB', None)
            stop_button = getattr(self.ui, 'stopAutoTest_PB', None)
            
            if start_button is None or stop_button is None:
                return
                
            # Safely get connection states with proper None handling
            try:
                hvpm_connected = bool(self.hvpm_service.is_connected())
            except Exception:
                hvpm_connected = False
                
            try:
                adb_connected = bool(self.selected_device and self.selected_device != "No devices found")
            except Exception:
                adb_connected = False
                
            try:
                test_running = bool(hasattr(self, 'test_scenario_engine') and self.test_scenario_engine.is_running())
                if hasattr(self, 'test_scenario_engine'):
                    engine_status = self.test_scenario_engine.get_status()
                    self._log(f"_update_auto_test_buttons: engine_status={engine_status.value}, test_running={test_running}", "debug")
            except Exception as e:
                test_running = False
                self._log(f"Error checking test running status: {e}", "debug")
            
            can_start = hvpm_connected and adb_connected and not test_running
            
            # Update GroupBox title colors based on connection status
            self._update_groupbox_colors(hvpm_connected, self.ni_service.is_connected() if self.ni_service else False)
            
            # Reset Auto Test group box title when test is not running
            if not test_running and hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                current_title = self.ui.autoTestGroupBox.title()
                if "RUNNING" in current_title or "COMPLETED" in current_title or "FAILED" in current_title or "STOPPED" in current_title:
                    # Reset to original title after a delay for completed/failed/stopped states
                    if "RUNNING" not in current_title:
                        QTimer.singleShot(3000, lambda: self.ui.autoTestGroupBox.setTitle("Auto Test") if hasattr(self.ui, 'autoTestGroupBox') else None)
                    else:
                        self.ui.autoTestGroupBox.setTitle("Auto Test")
            
            # Safely update button states
            try:
                if start_button is not None and hasattr(start_button, 'setEnabled'):
                    start_button.setEnabled(bool(can_start))
            except Exception as e:
                self._log(f"Error updating start button: {e}", "error")
                
            try:
                if stop_button is not None and hasattr(stop_button, 'setEnabled'):
                    stop_button.setEnabled(bool(test_running))
            except Exception as e:
                self._log(f"Error updating stop button: {e}", "error")
            
            # Update tooltips based on status
            try:
                if start_button is not None and hasattr(start_button, 'setToolTip'):
                    if not hvpm_connected:
                        start_button.setToolTip("HVPM device must be connected")
                    elif not adb_connected:
                        start_button.setToolTip("ADB device must be connected")
                    elif test_running:
                        start_button.setToolTip("Test is currently running")
                    else:
                        start_button.setToolTip("Start automated test with voltage control")
            except Exception as e:
                self._log(f"Error updating tooltip: {e}", "error")
                
        except Exception as e:
            # If anything goes wrong, just log and continue
            self._log(f"Error in _update_auto_test_buttons: {e}", "error")
    
    # ---------- NI DAQ ----------
    def refresh_ni_devices(self):
        """Refresh NI DAQ devices and channels - SIMPLIFIED AND GUARANTEED"""
        self._log("=== REFRESH NI DEVICES START ===", "info")
        
        # Check if UI elements exist
        if not hasattr(self.ui, 'daqDevice_CB') or self.ui.daqDevice_CB is None:
            self._log("ERROR: daqDevice_CB not found in UI", "error")
            return
            
        if not hasattr(self.ui, 'daqChannel_CB') or self.ui.daqChannel_CB is None:
            self._log("ERROR: daqChannel_CB not found in UI", "error")
            return
        
        self._log("UI elements found, proceeding...", "info")
        
        # Clear and populate channels first
        self.ui.daqChannel_CB.clear()
        standard_channels = [f"ai{i}" for i in range(8)]
        self.ui.daqChannel_CB.addItems(standard_channels)
        self.ui.daqChannel_CB.setCurrentText("ai0")
        self._log(f"Added {len(standard_channels)} channels", "info")
        
        # Clear devices and detect actual devices
        self.ui.daqDevice_CB.clear()
        self._log("Cleared daqDevice_CB", "info")
        
        # Try to get actual devices from service
        try:
            self._log("Attempting to get devices from service...", "info")
            service_devices = self.ni_service.get_available_devices()
            
            if service_devices and len(service_devices) > 0:
                self._log(f"Service returned {len(service_devices)} devices", "info")
                for device in service_devices:
                    # Clean device name - remove any parenthetical info
                    clean_device = device.split(' (')[0].split(' [')[0].strip()
                    self.ui.daqDevice_CB.addItem(clean_device)
                    self._log(f"   Added: {clean_device}", "info")
            else:
                self._log("Service returned no devices", "warn")
                
        except Exception as e:
            self._log(f"Service call failed: {e}", "error")
        
        # STEP 3: Final verification
        final_count = self.ui.daqDevice_CB.count()
        self._log(f"=== FINAL RESULT: {final_count} devices in combo box ===", "info")
        
        for i in range(final_count):
            item_text = self.ui.daqDevice_CB.itemText(i)
            self._log(f"   [{i}] {item_text}", "info")
        
        if final_count == 0:
            self._log("WARNING: No NI DAQ devices detected. Check hardware connections and drivers.", "warning")
        
        self._log("=== REFRESH NI DEVICES COMPLETE ===", "info")
    
    def toggle_ni_connection(self):
        """Toggle NI DAQ connection"""
        if not hasattr(self.ui, 'daqConnect_PB') or not self.ui.daqConnect_PB:
            return
            
        if self.ni_service.is_connected():
            # Disconnect
            self.ni_service.disconnect_device()
            self.ui.daqConnect_PB.setText("Connect")
            self._log("NI DAQ disconnected", "info")
            
            # Update color to red after disconnect
            if hasattr(self.ui, 'niCurrentGroupBox') and self.ui.niCurrentGroupBox:
                self.ui.niCurrentGroupBox.setStyleSheet("""
                    QGroupBox::title {
                        color: #ff6b6b;
                        font-weight: bold;
                        font-size: 9pt;
                    }
                """)
        else:
            # Connect
            if not hasattr(self.ui, 'daqDevice_CB') or not hasattr(self.ui, 'daqChannel_CB'):
                self._log("ERROR: NI DAQ UI elements not found", "error")
                return
                
            device = self.ui.daqDevice_CB.currentText().strip()
            channel = self.ui.daqChannel_CB.currentText().strip()
            
            self._log(f"Attempting NI DAQ connection...", "info")
            self._log(f"   Device: '{device}'", "info")
            self._log(f"   Channel: '{channel}'", "info")
            
            # Validate inputs
            if not device:
                self._log("ERROR: No device selected", "error")
                return
            if not channel:
                self._log("ERROR: No channel selected", "error")
                return
            if device in ["No devices found", "Error detecting devices"]:
                self._log("ERROR: Invalid device selection", "error")
                return
            if "Error:" in device or "not installed" in device:
                self._log("ERROR: Device has error status", "error")
                return
            if not channel.startswith('ai'):
                self._log(f"ERROR: Invalid channel format '{channel}' - should be 'ai0', 'ai1', etc.", "error")
                return
            
            if device and channel:
                success = self.ni_service.connect_device(device, channel)
                if success:
                    
                    # Get detailed device info
                    device_info = self.ni_service.get_device_info()
                    clean_device = device_info.get('device_name', device.split(' (')[0])
                    
                    self._log(f"NI DAQ connected successfully!", "success")
                    self._log(f"   Device: {clean_device}", "success")
                    self._log(f"   Channel: {channel}", "success")
                    self._log(f"   Voltage Range: ±{self.ni_service.voltage_range}V", "info")
                    
                    # Update color to green after successful connection
                    if hasattr(self.ui, 'niCurrentGroupBox') and self.ui.niCurrentGroupBox:
                        self.ui.niCurrentGroupBox.setStyleSheet("""
                            QGroupBox::title {
                                color: #4CAF50;
                                font-weight: bold;
                                font-size: 9pt;
                            }
                        """)
                else:
                    self._log(f"ERROR: Failed to connect to {device}/{channel}", "error")
                    self._log("   Check device connections and drivers", "error")
                    
                    # Update color to red after failed connection
                    if hasattr(self.ui, 'niCurrentGroupBox') and self.ui.niCurrentGroupBox:
                        self.ui.niCurrentGroupBox.setStyleSheet("""
                            QGroupBox::title {
                                color: #ff6b6b;
                                font-weight: bold;
                                font-size: 9pt;
                            }
                        """)
            else:
                if "No devices found" in device:
                    self._log("ERROR: No NI DAQ devices available", "error")
                    self._log("   Check hardware connections and NI-DAQmx drivers", "error")
                elif "Error:" in device:
                    self._log("ERROR: NI DAQ system error detected", "error")
                else:
                    self._log("ERROR: Invalid device selection", "error")
                # 잘못된 선택 시에도 상태 업데이트
                self._update_ni_status()
    
    def toggle_monitoring(self):
        """Toggle HVPM real-time V/I/P reading (no graphs)"""
        if not hasattr(self.ui, 'startMonitoring_PB') or not self.ui.startMonitoring_PB:
            return
            
        # Simple HVPM V/I/P monitoring without graphs
        if hasattr(self, '_hvpm_monitoring_active') and self._hvpm_monitoring_active:
            # Stop HVPM monitoring
            self._hvpm_monitoring_active = False
            if hasattr(self, '_hvpm_monitor_timer'):
                self._hvpm_monitor_timer.stop()
            self.ui.startMonitoring_PB.setText("Start Monitor")
            self._log("HVPM V/I/P monitoring stopped", "info")
        else:
            # Start HVPM monitoring
            if hasattr(self.hvpm_service, 'pm') and self.hvpm_service.pm:
                self._start_hvpm_monitoring()
                self.ui.startMonitoring_PB.setText("Stop Monitor")
                self._log("HVPM V/I/P monitoring started", "info")
            else:
                self._log("ERROR: HVPM not connected", "error")
                QtWidgets.QMessageBox.warning(
                    self, 
                    "Connection Required", 
                    "Please connect to HVPM device before starting monitoring."
                )
    
    def _start_hvpm_monitoring(self):
        """Start simple HVPM V/I/P monitoring"""
        self._hvpm_monitoring_active = True
        self._hvpm_monitor_timer.start()
        
    def _on_hvpm_monitor_tick(self):
        """Update HVPM V/I/P display every second"""
        try:
            if not (hasattr(self.hvpm_service, 'pm') and self.hvpm_service.pm):
                self._log("WARNING: HVPM connection lost during monitoring", "warn")
                self.toggle_monitoring()  # Stop monitoring
                return
                
            # Read HVPM values
            v, i = self.hvpm_service.read_vi(log_callback=None)  # No logging for continuous updates
            
            if v is not None and i is not None:
                # Update displays
                self.hvpm_service.last_set_vout = v
                self.hvpm_service._update_volt_label()
                
                # Update current display
                if hasattr(self.ui, 'hvpmCurrent_LB') and self.ui.hvpmCurrent_LB:
                    self.ui.hvpmCurrent_LB.setText(f"{i:.3f} A")
                
                # Update power display
                if hasattr(self.ui, 'hvpmPower_LB') and self.ui.hvpmPower_LB:
                    power = v * i
                    self.ui.hvpmPower_LB.setText(f"{power:.3f} W")
                    
        except Exception as e:
            self._log(f"ERROR: HVPM monitoring error: {e}", "error")
            self.toggle_monitoring()  # Stop monitoring on error
    
    def _on_ni_current_updated(self, current: float):
        """Handle NI current reading update"""
        if hasattr(self.ui, 'niCurrent_LB') and self.ui.niCurrent_LB:
            self.ui.niCurrent_LB.setText(f"{current:.3f} A")
    
    def toggle_ni_monitoring(self):
        """Toggle NI DAQ monitoring"""
        if not hasattr(self.ui, 'niMonitor_PB') or not self.ui.niMonitor_PB:
            return
            
        if self.ni_service.is_monitoring():
            # Stop monitoring
            self.ni_service.stop_monitoring()
            self.ui.niMonitor_PB.setText("Start Monitor")
            self._log("NI monitoring stopped", "info")
            self._measurement_mode = "hvpm" if self._graphActive else "none"
        else:
            # Start monitoring
            if self.ni_service.is_connected():
                # 충돌 경고 표시 (독립적이지만 동시 사용 시 알림)
                if self._graphActive and self._show_conflict_warning:
                    self._log("INFO: HVPM and NI DAQ monitoring running independently", "info")
                    self._log("NOTE: Both systems can run simultaneously", "info")
                
                self._ni_monitoring = True
                
                success = self.ni_service.start_monitoring(1000)  # 1 second interval
                if success:
                    self.ui.niMonitor_PB.setText("Stop Monitor")
                    self._log("NI monitoring started", "info")
            else:
                self._log("ERROR: NI DAQ not connected", "error")
        
        self._update_ni_status()
        self._update_measurement_mode_status()
    
    def _update_ni_status(self):
        """Update NI DAQ status display and button colors"""
        # Update status label
        if hasattr(self.ui, 'niStatus_LB') and self.ui.niStatus_LB:
            if self.ni_service.is_connected():
                # Get device info for display
                device_info = self.ni_service.get_device_info()
                device_name = device_info.get('device_name', 'Unknown')
                channel = device_info.get('channel', 'ai0')
                
                if self.ni_service.is_monitoring():
                    self.ui.niStatus_LB.setText(f"Monitoring: {device_name}/{channel}")
                    self.ui.niStatus_LB.setStyleSheet("font-weight: bold; font-size: 10pt; color: #4CAF50;")
                else:
                    self.ui.niStatus_LB.setText(f"Connected: {device_name}/{channel}")
                    self.ui.niStatus_LB.setStyleSheet("font-weight: bold; font-size: 10pt; color: #FF9800;")
            else:
                self.ui.niStatus_LB.setText("Disconnected")
                self.ui.niStatus_LB.setStyleSheet("font-weight: bold; font-size: 10pt; color: #ff6b6b;")
        
        # Update connect button color and text based on actual connection status
        if hasattr(self.ui, 'daqConnect_PB') and self.ui.daqConnect_PB:
            if self.ni_service.is_connected():
                self.ui.daqConnect_PB.setText("Disconnect")
                self.ui.daqConnect_PB.setStyleSheet("""
                    QPushButton { 
                        background-color: #4CAF50; 
                        color: white; 
                        font-weight: bold; 
                        border-radius: 5px; 
                        font-size: 9pt;
                    }
                    QPushButton:hover { 
                        background-color: #45a049; 
                    }
                """)
            else:
                self.ui.daqConnect_PB.setText("Connect")
                self.ui.daqConnect_PB.setStyleSheet("""
                    QPushButton { 
                        background-color: #f44336; 
                        color: white; 
                        font-weight: bold; 
                        border-radius: 5px; 
                        font-size: 9pt;
                    }
                    QPushButton:hover { 
                        background-color: #da190b; 
                    }
                """)
    
    def _on_ni_connection_changed(self, connected: bool):
        """Handle NI DAQ connection status change"""
        if hasattr(self.ui, 'daqConnect_PB') and self.ui.daqConnect_PB:
            self.ui.daqConnect_PB.setText("Connected" if connected else "Connect")
        self._update_ni_status()
    
    def _on_ni_error(self, error_msg: str):
        """Handle NI DAQ errors"""
        self._log(f"ERROR: NI DAQ Error: {error_msg}", "error")
    
    def _update_measurement_mode_status(self):
        """Update status bar with current measurement mode"""
        hvpm_active = self._graphActive
        ni_active = self.ni_service.is_monitoring() if self.ni_service else False
        
        if hvpm_active and ni_active:
            message = "HVPM & NI DAQ monitoring active (independent)"
        elif hvpm_active:
            message = "HVPM monitoring active"
        elif ni_active:
            message = "NI DAQ monitoring active"
        else:
            message = "No active monitoring"
        
        self.ui.statusbar.showMessage(message, 3000)

    # ---------- 로그 ----------
    def _log(self, msg: str, level: str = "info"):
        """
        Enhanced logging with better formatting and stability
        
        THREAD SAFE: This method is connected via QueuedConnection,
        so Qt automatically ensures it runs in the main thread.
        No manual thread checking needed!
        """
        try:
            timestamp = time.strftime("%H:%M:%S")
            formatted_msg = f"[{timestamp}] {msg}"
            
            # Limit log entries to prevent memory issues
            if self.ui.log_LW.count() > 1000:
                # Remove oldest entries when limit reached
                for i in range(100):  # Remove 100 oldest entries
                    item = self.ui.log_LW.takeItem(0)
                    if item:
                        del item
            
            item = QtWidgets.QListWidgetItem(formatted_msg)
            
            # Set colors based on level
            try:
                color = theme.get_status_color(level)
                item.setForeground(QColor(color))
            except Exception:
                # Fallback color if theme fails
                default_colors = {
                    'error': '#ff6b6b',
                    'warn': '#ffa726', 
                    'success': '#4caf50',
                    'info': '#ffffff'
                }
                color = default_colors.get(level, '#ffffff')
                item.setForeground(QColor(color))
            
            self.ui.log_LW.addItem(item)
            self.ui.log_LW.scrollToBottom()
            
            # Also update status bar for important messages
            if level in ['error', 'warn']:
                try:
                    self.ui.statusbar.showMessage(msg, 3000)
                except Exception:
                    pass  # Ignore status bar errors
                    
        except Exception as e:
            # Fallback logging to console if UI logging fails
            print(f"[{level.upper()}] {msg}")
            print(f"Logging error: {e}")

    # ---------- Graph ----------
    def start_graph(self):
        """Start enhanced graph monitoring"""
        if self._graphActive:
            return
            
        # Check if HVPM is connected
        if not (hasattr(self.hvpm_service, 'pm') and self.hvpm_service.pm):
            QtWidgets.QMessageBox.warning(
                self, 
                "Connection Required", 
                "Please connect to HVPM device before starting monitoring."
            )
            return
            
        self._tbuf.clear()
        self._vbuf.clear()
        self._ibuf.clear()
        self._t0 = time.perf_counter()
        
        # Update UI state
        if hasattr(self.ui, 'readVoltCurrent_PB') and self.ui.readVoltCurrent_PB:
            self.ui.readVoltCurrent_PB.setEnabled(False)
        if hasattr(self.ui, 'startGraph_PB') and self.ui.startGraph_PB:
            self.ui.startGraph_PB.setEnabled(False)
        if hasattr(self.ui, 'stopGraph_PB') and self.ui.stopGraph_PB:
            self.ui.stopGraph_PB.setEnabled(True)
        
        self._graphActive = True
        self._graphTimer.start()
        
        self._log("Real-time monitoring started (10 Hz)", "info")
        self.ui.statusbar.showMessage("Monitoring active - Collecting data...", 0)

    def stop_graph(self):
        """Stop graph monitoring"""
        if not self._graphActive:
            return
            
        self._graphTimer.stop()
        self._graphActive = False
        
        # Update measurement mode
        self._measurement_mode = "ni_daq" if self.ni_service.is_monitoring() else "none"
        self._update_measurement_mode_status()
        
        # Update UI state
        if hasattr(self.ui, 'readVoltCurrent_PB') and self.ui.readVoltCurrent_PB:
            self.ui.readVoltCurrent_PB.setEnabled(True)
        if hasattr(self.ui, 'startGraph_PB') and self.ui.startGraph_PB:
            self.ui.startGraph_PB.setEnabled(True)
        if hasattr(self.ui, 'stopGraph_PB') and self.ui.stopGraph_PB:
            self.ui.stopGraph_PB.setEnabled(False)
        
        self._log("Real-time monitoring stopped", "info")
        self.ui.statusbar.showMessage("Monitoring stopped", 3000)

    def _on_graph_tick(self):
        """Enhanced graph tick with better error handling"""
        try:
            # Check connection
            svc = self.hvpm_service
            if not (getattr(svc, "pm", None) and getattr(svc, "engine", None)):
                self._log("WARNING: Connection lost during monitoring", "warn")
                self.stop_graph()
                return

            # Read voltage and current
            v, i = self.hvpm_service.read_vi(log_callback=self._log)

            # Validate data
            try:
                v = float(v) if v is not None else float("nan")
                i = float(i) if i is not None else float("nan")
            except Exception:
                v = float("nan")
                i = float("nan")

            if not math.isfinite(v) and not math.isfinite(i):
                if not hasattr(self, "_graphWarnedNaN") or not self._graphWarnedNaN:
                    self._graphWarnedNaN = True
                    self._log("WARNING: Invalid data received - skipping update", "warn")
                return

            # Update buffers
            t = time.perf_counter() - (self._t0 or time.perf_counter())
            self._tbuf.append(t)
            
            if math.isfinite(v):
                self._vbuf.append(v)
            if math.isfinite(i):
                self._ibuf.append(i)

            # Update plots with enhanced styling
            self.update_plot_data()

        except Exception as e:
            self._log(f"ERROR: Graph update failed: {e}", "error")

    def update_plot_data(self):
        """Update plot data with enhanced visualization"""
        tb = list(self._tbuf)
        vb = list(self._vbuf)
        ib = list(self._ibuf)
        
        # Update voltage plot
        if vb:
            xv = tb[-len(vb):]
            self._curve_v.setData(xv, vb)
            
            # Auto-scale with padding
            vmin, vmax = min(vb), max(vb)
            if vmin == vmax:
                pad = max(0.05, abs(vmax) * 0.05)
                vmin -= pad
                vmax += pad
            self._plot_v.setYRange(vmin, vmax, padding=0.1)

        # Update current plot
        if ib:
            xi = tb[-len(ib):]
            self._curve_i.setData(xi, ib)
            
            # Auto-scale with padding
            imin, imax = min(ib), max(ib)
            if imin == imax:
                pad_i = max(0.01, abs(imax) * 0.1)
                imin -= pad_i
                imax += pad_i
            self._plot_i.setYRange(imin, imax, padding=0.1)

        # Update X-axis (show last 30 seconds)
        if tb:
            tmax = tb[-1]
            tmin = max(0.0, tmax - 30.0)
            self._plot_v.setXRange(tmin, tmax, padding=0.01)
            self._plot_i.setXRange(tmin, tmax, padding=0.01)

    # ---------- ADB ----------
    def refresh_adb_ports(self):
        """Enhanced ADB port refresh"""
        self._refreshing_adb = True
        self.ui.comport_CB.clear()
        
        try:
            devices = adb.list_devices()
        except Exception as e:
            devices = []
            self._log(f"ERROR: ADB Error: {e}", "error")

        if devices:
            self.ui.comport_CB.addItems(devices)
            self.ui.comport_CB.setCurrentIndex(0)
            self.selected_device = devices[0]
            self._log(f"ADB device selected: {self.selected_device}", "info")
            
            # Update auto test service
            self.auto_test_service.set_device(self.selected_device)
        else:
            self.ui.comport_CB.addItem("No devices found")
            self.selected_device = None
            self._log("WARNING: No ADB devices found", "warn")
            
        self._refreshing_adb = False
        self._update_auto_test_buttons()

    def _on_device_selected(self):
        """Handle ADB device selection"""
        if self._refreshing_adb:
            return
            
        device = self.ui.comport_CB.currentText().strip()
        if device and device != "No devices found":
            self.selected_device = device
            self._log(f"ADB device changed: {device}", "info")
            self.auto_test_service.set_device(device)
        else:
            self.selected_device = None
            self._log("WARNING: No ADB device selected", "warn")
        
        self._update_auto_test_buttons()

    # ---------- HVPM ----------
    def handle_read_voltage_current(self):
        """Read both voltage and current"""
        if hasattr(self.ui, 'readVoltCurrent_PB') and self.ui.readVoltCurrent_PB:
            self.ui.readVoltCurrent_PB.setEnabled(False)
            self.ui.readVoltCurrent_PB.setText("Reading...")
        
        try:
            # Read HVPM voltage and current
            v, i = self.hvpm_service.read_vi(log_callback=self._log)
            
            if v is not None:
                self.hvpm_service.last_set_vout = v
                self.hvpm_service.enabled = v > 0
                self.hvpm_service._update_volt_label()
                
                # Update current display
                if hasattr(self.ui, 'hvpmCurrent_LB') and self.ui.hvpmCurrent_LB:
                    if i is not None:
                        self.ui.hvpmCurrent_LB.setText(f"{i:.3f} A")
                    else:
                        self.ui.hvpmCurrent_LB.setText("__.__ A")
                
                # Update power display
                if hasattr(self.ui, 'hvpmPower_LB') and self.ui.hvpmPower_LB:
                    if v is not None and i is not None:
                        power = v * i
                        self.ui.hvpmPower_LB.setText(f"{power:.3f} W")
                    else:
                        self.ui.hvpmPower_LB.setText("__.__ W")
                
                self._log(f"HVPM - Voltage: {v:.3f}V, Current: {i:.3f}A", "info")
                self.ui.statusbar.showMessage(f"HVPM - V: {v:.3f}V, I: {i:.3f}A", 3000)
            else:
                self._log("ERROR: Failed to read HVPM values", "error")
            
            # NI DAQ reading removed - HVPM Read V&I should only read HVPM
            # No NI DAQ interaction needed for HVPM-only operation
                
        except Exception as e:
            self._log(f"ERROR: Read error: {e}", "error")
        finally:
            if hasattr(self.ui, 'readVoltCurrent_PB') and self.ui.readVoltCurrent_PB:
                self.ui.readVoltCurrent_PB.setEnabled(True)
                self.ui.readVoltCurrent_PB.setText("Read V&I")

    def handle_set_voltage(self):
        """Enhanced voltage setting with validation"""
        try:
            voltage_text = self.ui.hvpmVolt_LE.text().strip()
            if not voltage_text:
                QtWidgets.QMessageBox.warning(self, "Input Required", "Please enter a voltage value.")
                return
                
            volts = float(voltage_text)
            
            # Validate voltage range (adjust as needed)
            if volts < 0 or volts > 50:  # Example range
                reply = QtWidgets.QMessageBox.question(
                    self, 
                    "Voltage Warning", 
                    f"Voltage {volts}V is outside normal range (0-50V). Continue?",
                    QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
                )
                if reply == QtWidgets.QMessageBox.StandardButton.No:
                    return
                    
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for voltage.")
            return

        self.ui.setVolt_PB.setEnabled(False)
        self.ui.setVolt_PB.setText("⚡ Setting...")
        
        try:
            ok = self.hvpm_service.set_voltage(volts, log_callback=self._log)
            if not ok:
                QtWidgets.QMessageBox.warning(self, "HVPM Error", "Failed to set voltage")
                return
                
            # Read back for verification
            rb = self.hvpm_service.read_voltage(log_callback=self._log)
            if rb is not None:
                self.hvpm_service.last_set_vout = rb
                self.hvpm_service.enabled = rb > 0
                self.hvpm_service._update_volt_label()
                self._log(f"⚡ Voltage set to {volts}V, readback: {rb:.3f}V", "success")
                self.ui.statusbar.showMessage(f"Voltage set: {rb:.3f}V", 3000)
            else:
                self._log(f"⚡ Voltage set to {volts}V (readback failed)", "warn")
                
        finally:
            self.ui.setVolt_PB.setEnabled(True)
            self.ui.setVolt_PB.setText("⚡ Set")

    # ---------- Auto Test ----------
    def _on_voltage_config_changed(self):
        """Handle voltage configuration changes"""
        # Voltage configuration is now handled through settings dialog
        self.auto_test_service.set_voltages(
            self.test_config['stabilization_voltage'],
            self.test_config['test_voltage']
        )

    def _on_start_test_button_clicked(self):
        """Handle start test button click with additional logging"""
        import traceback
        stack_trace = ''.join(traceback.format_stack()[-3:-1])  # Get caller info
        self._log(f"🖱️ Start test button clicked! Call stack:\n{stack_trace}", "info")
        
        # Check if we're in a completion callback
        if any("_on_auto_test_completed" in line for line in stack_trace.split('\n')):
            self._log("⚠️ Button clicked from test completion callback - ignoring!", "warn")
            return
            
        self.start_auto_test()

    def start_auto_test(self):
        """Start automated test with selected scenario"""
        self._log(f"🚀 start_auto_test called", "info")
        
        # Check if test scenario engine is running
        if self.test_scenario_engine.is_running():
            self._log(f"⚠️ Test already running, ignoring start request", "warn")
            return
        
        # Check device connections first
        connection_errors = []
        
        # Check HVPM connection
        try:
            if not (hasattr(self.hvpm_service, 'pm') and self.hvpm_service.pm):
                connection_errors.append("HVPM device not connected")
        except Exception as e:
            connection_errors.append(f"HVPM connection error: {e}")
        
        # Check ADB connection
        try:
            if not self.selected_device or self.selected_device == "No devices found":
                connection_errors.append("ADB device not connected")
        except Exception as e:
            connection_errors.append(f"ADB connection error: {e}")
        
        # Show connection errors if any
        if connection_errors:
            error_msg = "Device connection issues:\n\n" + "\n".join(f"• {error}" for error in connection_errors)
            error_msg += "\n\nPlease connect all required devices and try again."
            QtWidgets.QMessageBox.warning(self, "Connection Required", error_msg)
            return
        
        # Check if any scenario is selected
        if self.ui.testScenario_CB.count() == 0 or not self.ui.testScenario_CB.isEnabled():
            QtWidgets.QMessageBox.warning(self, "No Scenario", "No test scenarios available.")
            return
            
        current_text = self.ui.testScenario_CB.currentText()
        if current_text == "No test scenarios available":
            QtWidgets.QMessageBox.warning(self, "No Scenario", "No test scenarios available.")
            return
        
        # Get selected scenario
        scenario_name = self.ui.testScenario_CB.currentText()
        scenario_key = self.ui.testScenario_CB.currentData()
        
        if not scenario_key:
            QtWidgets.QMessageBox.warning(self, "Invalid Scenario", "Selected scenario is not properly configured.")
            return
        
        # Confirm test start
        reply = QtWidgets.QMessageBox.question(
            self,
            "Start Auto Test",
            f"Start test scenario: {scenario_name}?\n\n"
            f"This will control ADB device, HVPM, and DAQ automatically.\n"
            f"Make sure all required devices are connected and configured properly.\n\n"
            f"Test duration: Approximately 1-2 minutes",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return
        
        try:
            # Start the test using test scenario engine
            success = self.test_scenario_engine.start_test(scenario_key)
            
            if success:
                self._log(f"Test scenario started: {scenario_name}", "info")
                
                # Disable all UI controls except Stop button during test
                self._log("=== SETTING UI TEST MODE: TRUE ===", "info")
                self._set_ui_test_mode(True)
                self._log("=== UI TEST MODE SET COMPLETE ===", "info")
                
                # Update test status display
                if hasattr(self.ui, 'testProgress_PB') and self.ui.testProgress_PB:
                    self.ui.testProgress_PB.setValue(0)
                if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
                    self.ui.testStatus_LB.setText("Test scenario running...")
                    self.ui.testStatus_LB.setStyleSheet("font-size: 11pt; color: #4CAF50; font-weight: bold;")
                
                # Update Auto Test group box title to show running status
                if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                    self.ui.autoTestGroupBox.setTitle("Auto Test - RUNNING")
                
                # Update status bar
                self.ui.statusbar.showMessage(f"Running Auto Test: {scenario_name}", 0)
                
                # Log with enhanced formatting
                self._log(f"🎯 Starting automated test: {scenario_name}", "info")
                if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
                    timestamp = time.strftime("%H:%M:%S")
                    self.ui.testResults_TE.append(f"[{timestamp}] Test Started: {scenario_name}")
                    self._log(f"📝 Added to testResults_TE: Test Started: {scenario_name}", "debug")
            else:
                self._log(f"Failed to start test scenario: {scenario_name}", "error")
                QtWidgets.QMessageBox.critical(self, "Test Error", f"Failed to start test scenario: {scenario_name}")
            
        except Exception as e:
            self._log(f"Failed to start test scenario: {e}", "error")
            QtWidgets.QMessageBox.critical(self, "Test Error", f"Failed to start test:\n{e}")

    def stop_auto_test(self):
        """Stop automated test"""
        if not self.test_scenario_engine.is_running():
            return
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Stop Test Scenario",
            "Are you sure you want to stop the current test scenario?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            success = self.test_scenario_engine.stop_test()
            if success:
                self._log("Test scenario stopped by user", "info")
            else:
                self._log("Failed to stop test scenario", "error")
            
            # Re-enable all UI controls after test stop
            self._set_ui_test_mode(False)
            
            # Update test status
            if hasattr(self.ui, 'testProgress_PB') and self.ui.testProgress_PB:
                self.ui.testProgress_PB.setValue(0)
            if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
                self.ui.testStatus_LB.setText("Test stopped by user")
                self.ui.testStatus_LB.setStyleSheet("font-size: 11pt; color: #FF9800; font-weight: bold;")
            
            # Update Auto Test group box title
            if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                self.ui.autoTestGroupBox.setTitle("Auto Test - STOPPED")
            
            # Update status bar
            self.ui.statusbar.showMessage("Auto Test Stopped", 3000)
            
            # Add to test results
            if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
                timestamp = time.strftime("%H:%M:%S")
                self.ui.testResults_TE.append(f"[{timestamp}] Test stopped by user")

    def _on_auto_test_progress(self, progress: int, status: str):
        """Handle auto test progress updates"""
        if hasattr(self.ui, 'testProgress_PB') and self.ui.testProgress_PB:
            self.ui.testProgress_PB.setValue(progress)
        
        if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
            # Add progress indicator and color coding
            if progress < 30:
                color = "#FF9800"  # Orange for initialization
            elif progress < 70:
                color = "#2196F3"  # Blue for in progress
            else:
                color = "#4CAF50"  # Green for near completion
            
            formatted_status = f"{status} ({progress}%)"
            self.ui.testStatus_LB.setText(formatted_status)
            self.ui.testStatus_LB.setStyleSheet(f"font-size: 11pt; color: {color}; font-weight: bold;")
        
        # Update status bar with progress
        self.ui.statusbar.showMessage(f"Auto Test Running: {progress}% - {status}", 0)
        
        # Add to test results with 1-second interval logging
        current_time = time.time()
        if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
            if current_time - self.last_timestamp_log >= 1.0:  # 1 second interval
                timestamp = time.strftime("%H:%M:%S")
                self.ui.testResults_TE.append(f"[{timestamp}] {progress}% - {status}")
                self.last_timestamp_log = current_time

    def _on_auto_test_completed(self, success: bool, message: str):
        """Handle auto test completion"""
        self._log(f"🔔 _on_auto_test_completed called: success={success}, message={message}", "info")
        
        # Check test engine status before updating
        if hasattr(self, 'test_scenario_engine'):
            engine_status = self.test_scenario_engine.get_status()
            engine_running = self.test_scenario_engine.is_running()
            self._log(f"📊 Test engine status: {engine_status.value}, is_running: {engine_running}", "info")
            
            # Log current test info
            current_test = self.test_scenario_engine.get_current_test()
            if current_test:
                self._log(f"📋 Current test: {current_test.scenario_name}, status: {current_test.status.value if hasattr(current_test.status, 'value') else current_test.status}", "info")
        
        # Re-enable all UI controls after test completion
        self._set_ui_test_mode(False)
        
        # Update test results display
        if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
            timestamp = time.strftime("%H:%M:%S")
            result_text = f"[{timestamp}] Test {'PASSED' if success else 'FAILED'}: {message}\n"
            self.ui.testResults_TE.append(result_text)
        
        # Save test results
        self._save_test_results(success, message)
        
        # Get test data from scenario engine
        test_result = self.test_scenario_engine.get_current_test()
        if test_result and test_result.daq_data:
            self._log(f"Test completed with {len(test_result.daq_data)} data points", "info")
        
        # Show temporary completion status first
        if hasattr(self.ui, 'testProgress_PB') and self.ui.testProgress_PB:
            self.ui.testProgress_PB.setValue(100 if success else 0)
        
        if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
            if success:
                self.ui.testStatus_LB.setText("Test completed successfully")
                self.ui.testStatus_LB.setStyleSheet("font-size: 11pt; color: #4CAF50; font-weight: bold;")
            else:
                self.ui.testStatus_LB.setText("Test failed")
                self.ui.testStatus_LB.setStyleSheet("font-size: 11pt; color: #F44336; font-weight: bold;")
        
        # Force Auto Test group box title update
        if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
            if success:
                self.ui.autoTestGroupBox.setTitle("Auto Test - COMPLETED")
            else:
                self.ui.autoTestGroupBox.setTitle("Auto Test - FAILED")
            self._log(f"Auto Test GroupBox title updated to: {self.ui.autoTestGroupBox.title()}", "info")
        
        # Update status bar and show completion message
        if success:
            self.ui.statusbar.showMessage("Auto Test Completed Successfully", 5000)
            
            # Show simple completion message (no save dialog - results already auto-saved)
            QtWidgets.QMessageBox.information(
                self, "Test Complete", 
                f"Automated test completed successfully!\n\n{message}\n\nResults have been automatically saved to CSV."
            )
        else:
            # Update status bar
            self.ui.statusbar.showMessage("Auto Test Failed", 5000)
            
            QtWidgets.QMessageBox.warning(self, "Test Failed", f"Automated test failed:\n\n{message}")
        
        # Reset UI to initial state after dialog (with delay)
        QTimer.singleShot(1000, self._reset_ui_to_initial_state)
    
    def _force_ui_refresh(self):
        """Force UI refresh to ensure state changes are visible"""
        try:
            # Process all pending Qt events
            QtWidgets.QApplication.processEvents()
            
            # Force button state update
            self._update_auto_test_buttons()
            
            # Force repaint of UI elements
            if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                self.ui.autoTestGroupBox.repaint()
            if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
                self.ui.testStatus_LB.repaint()
                
            self._log("UI refresh completed", "debug")
        except Exception as e:
            self._log(f"Error during UI refresh: {e}", "error")

    def _reset_ui_to_initial_state(self):
        """Reset UI to initial state after test completion"""
        try:
            self._log("🔄 Resetting UI to initial state", "info")
            
            # Double-check that test is actually completed
            if hasattr(self, 'test_scenario_engine'):
                if self.test_scenario_engine.is_running():
                    self._log("⚠️ Test still running, skipping UI reset", "warn")
                    return
                engine_status = self.test_scenario_engine.get_status()
                self._log(f"📊 Engine status during reset: {engine_status.value}", "info")
            
            # Reset testStatus_LB to original "Ready" state
            if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
                self.ui.testStatus_LB.setText("Ready")
                self.ui.testStatus_LB.setStyleSheet("")  # Remove custom styling
                self._log("testStatus_LB reset to 'Ready'", "info")
            
            # Reset progress bar to 0
            if hasattr(self.ui, 'testProgress_PB') and self.ui.testProgress_PB:
                self.ui.testProgress_PB.setValue(0)
                self._log("testProgress_PB reset to 0", "info")
            
            # Reset Auto Test group box title
            if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                self.ui.autoTestGroupBox.setTitle("Auto Test")
                self._log("autoTestGroupBox title reset to 'Auto Test'", "info")
            
            # Re-enable all UI controls and update button states
            self._set_ui_test_mode(False)
            
            # Force UI refresh
            QtWidgets.QApplication.processEvents()
            
            self._log("UI reset to initial state completed", "info")
            
        except Exception as e:
            self._log(f"Error resetting UI to initial state: {e}", "error")

    def _set_ui_test_mode(self, test_running: bool):
        """Set UI controls state during test execution"""
        try:
            self._log(f"Setting UI test mode: test_running={test_running}", "info")
            
            # Auto Test buttons - Force state change
            if hasattr(self.ui, 'startAutoTest_PB') and self.ui.startAutoTest_PB:
                self.ui.startAutoTest_PB.setEnabled(not test_running)
                # Force repaint to ensure visual update
                self.ui.startAutoTest_PB.repaint()
                self._log(f"*** startAutoTest_PB enabled: {not test_running} ***", "info")
                
            if hasattr(self.ui, 'stopAutoTest_PB') and self.ui.stopAutoTest_PB:
                self.ui.stopAutoTest_PB.setEnabled(test_running)
                # Force repaint to ensure visual update
                self.ui.stopAutoTest_PB.repaint()
                self._log(f"*** stopAutoTest_PB enabled: {test_running} ***", "info")
                
                # Additional styling for emphasis during test
                if test_running:
                    self.ui.stopAutoTest_PB.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")
                else:
                    self.ui.stopAutoTest_PB.setStyleSheet("")  # Reset to default
            
            # Test scenario selection
            if hasattr(self.ui, 'testScenario_CB') and self.ui.testScenario_CB:
                self.ui.testScenario_CB.setEnabled(not test_running)
            
            # HVPM controls
            hvpm_controls = [
                'hvpmVolt_LE', 'setVolt_PB', 'readVoltCurrent_PB', 
                'hvpmOn_PB', 'hvpmOff_PB'
            ]
            for control_name in hvpm_controls:
                if hasattr(self.ui, control_name):
                    control = getattr(self.ui, control_name)
                    if control:
                        control.setEnabled(not test_running)
            
            # ADB controls
            adb_controls = [
                'comport_CB', 'refreshADB_PB'
            ]
            for control_name in adb_controls:
                if hasattr(self.ui, control_name):
                    control = getattr(self.ui, control_name)
                    if control:
                        control.setEnabled(not test_running)
            
            # NI DAQ controls
            daq_controls = [
                'daqDevice_CB', 'daqChannel_CB', 'refreshNI_PB',
                'startDAQ_PB', 'stopDAQ_PB', 'measurementMode_CB'
            ]
            for control_name in daq_controls:
                if hasattr(self.ui, control_name):
                    control = getattr(self.ui, control_name)
                    if control:
                        control.setEnabled(not test_running)
            
            # Multi-channel monitor controls
            if hasattr(self, 'multi_channel_monitor') and self.multi_channel_monitor:
                try:
                    # Disable multi-channel monitor controls during test
                    for i in range(8):  # Assuming 8 channels
                        checkbox_name = f'channel_{i}_checkbox'
                        if hasattr(self.multi_channel_monitor, checkbox_name):
                            checkbox = getattr(self.multi_channel_monitor, checkbox_name)
                            if checkbox:
                                checkbox.setEnabled(not test_running)
                except Exception as e:
                    self._log(f"Error setting multi-channel monitor state: {e}", "debug")
            
            # Menu actions (if any)
            if hasattr(self.ui, 'menubar') and self.ui.menubar:
                self.ui.menubar.setEnabled(not test_running)
            
            # Force Qt to process all pending events and repaint
            QtWidgets.QApplication.processEvents()
            QtWidgets.QApplication.processEvents()  # Call twice to ensure processing
            
            self._log(f"UI test mode set successfully: test_running={test_running}", "info")
            
        except Exception as e:
            self._log(f"Error setting UI test mode: {e}", "error")

    def _save_test_results(self, success: bool, message: str):
        """Save test results - txt file saving disabled (Excel only)"""
        # Disabled: Results are now saved in Excel format by test_scenario_engine
        # No more txt files cluttering the test_results folder
        pass
    
    def _export_test_results(self):
        """Export detailed test results with measurement data"""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Test Results", f"test_results_{time.strftime('%Y%m%d_%H%M%S')}.csv", 
            "CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    if filename.endswith('.csv'):
                        # CSV format with measurement data
                        f.write("Timestamp,Voltage(V),Current(A),Test_Phase\n")
                        tb = list(self._tbuf)
                        vb = list(self._vbuf) 
                        ib = list(self._ibuf)
                        
                        max_len = max(len(vb), len(ib), len(tb)) if any([vb, ib, tb]) else 0
                        for i in range(max_len):
                            timestamp = tb[i] if i < len(tb) else ""
                            voltage = vb[i] if i < len(vb) else ""
                            current = ib[i] if i < len(ib) else ""
                            f.write(f"{timestamp},{voltage},{current},Test_Execution\n")
                    else:
                        # Text format
                        scenario_name = self.ui.testScenario_CB.currentText() if hasattr(self.ui, 'testScenario_CB') else "Unknown"
                        f.write(f"=== HVPM Auto Test Detailed Results ===\n")
                        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Test Scenario: {scenario_name}\n\n")
                        
                        if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
                            f.write("=== Test Log ===\n")
                            f.write(self.ui.testResults_TE.toPlainText())
                
                self._log(f"Detailed results exported to {filename}", "success")
                QtWidgets.QMessageBox.information(self, "Export Complete", f"Test results exported to:\n{filename}")
                
            except Exception as e:
                self._log(f"ERROR: Export failed: {e}", "error")
                QtWidgets.QMessageBox.warning(self, "Export Error", f"Failed to export results:\n{e}")

    def _on_voltage_stabilized(self, voltage: float):
        """Handle voltage stabilization notification"""
        self._log(f"Voltage stabilized at {voltage:.2f}V", "success")
        
        # Start data collection from test voltage point (skip stabilization data if configured)
        if self.test_config.get('skip_stabilization_data', True):
            self.test_data_collection_active = True
            self._log(f"Data collection started from test voltage point", "info")
    
    def _on_test_params_changed(self):
        """Handle test parameter changes"""
        # Test parameters are now handled through settings dialog
        cycles = self.test_config.get('test_cycles', 5)
        duration = self.test_config.get('test_duration', 10)
        
        self._log(f"Test parameters: Cycles={cycles}, Duration={duration}s", "info")
    
    def _on_scenario_changed(self):
        """Handle test scenario selection change"""
        scenario_data = self.ui.testScenario_CB.currentData()
        scenario_name = self.ui.testScenario_CB.currentText()
        
        # Log scenario selection for debugging
        self._log(f"Test scenario selected: {scenario_name}", "info")
        
        # Enable/disable start button based on scenario selection
        if hasattr(self.ui, 'startAutoTest_PB') and self.ui.startAutoTest_PB:
            if scenario_name and scenario_name not in ["No test scenarios available", "Test engine not ready"]:
                # Check if not currently running a test
                if hasattr(self, 'test_scenario_engine') and not self.test_scenario_engine.is_running():
                    self.ui.startAutoTest_PB.setEnabled(True)
                else:
                    self.ui.startAutoTest_PB.setEnabled(False)
            else:
                self.ui.startAutoTest_PB.setEnabled(False)
        
        if scenario_data:
            self._log(f"Test scenario selected: {scenario_name}", "info")
            
            # Update test parameters based on scenario (stored in settings)
            if "screen_onoff" in scenario_data:
                cycles = 10 if "long" in scenario_data else 5
                duration = 15 if "long" in scenario_data else 10
                self.test_config['test_cycles'] = cycles
                self.test_config['test_duration'] = duration
            elif "cpu_stress" in scenario_data:
                self.test_config['test_cycles'] = 1
                duration = 300 if "long" in scenario_data else 60
                self.test_config['test_duration'] = duration
            elif scenario_data == "custom_script":
                self.test_config['test_cycles'] = 1
                self.test_config['test_duration'] = 30
        else:
            self._log("WARNING: No scenario data found", "warn")

    def _check_ui_elements(self):
        """Debug function to check UI elements"""
        ui_elements = [
            'startAutoTest_PB', 'stopAutoTest_PB', 'testScenario_CB',
            'testProgress_PB', 'testStatus_LB', 'testResults_TE'
        ]
        
        missing_elements = []
        existing_elements = []
        for element in ui_elements:
            if not hasattr(self.ui, element) or getattr(self.ui, element) is None:
                missing_elements.append(element)
            else:
                existing_elements.append(element)
        
        if missing_elements:
            self._log(f"WARNING: Missing UI elements: {', '.join(missing_elements)}", "warn")
            self._log("Some auto test features may be limited", "warn")
        
        if existing_elements:
            self._log(f"Found UI elements: {', '.join(existing_elements)}", "info")
        
        # Check test scenario combo box items
        if hasattr(self.ui, 'testScenario_CB') and self.ui.testScenario_CB:
            count = self.ui.testScenario_CB.count()
            self._log(f"Test scenario combo box has {count} items", "info")
        
        # Log current test settings
        self._log(f"Test settings loaded: {self.test_config}", "info")

    # ---------- Menu Actions ----------
    def export_data(self):
        """Export collected data"""
        if not self._vbuf and not self._ibuf:
            QtWidgets.QMessageBox.information(self, "No Data", "No data available to export.")
            return
            
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Data", "hvpm_data.csv", "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write("Time(s),Voltage(V),Current(A)\n")
                    tb = list(self._tbuf)
                    vb = list(self._vbuf)
                    ib = list(self._ibuf)
                    
                    max_len = max(len(vb), len(ib))
                    for i in range(max_len):
                        t = tb[i] if i < len(tb) else ""
                        v = vb[i] if i < len(vb) else ""
                        curr = ib[i] if i < len(ib) else ""
                        f.write(f"{t},{v},{curr}\n")
                        
                self._log(f"Data exported to {filename}", "success")
                QtWidgets.QMessageBox.information(self, "Export Complete", f"Data exported to:\n{filename}")
            except Exception as e:
                self._log(f"ERROR: Export failed: {e}", "error")
                QtWidgets.QMessageBox.warning(self, "Export Error", f"Failed to export data:\n{e}")

    def toggle_theme(self):
        """Toggle between themes (placeholder)"""
        self._log("Theme toggle not implemented yet", "info")

    def reset_layout(self):
        """Reset window layout"""
        self.resize(1400, 900)
        self._log("Layout reset", "info")

    def quick_test(self):
        """Quick test shortcut"""
        if self.ui.testScenario_CB.count() > 0:
            self.ui.testScenario_CB.setCurrentIndex(0)  # Select first scenario
            self.start_auto_test()

    def test_settings(self):
        """Test settings dialog from menu"""
        self.open_test_settings()

    def open_test_settings(self):
        """Open test parameter settings dialog"""
        try:
            dialog = TestSettingsDialog(self)
            dialog.set_settings(self.test_config)
            
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                # Update settings
                self.test_config.update(dialog.get_settings())
                
                # Update auto test service with new settings
                self.auto_test_service.set_voltages(
                    self.test_config['stabilization_voltage'],
                    self.test_config['test_voltage']
                )
                self.auto_test_service.stabilization_time = self.test_config['stabilization_time']
                
                self._log("Test settings updated", "info")
                
        except Exception as e:
            self._log(f"ERROR: Error opening test settings: {e}", "error")
            QtWidgets.QMessageBox.warning(self, "Settings Error", f"Failed to open test settings:\n{e}")
    
    def open_multi_channel_monitor(self):
        """Open multi-channel power rail monitor"""
        try:
            if self.multi_channel_dialog is None:
                self.multi_channel_dialog = MultiChannelMonitorDialog(self)
                
                # Connect signals
                self.multi_channel_dialog.channel_config_changed.connect(self._on_channel_config_changed)
                self.multi_channel_dialog.monitoring_requested.connect(self._on_multi_channel_monitoring)
                
                # Connect NI service signals if available
                if hasattr(self.ni_service, 'channel_data_updated'):
                    self.ni_service.channel_data_updated.connect(self._on_channel_data_updated)
                
                # Connect multi-channel monitor to test scenario engine
                self.test_scenario_engine.set_multi_channel_monitor(self.multi_channel_dialog)
            
            self.multi_channel_dialog.show()
            self.multi_channel_dialog.raise_()
            self.multi_channel_dialog.activateWindow()
            
        except Exception as e:
            self._log(f"ERROR: Failed to open multi-channel monitor: {e}", "error")
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to open multi-channel monitor:\n{e}")
    
    def _on_channel_config_changed(self, config_dict):
        """Handle channel configuration changes"""
        for channel, config in config_dict.items():
            if hasattr(self.ni_service, 'set_channel_config'):
                self.ni_service.set_channel_config(
                    channel, 
                    config['name'], 
                    config['target_v'], 
                    config['shunt_r'], 
                    config['enabled']
                )
# Removed real-time logging to reduce system log spam
                # self._log(f"Updated {channel}: {config['name']} ({config['target_v']}V)", "info")
    
    def _on_multi_channel_monitoring(self, start_monitoring):
        """Handle multi-channel monitoring request"""
        # DISABLED: Use internal timer-based monitoring instead of old NI service monitoring
        # The old monitoring system uses incorrect current calculation (175524.3mA issue)
        # New multi-channel monitor uses its own timer with correct current/voltage mode handling
        pass
    
    def _on_channel_data_updated(self, readings):
        """Handle channel data updates"""
        if self.multi_channel_dialog:
            for channel, data in readings.items():
                voltage = data.get('voltage', 0.0)
                current = data.get('current', 0.0)
                self.multi_channel_dialog.update_channel_display(channel, voltage, current)

    def show_about(self):
        """Show about dialog"""
        QtWidgets.QMessageBox.about(
            self, 
            "About HVPM Monitor with Multi-Channel DAQ", 
            "HVPM Monitor v3.2 with Multi-Channel DAQ\n\n"
            "Enhanced power measurement tool with automated testing capabilities.\n"
            "Features real-time monitoring, voltage control, and multi-channel DAQ monitoring.\n\n"
            "New Features:\n"
            "• 12-channel voltage/current monitoring\n"
            "• Excel copy-paste rail configuration\n"
            "• Real-time and single-shot measurements\n"
            "• Power rail management\n"
            "• Automated test scenarios\n"
            "• Enhanced UI and logging\n\n"
            "Built with PyQt6 and PyQtGraph"
        )

    def closeEvent(self, event):
        """Handle application close"""
        # Stop any running tests
        if self.auto_test_service.is_running:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Test Running",
                "An automated test is currently running. Stop the test and exit?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.auto_test_service.stop_test()
            else:
                event.ignore()
                return
        
        # Stop monitoring
        if self._graphActive:
            self.stop_graph()
        
        event.accept()

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    import traceback
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"[CRITICAL ERROR] Uncaught exception: {error_msg}")
    
    # Try to show error dialog if possible
    try:
        from PyQt6 import QtWidgets
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setWindowTitle("Critical Error")
        msg.setText("An unexpected error occurred.")
        msg.setDetailedText(error_msg)
        msg.exec()
    except Exception:
        pass  # If GUI fails, just print to console

def main():
    # Set global exception handler
    sys.excepthook = handle_exception
    
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("HVPM Monitor")
    app.setApplicationVersion("3.2")
    
    # PyQt6: High DPI scaling is enabled by default
    # No need to manually set AA_EnableHighDpiScaling as it's deprecated in PyQt6
    
    # Print screen information for debugging
    screen = app.primaryScreen()
    if screen:
        dpi = screen.physicalDotsPerInch()
        geometry = screen.availableGeometry()
        print(f"[System] Screen: {geometry.width()}x{geometry.height()}, DPI: {dpi:.1f}")
    
    try:
        w = MainWindow()
        w.show()
        
        print("[System] Application started successfully")
        sys.exit(app.exec())
    except Exception as e:
        print(f"[CRITICAL] Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()