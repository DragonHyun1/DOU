import sys, time, math
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QColor, QAction
from PyQt6.QtCore import QTimer
from generated import main_ui_improved
from services.hvpm import HvpmService
from services import theme, adb
from collections import deque
import pyqtgraph as pg

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = main_ui_improved.Ui_MainWindow()
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

        # Setup enhanced UI components
        self.setup_graphs()
        self.setup_connections()
        self.setup_status_indicators()
        self.setup_menu_actions()
        
        # 버퍼/타이머
        self._t0 = None
        self._tbuf = deque(maxlen=600)   # 10Hz*60s = 최근 1분
        self._vbuf = deque(maxlen=600)
        self._ibuf = deque(maxlen=600)
        self._graphActive = False
        self._graphTimer = QTimer(self)
        self._graphTimer.setInterval(100)        # 10 Hz UI 업데이트
        self._graphTimer.timeout.connect(self._on_graph_tick)

        # ADB 상태
        self.selected_device = None
        self._refreshing_adb = False
        self._cfg_refresh_reads_voltage = False

        # 초기화
        self.refresh_connections()
        
        # Status bar 메시지
        self.ui.statusbar.showMessage("Ready - Connect devices to start monitoring", 5000)

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
        self.ui.port_PB.clicked.connect(self.refresh_connections)
        self.ui.readVolt_PB.clicked.connect(self.handle_read_voltage)
        self.ui.setVolt_PB.clicked.connect(self.handle_set_voltage)
        self.ui.startGraph_PB.clicked.connect(self.start_graph)
        self.ui.stopGraph_PB.clicked.connect(self.stop_graph)
        
        # Combo box connections
        self.ui.comport_CB.currentIndexChanged.connect(self._on_device_selected)
        
        # Enter key for voltage input
        self.ui.hvpmVolt_LE.returnPressed.connect(self.handle_set_voltage)

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

    def setup_menu_actions(self):
        """Setup menu actions"""
        # File menu actions
        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionExport_Data.triggered.connect(self.export_data)
        
        # View menu actions
        self.ui.actionToggle_Theme.triggered.connect(self.toggle_theme)
        self.ui.actionReset_Layout.triggered.connect(self.reset_layout)
        
        # Help menu actions
        self.ui.actionAbout.triggered.connect(self.show_about)

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
        # Update HVPM status
        if hasattr(self.hvpm_service, 'pm') and self.hvpm_service.pm:
            self.ui.hvpmStatus_LB.setText("Connected")
            self.ui.hvpmStatus_LB.setStyleSheet(f"color: {theme.get_status_color('connected')}; font-weight: bold;")
        else:
            self.ui.hvpmStatus_LB.setText("Disconnected")
            self.ui.hvpmStatus_LB.setStyleSheet(f"color: {theme.get_status_color('disconnected')}; font-weight: bold;")

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
        else:
            self.ui.comport_CB.addItem("No devices found")
            self.selected_device = None
            self._log("⚠️ No ADB devices found", "warn")
            
        self._refreshing_adb = False

    def _on_device_selected(self):
        """Handle ADB device selection"""
        if self._refreshing_adb:
            return
            
        device = self.ui.comport_CB.currentText().strip()
        if device and device != "No devices found":
            self.selected_device = device
            self._log(f"📱 ADB device changed: {device}", "info")
        else:
            self.selected_device = None
            self._log("⚠️ No ADB device selected", "warn")

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
            self.ui.readVolt_PB.setText("📊 Read Current Voltage")

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
            self.ui.setVolt_PB.setText("⚡ Set Voltage")

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
        self.resize(1200, 800)
        self._log("🔄 Layout reset", "info")

    def show_about(self):
        """Show about dialog"""
        QtWidgets.QMessageBox.about(
            self, 
            "About HVPM Monitor", 
            "HVPM Monitor v2.0\n\n"
            "Enhanced power measurement tool with real-time monitoring.\n"
            "Features modern UI design and improved functionality.\n\n"
            "Built with PyQt6 and PyQtGraph"
        )

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("HVPM Monitor")
    app.setApplicationVersion("2.0")
    
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()