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
        self.setWindowTitle("Test Scenario Configuration")
        self.setMinimumSize(600, 650)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Title section
        title_layout = QHBoxLayout()
        title_label = QLabel("Test Scenario Configuration")
        from PyQt6.QtGui import QFont
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)
        
        # Mode selection (All / Manual) - GroupBox style
        mode_group_box = QGroupBox("Test Mode")
        mode_group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #3a3a3a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #42a5f5;
            }
        """)
        mode_layout = QHBoxLayout(mode_group_box)
        
        self.mode_group = QButtonGroup(self)
        self.all_radio = QRadioButton("All Scenarios")
        self.manual_radio = QRadioButton("Manual Selection")
        
        # Match multi_channel_monitor radio button style
        radio_style = """
            QRadioButton {
                font-weight: bold;
                color: #ffffff;
                spacing: 10px;
                font-size: 13px;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;
            }
            QRadioButton::indicator:unchecked {
                border: 3px solid #7f8c8d;
                background-color: #2b2b2b;
            }
            QRadioButton::indicator:unchecked:hover {
                border: 3px solid #aaaaaa;
                background-color: #3a3a3a;
            }
            QRadioButton::indicator:checked {
                border: 3px solid #42a5f5;
                background-color: #42a5f5;
            }
            QRadioButton::indicator:checked:hover {
                border: 3px solid #64b5f6;
                background-color: #64b5f6;
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
        
        main_layout.addWidget(mode_group_box)
        
        # Repeat count - GroupBox style
        repeat_group_box = QGroupBox("Repeat Configuration")
        repeat_group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #3a3a3a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #ff9800;
            }
        """)
        repeat_layout = QHBoxLayout(repeat_group_box)
        
        repeat_label = QLabel("Repeat Count:")
        repeat_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff;")
        repeat_layout.addWidget(repeat_label)
        
        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setMinimum(1)
        self.repeat_spinbox.setMaximum(100)
        self.repeat_spinbox.setValue(1)
        self.repeat_spinbox.setStyleSheet("""
            QSpinBox {
                font-size: 11pt; 
                font-weight: bold;
                padding: 8px;
                border: 2px solid #555555;
                border-radius: 5px;
                background-color: #2b2b2b;
                color: #ffffff;
                min-width: 80px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #555555;
                border: 1px solid #666666;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #666666;
            }
        """)
        repeat_layout.addWidget(self.repeat_spinbox)
        repeat_layout.addStretch()
        
        main_layout.addWidget(repeat_group_box)
        
        # Scenario list - GroupBox style
        scenarios_group_box = QGroupBox("Available Scenarios")
        scenarios_group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
                background-color: #3a3a3a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px 0 8px;
                color: #4CAF50;
            }
        """)
        scenarios_layout = QVBoxLayout(scenarios_group_box)
        
        # Scroll area for scenarios
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: 1px solid #555555; 
                border-radius: 5px;
                background-color: #2b2b2b;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(5)
        
        # Add checkbox for each scenario
        for scenario_key, scenario_config in self.available_scenarios.items():
            scenario_frame = QFrame()
            scenario_frame.setStyleSheet("""
                QFrame { 
                    background-color: #3a3a3a; 
                    border: 1px solid #555555; 
                    border-radius: 6px; 
                    padding: 10px; 
                }
                QFrame:hover {
                    background-color: #4a4a4a;
                    border: 1px solid #42a5f5;
                }
            """)
            
            scenario_layout = QVBoxLayout(scenario_frame)
            scenario_layout.setContentsMargins(8, 8, 8, 8)
            
            checkbox = QCheckBox(scenario_config.name)
            # Match multi_channel_monitor checkbox style
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-weight: bold; 
                    font-size: 11pt;
                    color: #ffffff;
                    spacing: 10px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
                QCheckBox::indicator::unchecked {
                    border: 2px solid #7f8c8d;
                    border-radius: 4px;
                    background-color: #2b2b2b;
                }
                QCheckBox::indicator::unchecked:hover {
                    border: 2px solid #aaaaaa;
                    background-color: #3a3a3a;
                }
                QCheckBox::indicator::checked {
                    border: 2px solid #4CAF50;
                    border-radius: 4px;
                    background-color: #4CAF50;
                }
                QCheckBox::indicator::checked:hover {
                    border: 2px solid #66bb6a;
                    background-color: #66bb6a;
                }
                QCheckBox:disabled {
                    color: #7f8c8d;
                }
            """)
            checkbox.setChecked(True)  # Default: all enabled
            checkbox.scenario_key = scenario_key  # Store scenario key
            
            scenario_layout.addWidget(checkbox)
            
            scroll_layout.addWidget(scenario_frame)
            
            self.scenario_checkboxes[scenario_key] = checkbox
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scenarios_layout.addWidget(scroll_area)
        main_layout.addWidget(scenarios_group_box)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_scenarios)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #4a4a4a;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #7f8c8d;
            }
        """)
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all_scenarios)
        self.deselect_all_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #4a4a4a;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #7f8c8d;
            }
        """)
        button_layout.addWidget(self.deselect_all_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
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
