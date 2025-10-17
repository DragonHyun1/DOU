import sys, time, math
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QColor, QAction
from PyQt6.QtCore import QTimer
from generated import main_ui
from services.hvpm import HvpmService
from services.auto_test import AutoTestService
from services import theme, adb
from collections import deque
import pyqtgraph as pg

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = main_ui.Ui_MainWindow()
        self.ui.setupUi(self)

        # Apply modern theme
        theme.apply_theme(self)

        # HVPM 서비스
        self.hvpm_service = HvpmService(
            combo=self.ui.hvpm_CB,
            status_label=self.ui.hvpmStatus_LB,
            volt_label=self.ui.hvpmVolt_LB,
            volt_entry=self.ui.hvpmVolt_LE
        )

        # Auto Test 서비스
        self.auto_test_service = AutoTestService(
            hvpm_service=self.hvpm_service,
            log_callback=self._log
        )

        # 버퍼/타이머 초기화
        self._t0 = None
        self._tbuf = deque(maxlen=600)   # 10Hz*60s = 최근 1분
        self._vbuf = deque(maxlen=600)
        self._ibuf = deque(maxlen=600)
        self._graphActive = False
        self._graphTimer = QTimer(self)
        self._graphTimer.setInterval(100)        # 10 Hz UI 업데이트
        self._graphTimer.timeout.connect(self._on_graph_tick)

        # ADB 상태 초기화
        self.selected_device = None
        self._refreshing_adb = False
        self._cfg_refresh_reads_voltage = False

        # Setup enhanced UI components
        self.setup_graphs()
        self.setup_status_indicators()
        self.setup_menu_actions()
        
        # Debug: Check UI elements first
        self._check_ui_elements()
        
        # Setup connections after UI check
        self.setup_connections()
        self.setup_auto_test_ui()
        
        # 초기화 - UI 설정 완료 후 실행
        self.refresh_connections()
        
        # Status bar 메시지
        self.ui.statusbar.showMessage("Ready - Connect devices to start monitoring and testing", 5000)

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
        if hasattr(self.ui, 'readVolt_PB') and self.ui.readVolt_PB:
            self.ui.readVolt_PB.clicked.connect(self.handle_read_voltage)
        if hasattr(self.ui, 'setVolt_PB') and self.ui.setVolt_PB:
            self.ui.setVolt_PB.clicked.connect(self.handle_set_voltage)
        if hasattr(self.ui, 'startGraph_PB') and self.ui.startGraph_PB:
            self.ui.startGraph_PB.clicked.connect(self.start_graph)
        if hasattr(self.ui, 'stopGraph_PB') and self.ui.stopGraph_PB:
            self.ui.stopGraph_PB.clicked.connect(self.stop_graph)
        
        # Auto test connections (check if they exist)
        if hasattr(self.ui, 'startAutoTest_PB') and self.ui.startAutoTest_PB:
            self.ui.startAutoTest_PB.clicked.connect(self.start_auto_test)
        if hasattr(self.ui, 'stopAutoTest_PB') and self.ui.stopAutoTest_PB:
            self.ui.stopAutoTest_PB.clicked.connect(self.stop_auto_test)
        
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

    def setup_status_indicators(self):
        """Setup status indicators and tooltips"""
        # Add tooltips
        self.ui.hvpm_CB.setToolTip("Select HVPM device")
        self.ui.comport_CB.setToolTip("Select ADB device")
        self.ui.port_PB.setToolTip("Refresh device connections")
        self.ui.hvpmVolt_LE.setToolTip("Enter target voltage (V)")
        self.ui.readVolt_PB.setToolTip("Read current voltage from device")
        self.ui.setVolt_PB.setToolTip("Set voltage to specified value")
        self.ui.startGraph_PB.setToolTip("Start real-time monitoring")
        self.ui.stopGraph_PB.setToolTip("Stop real-time monitoring")
        
        # Auto test tooltips
        self.ui.testScenario_CB.setToolTip("Select test scenario to run")
        self.ui.stabilizationVoltage_SB.setToolTip("Voltage for device stabilization before test")
        self.ui.testVoltage_SB.setToolTip("Voltage during actual test execution")
        self.ui.startAutoTest_PB.setToolTip("Start automated test with voltage control")
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
        
        # Help menu actions
        self.ui.actionAbout.triggered.connect(self.show_about)

    def setup_auto_test_ui(self):
        """Setup auto test UI components"""
        # Check if auto test UI elements exist
        if not hasattr(self.ui, 'testScenario_CB') or not self.ui.testScenario_CB:
            self._log("⚠️ Auto test UI elements not found - auto test features disabled", "warn")
            return
            
        # Test scenarios are now pre-populated in the UI file, but we can verify they have data
        scenarios = self.auto_test_service.get_available_scenarios()
        
        # Ensure all items have proper data values
        for i in range(self.ui.testScenario_CB.count()):
            item_data = self.ui.testScenario_CB.itemData(i)
            if not item_data:
                # Set data based on index if not already set
                scenario_keys = ["screen_onoff", "screen_onoff_long", "cpu_stress", "cpu_stress_long"]
                if i < len(scenario_keys):
                    self.ui.testScenario_CB.setItemData(i, scenario_keys[i])
        
        # Connect voltage spinbox changes (check if they exist)
        if hasattr(self.ui, 'stabilizationVoltage_SB') and self.ui.stabilizationVoltage_SB:
            self.ui.stabilizationVoltage_SB.valueChanged.connect(self._on_voltage_config_changed)
        if hasattr(self.ui, 'testVoltage_SB') and self.ui.testVoltage_SB:
            self.ui.testVoltage_SB.valueChanged.connect(self._on_voltage_config_changed)
        
        # Connect new test parameter controls
        if hasattr(self.ui, 'testCycles_SB') and self.ui.testCycles_SB:
            self.ui.testCycles_SB.valueChanged.connect(self._on_test_params_changed)
        if hasattr(self.ui, 'testDuration_SB') and self.ui.testDuration_SB:
            self.ui.testDuration_SB.valueChanged.connect(self._on_test_params_changed)
        
        # Connect scenario selection change
        self.ui.testScenario_CB.currentIndexChanged.connect(self._on_scenario_changed)
        
        # Initial configuration
        self._on_voltage_config_changed()
        self._on_test_params_changed()

    def refresh_connections(self):
        """Enhanced connection refresh with better feedback"""
        self.ui.port_PB.setEnabled(False)
        self.ui.port_PB.setText("🔄 Refreshing...")
        
        # Refresh ADB
        self.refresh_adb_ports()
        
        # Refresh HVPM
        self.hvpm_service.refresh_ports(log_callback=self._log)
        
        # Update status
        self.update_connection_status()
        
        self.ui.port_PB.setEnabled(True)
        self.ui.port_PB.setText("🔄 Refresh")
        
        # Read initial voltage if configured
        if self._cfg_refresh_reads_voltage and self.hvpm_service.is_connected():
            self.handle_read_voltage()

    def update_connection_status(self):
        """Update connection status indicators"""
        try:
            # Update HVPM status
            if hasattr(self.ui, 'hvpmStatus_LB') and self.ui.hvpmStatus_LB:
                if hasattr(self.hvpm_service, 'pm') and self.hvpm_service.pm:
                    self.ui.hvpmStatus_LB.setText("Connected")
                    self.ui.hvpmStatus_LB.setStyleSheet(f"color: {theme.get_status_color('connected')}; font-weight: bold;")
                else:
                    self.ui.hvpmStatus_LB.setText("Disconnected")
                    self.ui.hvpmStatus_LB.setStyleSheet(f"color: {theme.get_status_color('disconnected')}; font-weight: bold;")
            
            # Update auto test button availability (safely)
            self._update_auto_test_buttons()
            
        except Exception as e:
            self._log(f"Error updating connection status: {e}", "error")

    def _update_auto_test_buttons(self):
        """Update auto test button states"""
        # Check if auto test UI elements exist and are not None
        try:
            start_button = getattr(self.ui, 'startAutoTest_PB', None)
            stop_button = getattr(self.ui, 'stopAutoTest_PB', None)
            
            if start_button is None or stop_button is None:
                return
                
            hvpm_connected = self.hvpm_service.is_connected()
            adb_connected = self.selected_device and self.selected_device != "No devices found"
            test_running = self.auto_test_service.is_running
            
            can_start = hvpm_connected and adb_connected and not test_running
            
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
                start_button.setEnabled(can_start)
            except Exception as e:
                self._log(f"Error updating start button: {e}", "error")
                
            try:
                stop_button.setEnabled(test_running)
            except Exception as e:
                self._log(f"Error updating stop button: {e}", "error")
            
            # Update tooltips based on status
            try:
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

    # ---------- 로그 ----------
    def _log(self, msg: str, level: str = "info"):
        """Enhanced logging with better formatting"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        
        item = QtWidgets.QListWidgetItem(formatted_msg)
        
        # Set colors based on level
        color = theme.get_status_color(level)
        item.setForeground(QColor(color))
        
        self.ui.log_LW.addItem(item)
        self.ui.log_LW.scrollToBottom()
        
        # Also update status bar for important messages
        if level in ['error', 'warn']:
            self.ui.statusbar.showMessage(msg, 3000)

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
        self.ui.readVolt_PB.setEnabled(False)
        self.ui.startGraph_PB.setEnabled(False)
        self.ui.stopGraph_PB.setEnabled(True)
        
        self._graphActive = True
        self._graphTimer.start()
        
        self._log("📊 Real-time monitoring started (10 Hz)", "info")
        self.ui.statusbar.showMessage("Monitoring active - Collecting data...", 0)

    def stop_graph(self):
        """Stop graph monitoring"""
        if not self._graphActive:
            return
            
        self._graphTimer.stop()
        self._graphActive = False
        
        # Update UI state
        self.ui.readVolt_PB.setEnabled(True)
        self.ui.startGraph_PB.setEnabled(True)
        self.ui.stopGraph_PB.setEnabled(False)
        
        self._log("⏹️ Real-time monitoring stopped", "info")
        self.ui.statusbar.showMessage("Monitoring stopped", 3000)

    def _on_graph_tick(self):
        """Enhanced graph tick with better error handling"""
        try:
            # Check connection
            svc = self.hvpm_service
            if not (getattr(svc, "pm", None) and getattr(svc, "engine", None)):
                self._log("⚠️ Connection lost during monitoring", "warn")
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
                    self._log("⚠️ Invalid data received - skipping update", "warn")
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
            self._log(f"❌ Graph update failed: {e}", "error")

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
            self._log(f"❌ ADB Error: {e}", "error")

        if devices:
            self.ui.comport_CB.addItems(devices)
            self.ui.comport_CB.setCurrentIndex(0)
            self.selected_device = devices[0]
            self._log(f"📱 ADB device selected: {self.selected_device}", "info")
            
            # Update auto test service
            self.auto_test_service.set_device(self.selected_device)
        else:
            self.ui.comport_CB.addItem("No devices found")
            self.selected_device = None
            self._log("⚠️ No ADB devices found", "warn")
            
        self._refreshing_adb = False
        self._update_auto_test_buttons()

    def _on_device_selected(self):
        """Handle ADB device selection"""
        if self._refreshing_adb:
            return
            
        device = self.ui.comport_CB.currentText().strip()
        if device and device != "No devices found":
            self.selected_device = device
            self._log(f"📱 ADB device changed: {device}", "info")
            self.auto_test_service.set_device(device)
        else:
            self.selected_device = None
            self._log("⚠️ No ADB device selected", "warn")
        
        self._update_auto_test_buttons()

    # ---------- HVPM ----------
    def handle_read_voltage(self):
        """Enhanced voltage reading with better feedback"""
        self.ui.readVolt_PB.setEnabled(False)
        self.ui.readVolt_PB.setText("📊 Reading...")
        
        try:
            v = self.hvpm_service.read_voltage(log_callback=self._log)
            if v is not None:
                self.hvpm_service.last_set_vout = v
                self.hvpm_service.enabled = v > 0
                self.hvpm_service._update_volt_label()
                self._log(f"📊 Current voltage: {v:.3f} V", "info")
                self.ui.statusbar.showMessage(f"Voltage read: {v:.3f} V", 3000)
            else:
                self._log("❌ Failed to read voltage", "error")
        finally:
            self.ui.readVolt_PB.setEnabled(True)
            self.ui.readVolt_PB.setText("📊 Read")

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
        # Check if voltage spinboxes exist
        if not (hasattr(self.ui, 'stabilizationVoltage_SB') and hasattr(self.ui, 'testVoltage_SB')):
            return
        if not (self.ui.stabilizationVoltage_SB and self.ui.testVoltage_SB):
            return
            
        stabilization_voltage = self.ui.stabilizationVoltage_SB.value()
        test_voltage = self.ui.testVoltage_SB.value()
        
        self.auto_test_service.set_voltages(stabilization_voltage, test_voltage)

    def start_auto_test(self):
        """Start automated test"""
        if self.auto_test_service.is_running:
            return
        
        # Get selected scenario
        scenario_data = self.ui.testScenario_CB.currentData()
        if not scenario_data:
            QtWidgets.QMessageBox.warning(self, "No Scenario", "Please select a test scenario.")
            return
        
        # Confirm test start
        scenario_name = self.ui.testScenario_CB.currentText()
        stabilization_v = self.ui.stabilizationVoltage_SB.value()
        test_v = self.ui.testVoltage_SB.value()
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Start Auto Test",
            f"Start automated test?\n\n"
            f"Scenario: {scenario_name}\n"
            f"Stabilization Voltage: {stabilization_v}V\n"
            f"Test Voltage: {test_v}V\n"
            f"Device: {self.selected_device}\n\n"
            f"This will automatically control voltage and device.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.No:
            return
        
        # Start monitoring if not already active
        if not self._graphActive:
            self.start_graph()
        
        # Get custom script if needed
        custom_script = None
        if scenario_data == "custom_script" and hasattr(self.ui, 'customScript_TE') and self.ui.customScript_TE:
            custom_script = self.ui.customScript_TE.toPlainText().strip()
            if not custom_script:
                QtWidgets.QMessageBox.warning(self, "Custom Script Required", "Please enter ADB commands for the custom script test.")
                return
        
        # Clear previous results
        if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
            self.ui.testResults_TE.clear()
        
        # Start test
        success = self.auto_test_service.start_test(scenario_data, custom_script)
        if success:
            self._update_auto_test_buttons()
            self.ui.testProgress_PB.setValue(0)
            self.ui.testStatus_LB.setText("🚀 Initializing test...")
            self.ui.testStatus_LB.setStyleSheet("font-size: 11pt; color: #4CAF50; font-weight: bold;")
            
            # Update Auto Test group box title to show running status
            if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                self.ui.autoTestGroupBox.setTitle("Auto Test - RUNNING")
            
            # Update status bar
            self.ui.statusbar.showMessage(f"Running Auto Test: {scenario_name}", 0)
            
            # Log with enhanced formatting
            self._log(f"🚀 Starting automated test: {scenario_name}", "info")
            if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
                timestamp = time.strftime("%H:%M:%S")
                self.ui.testResults_TE.append(f"[{timestamp}] 🚀 Test Started: {scenario_name}")
        else:
            QtWidgets.QMessageBox.warning(self, "Test Start Failed", "Failed to start automated test. Check connections and try again.")

    def stop_auto_test(self):
        """Stop automated test"""
        if not self.auto_test_service.is_running:
            return
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "Stop Auto Test",
            "Are you sure you want to stop the current test?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.auto_test_service.stop_test()
            self._update_auto_test_buttons()
            self.ui.testProgress_PB.setValue(0)
            if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
                self.ui.testStatus_LB.setText("⏹️ Test stopped by user")
                self.ui.testStatus_LB.setStyleSheet("font-size: 11pt; color: #FF9800; font-weight: bold;")
            
            # Update Auto Test group box title
            if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                self.ui.autoTestGroupBox.setTitle("Auto Test - STOPPED")
            
            # Update status bar
            self.ui.statusbar.showMessage("Auto Test Stopped", 3000)
            
            # Add to test results
            if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
                timestamp = time.strftime("%H:%M:%S")
                self.ui.testResults_TE.append(f"[{timestamp}] ⏹️ Test stopped by user")

    def _on_auto_test_progress(self, progress: int, status: str):
        """Handle auto test progress updates"""
        if hasattr(self.ui, 'testProgress_PB') and self.ui.testProgress_PB:
            self.ui.testProgress_PB.setValue(progress)
        
        if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
            # Add progress indicator and color coding
            if progress < 30:
                color = "#FF9800"  # Orange for initialization
                icon = "🔄"
            elif progress < 70:
                color = "#2196F3"  # Blue for in progress
                icon = "⚡"
            else:
                color = "#4CAF50"  # Green for near completion
                icon = "🎯"
            
            formatted_status = f"{icon} {status} ({progress}%)"
            self.ui.testStatus_LB.setText(formatted_status)
            self.ui.testStatus_LB.setStyleSheet(f"font-size: 11pt; color: {color}; font-weight: bold;")
        
        # Update status bar with progress
        self.ui.statusbar.showMessage(f"Auto Test Running: {progress}% - {status}", 0)
        
        # Add to test results for detailed tracking
        if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
            timestamp = time.strftime("%H:%M:%S")
            self.ui.testResults_TE.append(f"[{timestamp}] {progress}% - {status}")

    def _on_auto_test_completed(self, success: bool, message: str):
        """Handle auto test completion"""
        self._update_auto_test_buttons()
        
        # Update test results display
        if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
            timestamp = time.strftime("%H:%M:%S")
            result_text = f"[{timestamp}] Test {'PASSED' if success else 'FAILED'}: {message}\n"
            self.ui.testResults_TE.append(result_text)
        
        # Save test results
        self._save_test_results(success, message)
        
        if success:
            if hasattr(self.ui, 'testProgress_PB') and self.ui.testProgress_PB:
                self.ui.testProgress_PB.setValue(100)
            if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
                self.ui.testStatus_LB.setText("✅ Test completed successfully")
                self.ui.testStatus_LB.setStyleSheet("font-size: 11pt; color: #4CAF50; font-weight: bold;")
            
            # Update Auto Test group box title
            if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                self.ui.autoTestGroupBox.setTitle("Auto Test - COMPLETED")
            
            # Update status bar
            self.ui.statusbar.showMessage("Auto Test Completed Successfully", 5000)
            
            # Ask user if they want to save detailed results
            reply = QtWidgets.QMessageBox.question(
                self, "Test Complete", 
                f"Automated test completed successfully!\n\n{message}\n\nWould you like to save detailed test results?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self._export_test_results()
        else:
            if hasattr(self.ui, 'testStatus_LB') and self.ui.testStatus_LB:
                self.ui.testStatus_LB.setText("❌ Test failed")
                self.ui.testStatus_LB.setStyleSheet("font-size: 11pt; color: #f44336; font-weight: bold;")
            
            # Update Auto Test group box title
            if hasattr(self.ui, 'autoTestGroupBox') and self.ui.autoTestGroupBox:
                self.ui.autoTestGroupBox.setTitle("Auto Test - FAILED")
            
            # Update status bar
            self.ui.statusbar.showMessage("Auto Test Failed", 5000)
            
            QtWidgets.QMessageBox.warning(self, "Test Failed", f"Automated test failed:\n\n{message}")
    
    def _save_test_results(self, success: bool, message: str):
        """Save test results to file"""
        try:
            import os
            results_dir = "test_results"
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{results_dir}/test_result_{timestamp}.txt"
            
            scenario_name = self.ui.testScenario_CB.currentText() if hasattr(self.ui, 'testScenario_CB') else "Unknown"
            stabilization_v = self.ui.stabilizationVoltage_SB.value() if hasattr(self.ui, 'stabilizationVoltage_SB') else 0
            test_v = self.ui.testVoltage_SB.value() if hasattr(self.ui, 'testVoltage_SB') else 0
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"=== HVPM Auto Test Results ===\n")
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Test Scenario: {scenario_name}\n")
                f.write(f"Stabilization Voltage: {stabilization_v}V\n")
                f.write(f"Test Voltage: {test_v}V\n")
                f.write(f"Device: {self.selected_device or 'Unknown'}\n")
                f.write(f"Result: {'PASSED' if success else 'FAILED'}\n")
                f.write(f"Message: {message}\n")
                f.write(f"\n=== Test Log ===\n")
                
                # Add test results from UI if available
                if hasattr(self.ui, 'testResults_TE') and self.ui.testResults_TE:
                    f.write(self.ui.testResults_TE.toPlainText())
            
            self._log(f"📁 Test results saved to {filename}", "info")
            
        except Exception as e:
            self._log(f"❌ Failed to save test results: {e}", "error")
    
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
                
                self._log(f"📁 Detailed results exported to {filename}", "success")
                QtWidgets.QMessageBox.information(self, "Export Complete", f"Test results exported to:\n{filename}")
                
            except Exception as e:
                self._log(f"❌ Export failed: {e}", "error")
                QtWidgets.QMessageBox.warning(self, "Export Error", f"Failed to export results:\n{e}")

    def _on_voltage_stabilized(self, voltage: float):
        """Handle voltage stabilization notification"""
        self._log(f"✅ Voltage stabilized at {voltage:.2f}V", "success")
    
    def _on_test_params_changed(self):
        """Handle test parameter changes"""
        if not (hasattr(self.ui, 'testCycles_SB') and hasattr(self.ui, 'testDuration_SB')):
            return
        if not (self.ui.testCycles_SB and self.ui.testDuration_SB):
            return
            
        cycles = self.ui.testCycles_SB.value()
        duration = self.ui.testDuration_SB.value()
        
        self._log(f"⚙️ Test parameters: Cycles={cycles}, Duration={duration}s", "info")
    
    def _on_scenario_changed(self):
        """Handle test scenario selection change"""
        scenario_data = self.ui.testScenario_CB.currentData()
        scenario_name = self.ui.testScenario_CB.currentText()
        
        # Show/hide custom script frame
        if hasattr(self.ui, 'customScriptFrame') and self.ui.customScriptFrame:
            is_custom = "Custom Script" in scenario_name
            self.ui.customScriptFrame.setVisible(is_custom)
        
        if scenario_data:
            self._log(f"📋 Test scenario selected: {scenario_name}", "info")
            
            # Update test parameters based on scenario
            if "screen_onoff" in scenario_data:
                if hasattr(self.ui, 'testCycles_SB') and self.ui.testCycles_SB:
                    cycles = 10 if "long" in scenario_data else 5
                    self.ui.testCycles_SB.setValue(cycles)
                if hasattr(self.ui, 'testDuration_SB') and self.ui.testDuration_SB:
                    self.ui.testDuration_SB.setValue(15 if "long" in scenario_data else 10)
            elif "cpu_stress" in scenario_data:
                if hasattr(self.ui, 'testCycles_SB') and self.ui.testCycles_SB:
                    self.ui.testCycles_SB.setValue(1)
                if hasattr(self.ui, 'testDuration_SB') and self.ui.testDuration_SB:
                    duration = 300 if "long" in scenario_data else 60
                    self.ui.testDuration_SB.setValue(duration)
            elif scenario_data == "custom_script":
                if hasattr(self.ui, 'testCycles_SB') and self.ui.testCycles_SB:
                    self.ui.testCycles_SB.setValue(1)
                if hasattr(self.ui, 'testDuration_SB') and self.ui.testDuration_SB:
                    self.ui.testDuration_SB.setValue(30)
        else:
            self._log("⚠️ No scenario data found", "warn")

    def _check_ui_elements(self):
        """Debug function to check UI elements"""
        ui_elements = [
            'startAutoTest_PB', 'stopAutoTest_PB', 'testScenario_CB',
            'stabilizationVoltage_SB', 'testVoltage_SB', 'testProgress_PB', 'testStatus_LB',
            'testCycles_SB', 'testDuration_SB', 'testResults_TE'
        ]
        
        missing_elements = []
        existing_elements = []
        for element in ui_elements:
            if not hasattr(self.ui, element) or getattr(self.ui, element) is None:
                missing_elements.append(element)
            else:
                existing_elements.append(element)
        
        if missing_elements:
            self._log(f"⚠️ Missing UI elements: {', '.join(missing_elements)}", "warn")
            self._log("Auto test features may be limited", "warn")
        
        if existing_elements:
            self._log(f"✅ Found UI elements: {', '.join(existing_elements)}", "info")
        
        # Check test scenario combo box items
        if hasattr(self.ui, 'testScenario_CB') and self.ui.testScenario_CB:
            count = self.ui.testScenario_CB.count()
            self._log(f"📋 Test scenario combo box has {count} items", "info")

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
                        
                self._log(f"📁 Data exported to {filename}", "success")
                QtWidgets.QMessageBox.information(self, "Export Complete", f"Data exported to:\n{filename}")
            except Exception as e:
                self._log(f"❌ Export failed: {e}", "error")
                QtWidgets.QMessageBox.warning(self, "Export Error", f"Failed to export data:\n{e}")

    def toggle_theme(self):
        """Toggle between themes (placeholder)"""
        self._log("🎨 Theme toggle not implemented yet", "info")

    def reset_layout(self):
        """Reset window layout"""
        self.resize(1400, 900)
        self._log("🔄 Layout reset", "info")

    def quick_test(self):
        """Quick test shortcut"""
        if self.ui.testScenario_CB.count() > 0:
            self.ui.testScenario_CB.setCurrentIndex(0)  # Select first scenario
            self.start_auto_test()

    def test_settings(self):
        """Test settings dialog (placeholder)"""
        QtWidgets.QMessageBox.information(
            self,
            "Test Settings",
            "Test settings dialog not implemented yet.\n\n"
            "Use the Auto Test panel to configure test parameters."
        )

    def show_about(self):
        """Show about dialog"""
        QtWidgets.QMessageBox.about(
            self, 
            "About HVPM Monitor with Auto Test", 
            "HVPM Monitor v3.0 with Auto Test\n\n"
            "Enhanced power measurement tool with automated testing capabilities.\n"
            "Features real-time monitoring, voltage control, and ADB-based device testing.\n\n"
            "New Features:\n"
            "• Automated test scenarios\n"
            "• Voltage stabilization\n"
            "• ADB device control\n"
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

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("HVPM Monitor")
    app.setApplicationVersion("3.0")
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()