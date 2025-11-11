from PyQt6 import QtWidgets, QtCore
from PyQt6.uic import loadUi
import os

class TestSettingsDialog(QtWidgets.QDialog):
    """Test parameter settings dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load UI file
        ui_file = os.path.join(os.path.dirname(__file__), 'test_settings_dialog.ui')
        try:
            loadUi(ui_file, self)
        except Exception as e:
            # Fallback: create UI programmatically
            self._create_ui_programmatically()
        
        # Default settings
        self.settings = {
            'stabilization_voltage': 4.8,
            'test_voltage': 4.0,
            'test_cycles': 5,
            'test_duration': 10,
            'stabilization_time': 10,
            'sampling_interval': 1.0,
            'skip_stabilization_data': True,
            # DAQ Configuration
            'voltage_range': 5.0,  # ±5V (default)
            'sample_rate': 30000,  # Hz
            'compression_ratio': 30,  # 30:1
            'measurement_duration': 10.0  # seconds
        }
        
        # Connect signals
        self._connect_signals()
        
        # Load current settings
        self.load_settings()
    
    def _create_ui_programmatically(self):
        """Create UI programmatically if UI file loading fails"""
        self.setWindowTitle("Test Parameter Settings")
        self.setModal(True)
        self.resize(400, 500)
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Voltage Configuration
        voltage_group = QtWidgets.QGroupBox("Voltage Configuration")
        voltage_layout = QtWidgets.QFormLayout(voltage_group)
        
        self.stabilizationVoltage_SB = QtWidgets.QDoubleSpinBox()
        self.stabilizationVoltage_SB.setSuffix("V")
        self.stabilizationVoltage_SB.setDecimals(1)
        self.stabilizationVoltage_SB.setRange(0.0, 5.5)
        self.stabilizationVoltage_SB.setSingleStep(0.1)
        self.stabilizationVoltage_SB.setValue(4.8)
        
        self.testVoltage_SB = QtWidgets.QDoubleSpinBox()
        self.testVoltage_SB.setSuffix("V")
        self.testVoltage_SB.setDecimals(1)
        self.testVoltage_SB.setRange(0.0, 5.5)
        self.testVoltage_SB.setSingleStep(0.1)
        self.testVoltage_SB.setValue(4.0)
        
        voltage_layout.addRow("Stabilization Voltage:", self.stabilizationVoltage_SB)
        voltage_layout.addRow("Test Voltage:", self.testVoltage_SB)
        
        # Test Parameters
        params_group = QtWidgets.QGroupBox("Test Parameters")
        params_layout = QtWidgets.QFormLayout(params_group)
        
        self.testCycles_SB = QtWidgets.QSpinBox()
        self.testCycles_SB.setRange(1, 100)
        self.testCycles_SB.setValue(5)
        
        self.testDuration_SB = QtWidgets.QSpinBox()
        self.testDuration_SB.setSuffix("s")
        self.testDuration_SB.setRange(5, 3600)
        self.testDuration_SB.setValue(10)
        
        self.stabilizationTime_SB = QtWidgets.QSpinBox()
        self.stabilizationTime_SB.setSuffix("s")
        self.stabilizationTime_SB.setRange(5, 60)
        self.stabilizationTime_SB.setValue(10)
        
        params_layout.addRow("Test Cycles:", self.testCycles_SB)
        params_layout.addRow("Duration per cycle:", self.testDuration_SB)
        params_layout.addRow("Stabilization Time:", self.stabilizationTime_SB)
        
        # Data Collection
        data_group = QtWidgets.QGroupBox("Data Collection")
        data_layout = QtWidgets.QFormLayout(data_group)
        
        self.samplingInterval_SB = QtWidgets.QDoubleSpinBox()
        self.samplingInterval_SB.setSuffix("s")
        self.samplingInterval_SB.setDecimals(1)
        self.samplingInterval_SB.setRange(0.1, 10.0)
        self.samplingInterval_SB.setSingleStep(0.1)
        self.samplingInterval_SB.setValue(1.0)
        
        self.skipStabilization_CB = QtWidgets.QCheckBox("Skip stabilization data collection (collect only test voltage data)")
        self.skipStabilization_CB.setChecked(True)
        
        data_layout.addRow("Sampling Interval:", self.samplingInterval_SB)
        data_layout.addRow(self.skipStabilization_CB)
        
        # Buttons
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel |
            QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults
        )
        
        # Add to layout
        layout.addWidget(voltage_group)
        layout.addWidget(params_group)
        layout.addWidget(data_group)
        layout.addStretch()
        layout.addWidget(self.buttonBox)
    
    def _connect_signals(self):
        """Connect dialog signals"""
        if hasattr(self, 'buttonBox'):
            self.buttonBox.accepted.connect(self.accept)
            self.buttonBox.rejected.connect(self.reject)
            
            # Connect restore defaults button
            restore_button = self.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults)
            if restore_button:
                restore_button.clicked.connect(self.restore_defaults)
    
    def load_settings(self):
        """Load current settings into UI"""
        if hasattr(self, 'stabilizationVoltage_SB'):
            self.stabilizationVoltage_SB.setValue(self.settings['stabilization_voltage'])
        if hasattr(self, 'testVoltage_SB'):
            self.testVoltage_SB.setValue(self.settings['test_voltage'])
        if hasattr(self, 'testCycles_SB'):
            self.testCycles_SB.setValue(self.settings['test_cycles'])
        if hasattr(self, 'testDuration_SB'):
            self.testDuration_SB.setValue(self.settings['test_duration'])
        if hasattr(self, 'stabilizationTime_SB'):
            self.stabilizationTime_SB.setValue(self.settings['stabilization_time'])
        if hasattr(self, 'samplingInterval_SB'):
            self.samplingInterval_SB.setValue(self.settings['sampling_interval'])
        if hasattr(self, 'skipStabilization_CB'):
            self.skipStabilization_CB.setChecked(self.settings['skip_stabilization_data'])
        
        # Load DAQ settings
        if hasattr(self, 'voltageRange_CB'):
            voltage_range = self.settings.get('voltage_range', 5.0)
            index = 0 if voltage_range == 5.0 else 1
            self.voltageRange_CB.setCurrentIndex(index)
        if hasattr(self, 'sampleRate_SB'):
            self.sampleRate_SB.setValue(self.settings.get('sample_rate', 30000))
        if hasattr(self, 'compressionRatio_SB'):
            self.compressionRatio_SB.setValue(self.settings.get('compression_ratio', 30))
        if hasattr(self, 'measurementDuration_SB'):
            self.measurementDuration_SB.setValue(self.settings.get('measurement_duration', 10.0))
    
    def save_settings(self):
        """Save UI values to settings"""
        if hasattr(self, 'stabilizationVoltage_SB'):
            self.settings['stabilization_voltage'] = self.stabilizationVoltage_SB.value()
        if hasattr(self, 'testVoltage_SB'):
            self.settings['test_voltage'] = self.testVoltage_SB.value()
        if hasattr(self, 'testCycles_SB'):
            self.settings['test_cycles'] = self.testCycles_SB.value()
        if hasattr(self, 'testDuration_SB'):
            self.settings['test_duration'] = self.testDuration_SB.value()
        if hasattr(self, 'stabilizationTime_SB'):
            self.settings['stabilization_time'] = self.stabilizationTime_SB.value()
        if hasattr(self, 'samplingInterval_SB'):
            self.settings['sampling_interval'] = self.samplingInterval_SB.value()
        if hasattr(self, 'skipStabilization_CB'):
            self.settings['skip_stabilization_data'] = self.skipStabilization_CB.isChecked()
        
        # Save DAQ settings
        if hasattr(self, 'voltageRange_CB'):
            voltage_range_text = self.voltageRange_CB.currentText()
            self.settings['voltage_range'] = 5.0 if '±5V' in voltage_range_text else 10.0
        if hasattr(self, 'sampleRate_SB'):
            self.settings['sample_rate'] = self.sampleRate_SB.value()
        if hasattr(self, 'compressionRatio_SB'):
            self.settings['compression_ratio'] = self.compressionRatio_SB.value()
        if hasattr(self, 'measurementDuration_SB'):
            self.settings['measurement_duration'] = self.measurementDuration_SB.value()
    
    def restore_defaults(self):
        """Restore default settings"""
        defaults = {
            'stabilization_voltage': 4.8,
            'test_voltage': 4.0,
            'test_cycles': 5,
            'test_duration': 10,
            'stabilization_time': 10,
            'sampling_interval': 1.0,
            'skip_stabilization_data': True,
            # DAQ Configuration defaults
            'voltage_range': 5.0,
            'sample_rate': 30000,
            'compression_ratio': 30,
            'measurement_duration': 10.0
        }
        self.settings.update(defaults)
        self.load_settings()
    
    def get_settings(self):
        """Get current settings"""
        return self.settings.copy()
    
    def set_settings(self, settings):
        """Set settings"""
        self.settings.update(settings)
        self.load_settings()
    
    def accept(self):
        """Accept dialog and save settings"""
        self.save_settings()
        super().accept()