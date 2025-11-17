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
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2196F3; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # Mode selection (All / Manual)
        mode_frame = QFrame()
        mode_frame.setStyleSheet("""
            QFrame { 
                background-color: #e3f2fd; 
                border: 2px solid #2196F3;
                border-radius: 8px; 
                padding: 15px; 
            }
        """)
        mode_layout = QHBoxLayout(mode_frame)
        
        mode_label = QLabel("Test Mode:")
        mode_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #1976D2;")
        mode_layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup(self)
        self.all_radio = QRadioButton("All Scenarios")
        self.manual_radio = QRadioButton("Manual Selection")
        
        # Improved radio button styling for better visibility
        radio_style = """
            QRadioButton {
                font-size: 11pt;
                font-weight: bold;
                color: #333;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
            }
            QRadioButton::indicator::unchecked {
                border: 2px solid #999;
                border-radius: 10px;
                background-color: white;
            }
            QRadioButton::indicator::checked {
                border: 2px solid #2196F3;
                border-radius: 10px;
                background-color: #2196F3;
            }
        """
        self.all_radio.setStyleSheet(radio_style)
        self.manual_radio.setStyleSheet(radio_style)
        
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
        repeat_frame.setStyleSheet("""
            QFrame { 
                background-color: #fff3e0; 
                border: 2px solid #FF9800;
                border-radius: 8px; 
                padding: 15px; 
            }
        """)
        repeat_layout = QHBoxLayout(repeat_frame)
        
        repeat_label = QLabel("Repeat Count:")
        repeat_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #F57C00;")
        repeat_layout.addWidget(repeat_label)
        
        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setMinimum(1)
        self.repeat_spinbox.setMaximum(100)
        self.repeat_spinbox.setValue(1)
        self.repeat_spinbox.setStyleSheet("""
            QSpinBox {
                font-size: 12pt; 
                font-weight: bold;
                padding: 8px;
                border: 2px solid #FF9800;
                border-radius: 5px;
                background-color: white;
                min-width: 80px;
            }
        """)
        repeat_layout.addWidget(self.repeat_spinbox)
        repeat_layout.addStretch()
        
        main_layout.addWidget(repeat_frame)
        
        # Scenario list
        scenarios_label = QLabel("Available Scenarios:")
        scenarios_label.setStyleSheet("font-weight: bold; font-size: 13pt; margin-top: 15px; color: #4CAF50;")
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
                    background-color: #f9f9f9; 
                    border: 2px solid #4CAF50; 
                    border-radius: 8px; 
                    padding: 12px; 
                }
                QFrame:hover {
                    background-color: #e8f5e9;
                    border: 2px solid #2196F3;
                }
            """)
            
            scenario_layout = QVBoxLayout(scenario_frame)
            scenario_layout.setContentsMargins(8, 8, 8, 8)
            
            checkbox = QCheckBox(scenario_config.name)
            # Improved checkbox styling for better visibility
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-weight: bold; 
                    font-size: 11pt;
                    color: #1976D2;
                    spacing: 10px;
                }
                QCheckBox::indicator {
                    width: 22px;
                    height: 22px;
                }
                QCheckBox::indicator::unchecked {
                    border: 2px solid #999;
                    border-radius: 4px;
                    background-color: white;
                }
                QCheckBox::indicator::checked {
                    border: 2px solid #4CAF50;
                    border-radius: 4px;
                    background-color: #4CAF50;
                    image: none;
                }
                QCheckBox::indicator::checked::after {
                    content: "✓";
                    color: white;
                }
                QCheckBox:disabled {
                    color: #999;
                }
            """)
            checkbox.setChecked(True)  # Default: all enabled
            checkbox.scenario_key = scenario_key  # Store scenario key
            
            scenario_layout.addWidget(checkbox)
            
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
