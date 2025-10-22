#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import pyqtSignal
import re

class MultiChannelMonitorDialog(QtWidgets.QDialog):
    """Multi-channel voltage/current monitoring dialog"""
    
    # Signals
    channel_config_changed = pyqtSignal(dict)  # {channel: config}
    monitoring_requested = pyqtSignal(bool)    # start/stop monitoring
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-Channel Power Rail Monitor")
        self.setMinimumSize(800, 600)
        
        # Channel configurations
        self.channel_configs = {}
        self.channel_widgets = {}  # Store UI widgets for each channel
        
        self.setup_ui()
        self.init_default_channels()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Title and controls
        title_layout = QtWidgets.QHBoxLayout()
        title_label = QtWidgets.QLabel("Power Rail Monitoring")
        title_label.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # Control buttons
        self.self_cal_btn = QtWidgets.QPushButton("Self-Calibration")
        self.self_cal_btn.clicked.connect(self.perform_self_calibration)
        self.self_cal_btn.setStyleSheet("QPushButton { background-color: #ff9800; color: white; font-weight: bold; }")
        
        self.start_btn = QtWidgets.QPushButton("Start Monitoring")
        self.start_btn.clicked.connect(self.toggle_monitoring)
        self.single_read_btn = QtWidgets.QPushButton("Single Read")
        self.single_read_btn.clicked.connect(self.single_read)
        
        # Measurement mode selection
        mode_layout = QtWidgets.QHBoxLayout()
        mode_label = QtWidgets.QLabel("Measurement Mode:")
        self.voltage_mode_rb = QtWidgets.QRadioButton("Voltage Mode")
        self.current_mode_rb = QtWidgets.QRadioButton("Current Mode")
        self.voltage_mode_rb.setChecked(True)  # Default to voltage mode
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.voltage_mode_rb)
        mode_layout.addWidget(self.current_mode_rb)
        mode_layout.addStretch()
        
        title_layout.addWidget(self.self_cal_btn)
        title_layout.addWidget(self.single_read_btn)
        title_layout.addWidget(self.start_btn)
        
        layout.addLayout(title_layout)
        layout.addLayout(mode_layout)  # mode_layout is defined above
        
        # Configuration section
        config_group = QtWidgets.QGroupBox("Rail Configuration")
        config_layout = QtWidgets.QVBoxLayout(config_group)
        
        # Excel paste section
        paste_layout = QtWidgets.QHBoxLayout()
        paste_label = QtWidgets.QLabel("Excel Data:")
        self.paste_text = QtWidgets.QTextEdit()
        self.paste_text.setMaximumHeight(100)
        self.paste_text.setPlaceholderText("Paste Excel data here (Rail Name, Target_V, Shunt_R)")
        
        paste_btn = QtWidgets.QPushButton("Import from Excel")
        paste_btn.clicked.connect(self.import_from_excel)
        
        paste_layout.addWidget(paste_label)
        paste_layout.addWidget(self.paste_text, 2)
        paste_layout.addWidget(paste_btn)
        
        config_layout.addLayout(paste_layout)
        
        # Save/Load buttons
        file_layout = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Save Config")
        load_btn = QtWidgets.QPushButton("Load Config")
        save_btn.clicked.connect(self.save_config)
        load_btn.clicked.connect(self.load_config)
        
        file_layout.addWidget(save_btn)
        file_layout.addWidget(load_btn)
        file_layout.addStretch()
        
        config_layout.addLayout(file_layout)
        layout.addWidget(config_group)
        
        # Create scrollable area for channels
        scroll_area = QtWidgets.QScrollArea()
        scroll_widget = QtWidgets.QWidget()
        self.channels_layout = QtWidgets.QVBoxLayout(scroll_widget)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area, 1)
        
        # Status bar
        self.status_label = QtWidgets.QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Monitoring state
        self.monitoring = False
        
    def init_default_channels(self):
        """Initialize default channel configurations"""
        default_rails = [
            {'name': '3V3_MAIN', 'target_v': 3.30, 'shunt_r': 0.010},
            {'name': '1V8_IO', 'target_v': 1.80, 'shunt_r': 0.020},
            {'name': '1V2_CORE', 'target_v': 1.20, 'shunt_r': 0.010},
            {'name': '5V0_USB', 'target_v': 5.00, 'shunt_r': 0.050},
            {'name': '2V5_ADC', 'target_v': 2.50, 'shunt_r': 0.020},
            {'name': '3V3_AUX', 'target_v': 3.30, 'shunt_r': 0.010},
            {'name': '1V0_DDR', 'target_v': 1.00, 'shunt_r': 0.005},
            {'name': '1V5_PLL', 'target_v': 1.50, 'shunt_r': 0.020},
            {'name': '2V8_RF', 'target_v': 2.80, 'shunt_r': 0.010},
            {'name': '3V0_SENSOR', 'target_v': 3.00, 'shunt_r': 0.015},
            {'name': '1V35_CPU', 'target_v': 1.35, 'shunt_r': 0.005},
            {'name': '2V1_MEM', 'target_v': 2.10, 'shunt_r': 0.010}
        ]
        
        for i, rail in enumerate(default_rails):
            channel = f"ai{i}"
            self.add_channel_widget(channel, rail['name'], rail['target_v'], rail['shunt_r'])
    
    def add_channel_widget(self, channel: str, name: str, target_v: float, shunt_r: float, enabled: bool = False):
        """Add a channel monitoring widget"""
        # Channel group box
        group = QtWidgets.QGroupBox(f"Channel {channel}")
        layout = QtWidgets.QHBoxLayout(group)
        
        # Enable checkbox
        enable_cb = QtWidgets.QCheckBox("Enable")
        enable_cb.setChecked(enabled)
        enable_cb.stateChanged.connect(lambda: self.update_channel_config(channel))
        
        # Rail name
        name_label = QtWidgets.QLabel("Name:")
        name_edit = QtWidgets.QLineEdit(name)
        name_edit.setMaximumWidth(100)
        name_edit.textChanged.connect(lambda: self.update_channel_config(channel))
        
        # Target voltage
        target_label = QtWidgets.QLabel("Target:")
        target_spin = QtWidgets.QDoubleSpinBox()
        target_spin.setRange(0.0, 50.0)
        target_spin.setDecimals(3)
        target_spin.setValue(target_v)
        target_spin.setSuffix(" V")
        target_spin.setMaximumWidth(80)
        target_spin.valueChanged.connect(lambda: self.update_channel_config(channel))
        
        # Shunt resistor
        shunt_label = QtWidgets.QLabel("Shunt:")
        shunt_spin = QtWidgets.QDoubleSpinBox()
        shunt_spin.setRange(0.001, 1.0)
        shunt_spin.setDecimals(4)
        shunt_spin.setValue(shunt_r)
        shunt_spin.setSuffix(" Ω")
        shunt_spin.setMaximumWidth(80)
        shunt_spin.valueChanged.connect(lambda: self.update_channel_config(channel))
        
        # Voltage display
        voltage_label = QtWidgets.QLabel("Voltage:")
        voltage_display = QtWidgets.QLabel("----")
        voltage_display.setMinimumWidth(60)
        voltage_display.setStyleSheet("font-weight: bold; color: blue;")
        
        # Current display
        current_label = QtWidgets.QLabel("Current:")
        current_display = QtWidgets.QLabel("----")
        current_display.setMinimumWidth(60)
        current_display.setStyleSheet("font-weight: bold; color: red;")
        
        # Add to layout
        layout.addWidget(enable_cb)
        layout.addWidget(name_label)
        layout.addWidget(name_edit)
        layout.addWidget(target_label)
        layout.addWidget(target_spin)
        layout.addWidget(shunt_label)
        layout.addWidget(shunt_spin)
        layout.addWidget(voltage_label)
        layout.addWidget(voltage_display)
        layout.addWidget(current_label)
        layout.addWidget(current_display)
        layout.addStretch()
        
        # Store widgets for later access
        self.channel_widgets[channel] = {
            'group': group,
            'enable_cb': enable_cb,
            'name_edit': name_edit,
            'target_spin': target_spin,
            'shunt_spin': shunt_spin,
            'voltage_display': voltage_display,
            'current_display': current_display
        }
        
        # Add to channels layout
        self.channels_layout.addWidget(group)
        
        # Initialize configuration
        self.update_channel_config(channel)
    
    def update_channel_config(self, channel: str):
        """Update channel configuration from UI"""
        if channel not in self.channel_widgets:
            return
        
        widgets = self.channel_widgets[channel]
        
        config = {
            'name': widgets['name_edit'].text(),
            'target_v': widgets['target_spin'].value(),
            'shunt_r': widgets['shunt_spin'].value(),
            'enabled': widgets['enable_cb'].isChecked()
        }
        
        self.channel_configs[channel] = config
        
        # Emit signal for service update
        self.channel_config_changed.emit({channel: config})
    
    def update_channel_display(self, channel: str, voltage: float, current: float):
        """Update channel display values"""
        if channel not in self.channel_widgets:
            return
        
        widgets = self.channel_widgets[channel]
        widgets['voltage_display'].setText(f"{voltage:.3f}V")
        widgets['current_display'].setText(f"{current:.3f}A")
        
        # Color coding based on target voltage
        target_v = widgets['target_spin'].value()
        tolerance = 0.05  # 5% tolerance
        
        if abs(voltage - target_v) / target_v <= tolerance:
            widgets['voltage_display'].setStyleSheet("font-weight: bold; color: green;")
        else:
            widgets['voltage_display'].setStyleSheet("font-weight: bold; color: red;")
    
    def import_from_excel(self):
        """Import configuration from Excel paste"""
        text = self.paste_text.toPlainText().strip()
        if not text:
            QtWidgets.QMessageBox.warning(self, "No Data", "Please paste Excel data first.")
            return
        
        try:
            lines = text.split('\n')
            imported_count = 0
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or 'Rail Name' in line:  # Skip header or empty lines
                    continue
                
                # Parse tab-separated or comma-separated values
                parts = re.split(r'[\t,]', line)
                if len(parts) >= 3:
                    name = parts[0].strip()
                    try:
                        target_v = float(parts[1].strip())
                        shunt_r = float(parts[2].strip())
                        
                        # Find available channel
                        channel = f"ai{imported_count}"
                        if channel in self.channel_widgets:
                            widgets = self.channel_widgets[channel]
                            widgets['name_edit'].setText(name)
                            widgets['target_spin'].setValue(target_v)
                            widgets['shunt_spin'].setValue(shunt_r)
                            widgets['enable_cb'].setChecked(True)
                            
                            self.update_channel_config(channel)
                            imported_count += 1
                            
                            if imported_count >= 12:  # Max 12 channels
                                break
                                
                    except ValueError as e:
                        print(f"Error parsing line {i}: {line} - {e}")
                        continue
            
            self.status_label.setText(f"Imported {imported_count} rail configurations")
            self.paste_text.clear()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Import Error", f"Failed to import data:\n{e}")
    
    def toggle_monitoring(self):
        """Toggle monitoring state"""
        self.monitoring = not self.monitoring
        
        if self.monitoring:
            self.start_btn.setText("Stop Monitoring")
            self.status_label.setText("Monitoring active...")
        else:
            self.start_btn.setText("Start Monitoring")
            self.status_label.setText("Monitoring stopped")
        
        self.monitoring_requested.emit(self.monitoring)
    
    def perform_self_calibration(self):
        """Perform DAQ device self-calibration"""
        if hasattr(self.parent(), 'ni_service'):
            ni_service = self.parent().ni_service
            if ni_service.is_connected():
                device_name = ni_service.device_name
                if device_name:
                    self.status_label.setText("Starting self-calibration... (This may take ~18 seconds)")
                    self.self_cal_btn.setEnabled(False)
                    self.self_cal_btn.setText("Calibrating...")
                    
                    # Perform calibration in a separate thread to avoid UI freeze
                    QtCore.QTimer.singleShot(100, lambda: self._do_calibration(device_name))
                else:
                    self.status_label.setText("Device name not available for calibration")
            else:
                self.status_label.setText("DAQ not connected - connect device first")
        else:
            self.status_label.setText("DAQ service not available")
    
    def _do_calibration(self, device_name):
        """Actually perform the calibration"""
        try:
            ni_service = self.parent().ni_service
            success = ni_service.perform_self_calibration(device_name)
            
            if success:
                self.status_label.setText("✅ Self-calibration completed successfully!")
            else:
                self.status_label.setText("❌ Self-calibration failed")
                
        except Exception as e:
            self.status_label.setText(f"❌ Calibration error: {e}")
        finally:
            self.self_cal_btn.setEnabled(True)
            self.self_cal_btn.setText("Self-Calibration")
    
    def single_read(self):
        """Perform single read of all enabled channels"""
        if hasattr(self.parent(), 'ni_service'):
            ni_service = self.parent().ni_service
            if ni_service.is_connected():
                # Get enabled channels
                enabled_channels = [ch for ch, config in self.channel_configs.items() if config.get('enabled', False)]
                if enabled_channels:
                    self.status_label.setText(f"Reading {len(enabled_channels)} channels...")
                    
                    # Choose measurement method based on selected mode
                    try:
                        is_current_mode = self.current_mode_rb.isChecked()
                        mode_name = "Current" if is_current_mode else "Voltage"
                        
                        print(f"[Single Read] {mode_name} mode selected for channels: {enabled_channels}")
                        
                        if is_current_mode:
                            # Current mode: Use DAQ's direct current measurement (like other tool)
                            results = ni_service.read_current_channels_direct(enabled_channels, samples_per_channel=12)
                        else:
                            # Voltage mode: Use regular voltage measurement
                            results = ni_service.read_voltage_channels_trace_based(enabled_channels, samples_per_channel=12)
                        
                        print(f"[Single Read] {mode_name} mode results: {results}")
                        if results:
                            # Update channel displays based on measurement mode
                            is_current_mode = self.current_mode_rb.isChecked()
                            
                            for channel, data in results.items():
                                sample_count = data.get('sample_count', 0)
                                
                                # Update the channel widget display
                                if channel in self.channel_widgets:
                                    widget_data = self.channel_widgets[channel]
                                    
                                    if is_current_mode:
                                        # Current mode: Display measured current directly
                                        avg_current = data.get('avg_current', 0.0)  # Current in Amps
                                        if 'voltage_display' in widget_data:
                                            widget_data['voltage_display'].setText("N/A (Current Mode)")
                                        if 'current_display' in widget_data:
                                            widget_data['current_display'].setText(f"{avg_current*1000:.3f}mA")
                                            print(f"Channel {channel}: Direct current = {avg_current*1000:.3f}mA")
                                    else:
                                        # Voltage mode: Display voltage, calculate current if possible
                                        avg_voltage = data.get('avg_voltage', 0.0)
                                        if 'voltage_display' in widget_data:
                                            widget_data['voltage_display'].setText(f"{avg_voltage:.3f}V")
                                        if 'current_display' in widget_data:
                                            widget_data['current_display'].setText("N/A (Voltage Mode)")
                                            print(f"Channel {channel}: Voltage = {avg_voltage:.3f}V")
                                
                            mode_name = "Current" if is_current_mode else "Voltage"
                            self.status_label.setText(f"✅ {mode_name} mode read completed - {len(results)} channels")
                        else:
                            self.status_label.setText("❌ Single read failed - no data received")
                    except Exception as e:
                        self.status_label.setText(f"❌ Single read error: {e}")
                else:
                    self.status_label.setText("No channels enabled for reading")
            else:
                self.status_label.setText("DAQ not connected - connect device first")
        else:
            self.status_label.setText("DAQ service not available")
    
    def update_channel_display(self, channel: str, voltage: float, current: float):
        """Update channel display with new readings"""
        if channel in self.channel_widgets:
            widget_data = self.channel_widgets[channel]
            if 'voltage_display' in widget_data:
                widget_data['voltage_display'].setText(f"{voltage:.3f}V")
            if 'current_display' in widget_data:
                widget_data['current_display'].setText(f"{current*1000:.1f}mA")
    
    def save_config(self):
        """Save current configuration to file"""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Rail Configuration", "rail_config.json", "JSON Files (*.json)"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(self.channel_configs, f, indent=2)
                self.status_label.setText(f"Configuration saved to {filename}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Save Error", f"Failed to save:\n{e}")
    
    def load_config(self):
        """Load configuration from file"""
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Rail Configuration", "", "JSON Files (*.json)"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'r') as f:
                    configs = json.load(f)
                
                for channel, config in configs.items():
                    if channel in self.channel_widgets:
                        widgets = self.channel_widgets[channel]
                        widgets['name_edit'].setText(config.get('name', ''))
                        widgets['target_spin'].setValue(config.get('target_v', 0.0))
                        widgets['shunt_spin'].setValue(config.get('shunt_r', 0.010))
                        widgets['enable_cb'].setChecked(config.get('enabled', False))
                        
                        self.update_channel_config(channel)
                
                self.status_label.setText(f"Configuration loaded from {filename}")
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Load Error", f"Failed to load:\n{e}")