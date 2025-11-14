"""
Scenario Config Dialog
시나리오 선택 및 반복 횟수 설정을 위한 다이얼로그
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QCheckBox, QScrollArea,
                             QWidget, QFrame, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt


class ScenarioConfigDialog(QDialog):
    """Scenario configuration dialog for selecting test scenarios and repeat count"""
    
    def __init__(self, available_scenarios, parent=None):
        super().__init__(parent)
        self.available_scenarios = available_scenarios
        self.scenario_checkboxes = {}
        self.repeat_count = 1
        self.mode = "all"  # "all" or "manual"
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup UI components"""
        self.setWindowTitle("Scenario Configuration")
        self.setMinimumSize(500, 600)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Test Scenario Configuration")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2196F3;")
        main_layout.addWidget(title_label)
        
        # Mode selection (All / Manual)
        mode_frame = QFrame()
        mode_frame.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 5px; padding: 10px; }")
        mode_layout = QHBoxLayout(mode_frame)
        
        mode_label = QLabel("Test Mode:")
        mode_label.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup(self)
        self.all_radio = QRadioButton("All Scenarios")
        self.manual_radio = QRadioButton("Manual Selection")
        
        self.all_radio.setChecked(True)  # Default: All
        self.all_radio.toggled.connect(self.on_mode_changed)
        
        self.mode_group.addButton(self.all_radio)
        self.mode_group.addButton(self.manual_radio)
        
        mode_layout.addWidget(self.all_radio)
        mode_layout.addWidget(self.manual_radio)
        mode_layout.addStretch()
        
        main_layout.addWidget(mode_frame)
        
        # Repeat count
        repeat_frame = QFrame()
        repeat_frame.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 5px; padding: 10px; }")
        repeat_layout = QHBoxLayout(repeat_frame)
        
        repeat_label = QLabel("Repeat Count:")
        repeat_label.setStyleSheet("font-weight: bold;")
        repeat_layout.addWidget(repeat_label)
        
        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setMinimum(1)
        self.repeat_spinbox.setMaximum(100)
        self.repeat_spinbox.setValue(1)
        self.repeat_spinbox.setStyleSheet("font-size: 11pt; padding: 5px;")
        repeat_layout.addWidget(self.repeat_spinbox)
        
        repeat_info = QLabel("(Each scenario will run this many times)")
        repeat_info.setStyleSheet("color: #666; font-size: 9pt;")
        repeat_layout.addWidget(repeat_info)
        repeat_layout.addStretch()
        
        main_layout.addWidget(repeat_frame)
        
        # Scenario list
        scenarios_label = QLabel("Available Scenarios:")
        scenarios_label.setStyleSheet("font-weight: bold; font-size: 11pt; margin-top: 10px;")
        main_layout.addWidget(scenarios_label)
        
        # Scroll area for scenarios
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: 1px solid #ccc; border-radius: 5px; }")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(5)
        
        # Add checkbox for each scenario
        for scenario_key, scenario_config in self.available_scenarios.items():
            scenario_frame = QFrame()
            scenario_frame.setStyleSheet("""
                QFrame { 
                    background-color: white; 
                    border: 1px solid #ddd; 
                    border-radius: 5px; 
                    padding: 8px; 
                }
                QFrame:hover {
                    border: 1px solid #2196F3;
                }
            """)
            
            scenario_layout = QVBoxLayout(scenario_frame)
            scenario_layout.setContentsMargins(5, 5, 5, 5)
            
            checkbox = QCheckBox(scenario_config.name)
            checkbox.setStyleSheet("font-weight: bold; font-size: 10pt;")
            checkbox.setChecked(True)  # Default: all enabled
            checkbox.scenario_key = scenario_key  # Store scenario key
            
            description = QLabel(scenario_config.description)
            description.setStyleSheet("color: #666; font-size: 9pt; margin-left: 20px;")
            description.setWordWrap(True)
            
            duration_info = QLabel(f"Duration: ~{int(scenario_config.test_duration)}s test + setup")
            duration_info.setStyleSheet("color: #999; font-size: 8pt; margin-left: 20px;")
            
            scenario_layout.addWidget(checkbox)
            scenario_layout.addWidget(description)
            scenario_layout.addWidget(duration_info)
            
            scroll_layout.addWidget(scenario_frame)
            
            self.scenario_checkboxes[scenario_key] = checkbox
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # Button bar
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_scenarios)
        self.select_all_btn.setStyleSheet("padding: 8px 15px;")
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all_scenarios)
        self.deselect_all_btn.setStyleSheet("padding: 8px 15px;")
        button_layout.addWidget(self.deselect_all_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("padding: 8px 15px;")
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet("padding: 8px 15px; background-color: #2196F3; color: white; font-weight: bold;")
        button_layout.addWidget(ok_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # Initial mode setup
        self.on_mode_changed()
        
    def on_mode_changed(self):
        """Handle mode change (All vs Manual)"""
        is_all_mode = self.all_radio.isChecked()
        
        # Enable/disable scenario checkboxes based on mode
        for checkbox in self.scenario_checkboxes.values():
            if is_all_mode:
                checkbox.setChecked(True)
                checkbox.setEnabled(False)  # Disable manual selection in All mode
            else:
                checkbox.setEnabled(True)   # Enable manual selection in Manual mode
        
        # Enable/disable select all/deselect all buttons
        self.select_all_btn.setEnabled(not is_all_mode)
        self.deselect_all_btn.setEnabled(not is_all_mode)
        
    def select_all_scenarios(self):
        """Select all scenarios"""
        for checkbox in self.scenario_checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(True)
    
    def deselect_all_scenarios(self):
        """Deselect all scenarios"""
        for checkbox in self.scenario_checkboxes.values():
            if checkbox.isEnabled():
                checkbox.setChecked(False)
    
    def get_selected_scenarios(self):
        """Get list of selected scenario keys"""
        if self.all_radio.isChecked():
            # All mode: return all scenarios
            return list(self.available_scenarios.keys())
        else:
            # Manual mode: return only checked scenarios
            return [key for key, checkbox in self.scenario_checkboxes.items() 
                   if checkbox.isChecked()]
    
    def get_repeat_count(self):
        """Get repeat count"""
        return self.repeat_spinbox.value()
    
    def get_mode(self):
        """Get selected mode (all or manual)"""
        return "all" if self.all_radio.isChecked() else "manual"
