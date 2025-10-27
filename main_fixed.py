import sys, time, math
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QColor, QAction
from PyQt6.QtCore import QTimer
from generated import main_ui
from services.hvpm import HvpmService
from services.auto_test import AutoTestService
from services.test_scenario_engine import TestScenarioEngine
from services.test_scenario_engine import TestScenarioEngine
from services.ni_daq import create_ni_service
from services import theme, adb
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
            log_callback=self._log
        )
        
        # 측정 모드 추적 (독립적 제어)
        self._hvpm_monitoring = False
        self._ni_monitoring = False
        self._show_conflict_warning = True
        
        # Test configuration settings - FIXED: Correct spelling of 'stabilization'
        self.test_config = {
            'stabilization_voltage': 4.8,  # FIXED: Was 'stabilzation_voltage'
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
        
        # Initialize voltage configuration from settings - FIXED: This should work now
        self._on_voltage_config_changed()
        
        # Apply adaptive sizing to UI elements
        self._apply_adaptive_ui_sizing()
        
        # Apply responsive layout management
        self._apply_responsive_layout()
        
        # Status bar 메시지
        self.ui.statusbar.showMessage("Ready - Connect devices to start monitoring and testing", 5000)

    def _on_voltage_config_changed(self):
        """Handle voltage configuration changes - FIXED: Correct key names"""
        # Voltage configuration is now handled through settings dialog
        self.auto_test_service.set_voltages(
            self.test_config['stabilization_voltage'],  # FIXED: Correct spelling
            self.test_config['test_voltage']
        )

    # ... rest of the methods remain the same ...
    # (I'm only showing the key fixes - the full file would be too long)

def main():
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
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()