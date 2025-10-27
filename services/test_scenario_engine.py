#!/usr/bin/env python3
"""
Test Scenario Engine for Automated Testing
Handles complex test scenarios with ADB, HVPM, and DAQ integration
"""

import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    def pyqtSignal(*args): return None

from .adb_service import ADBService


class TestStatus(Enum):
    """Test execution status"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TestStep:
    """Individual test step"""
    name: str
    duration: float  # seconds
    action: str
    parameters: Dict[str, Any] = None


@dataclass
class TestConfig:
    """Test configuration"""
    name: str
    description: str
    hvpm_voltage: float = 4.0
    stabilization_time: float = 20.0
    monitoring_interval: float = 1.0
    test_duration: float = 20.0
    steps: List[TestStep] = None


@dataclass
class TestResult:
    """Test execution result"""
    scenario_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TestStatus = TestStatus.IDLE
    daq_data: List[Dict[str, Any]] = None
    error_message: str = ""


class TestScenarioEngine(QObject):
    """Engine for executing complex test scenarios"""
    
    # Qt Signals for thread-safe communication
    progress_updated = pyqtSignal(int, str)  # progress, status
    test_completed = pyqtSignal(bool, str)   # success, message
    log_message = pyqtSignal(str, str)       # message, level
    
    def __init__(self, hvpm_service=None, daq_service=None, log_callback: Callable = None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.hvpm_service = hvpm_service
        self.daq_service = daq_service
        self.adb_service = ADBService()
        self.log_callback = log_callback or self._default_log
        
        self.current_test: Optional[TestResult] = None
        self.status = TestStatus.IDLE
        self.test_thread: Optional[threading.Thread] = None
        self.stop_requested = False
        
        # DAQ monitoring
        self.daq_data = []
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        
        # Multi-channel monitor integration
        self.multi_channel_monitor = None
        self.enabled_channels = []
        
        # Progress tracking
        self.current_step = 0
        self.total_steps = 0
        
        # Register built-in scenarios
        self.scenarios = {}
        self._register_builtin_scenarios()
    
    def _default_log(self, message: str, level: str = "info"):
        """Default logging function"""
        if level == "error":
            self.logger.error(message)
        elif level == "warn":
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        # Emit log signal for thread-safe UI updates
        if QT_AVAILABLE:
            self.log_message.emit(message, level)
    
    def _register_builtin_scenarios(self):
        """Register built-in test scenarios"""
        self.log_callback("Registering built-in test scenarios...", "info")
        
        # Screen On/Off Scenario
        screen_onoff_config = TestConfig(
            name="Screen On/Off",
            description="Test screen on/off power consumption with ADB, HVPM, and DAQ monitoring",
            hvpm_voltage=4.0,
            stabilization_time=20.0,
            monitoring_interval=1.0,
            test_duration=20.0
        )
        
        # Define test steps
        screen_onoff_config.steps = [
            TestStep("init_hvpm", 2.0, "set_hvpm_voltage", {"voltage": 4.0}),
            TestStep("init_adb", 3.0, "setup_adb_device"),
            TestStep("flight_mode", 2.0, "enable_flight_mode"),
            TestStep("clear_apps", 3.0, "clear_recent_apps"),
            TestStep("unlock_screen", 2.0, "unlock_device"),
            TestStep("home_screen", 2.0, "go_to_home"),
            TestStep("stabilize", 20.0, "wait_stabilization"),
            TestStep("start_monitoring", 1.0, "start_daq_monitoring"),
            TestStep("screen_test", 20.0, "screen_on_off_cycle"),
            TestStep("stop_monitoring", 1.0, "stop_daq_monitoring"),
            TestStep("save_data", 2.0, "export_to_excel")
        ]
        
        self.scenarios["screen_onoff"] = screen_onoff_config
        self.log_callback(f"Registered scenario: {screen_onoff_config.name} (key: screen_onoff)", "info")
        self.log_callback(f"Total scenarios registered: {len(self.scenarios)}", "info")
    
    def get_available_scenarios(self) -> Dict[str, TestConfig]:
        """Get all available test scenarios"""
        self.log_callback(f"get_available_scenarios called, returning {len(self.scenarios)} scenarios", "info")
        for key, config in self.scenarios.items():
            self.log_callback(f"  Available: {key} -> {config.name}", "info")
        return self.scenarios.copy()
    
    def start_test(self, scenario_name: str) -> bool:
        """Start test scenario execution"""
        if self.status != TestStatus.IDLE:
            self.log_callback("Test already running or not idle", "error")
            return False
        
        if scenario_name not in self.scenarios:
            self.log_callback(f"Unknown scenario: {scenario_name}", "error")
            return False
        
        scenario = self.scenarios[scenario_name]
        self.current_test = TestResult(
            scenario_name=scenario_name,
            start_time=datetime.now(),
            daq_data=[]
        )
        
        # Initialize progress tracking
        self.current_step = 0
        self.total_steps = len(scenario.steps)
        
        self.status = TestStatus.INITIALIZING
        self.stop_requested = False
        
        # Start test in separate thread
        self.test_thread = threading.Thread(target=self._execute_test, args=(scenario,))
        self.test_thread.daemon = True
        self.test_thread.start()
        
        self.log_callback(f"Started test scenario: {scenario_name}", "info")
        return True
    
    def stop_test(self) -> bool:
        """Stop current test execution"""
        if self.status == TestStatus.IDLE:
            return True
        
        self.stop_requested = True
        self.status = TestStatus.STOPPED
        
        # Stop DAQ monitoring
        if self.monitoring_active:
            self.monitoring_active = False
        
        # Wait for threads to finish
        if self.test_thread and self.test_thread.is_alive():
            self.test_thread.join(timeout=5.0)
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=3.0)
        
        if self.current_test:
            self.current_test.end_time = datetime.now()
            self.current_test.status = TestStatus.STOPPED
        
        self.log_callback("Test execution stopped", "info")
        return True
    
    def _execute_test(self, scenario: TestConfig):
        """Execute test scenario"""
        try:
            self.status = TestStatus.RUNNING
            self.log_callback(f"Executing scenario: {scenario.name}", "info")
            
            # Execute each step
            for i, step in enumerate(scenario.steps):
                if self.stop_requested:
                    break
                
                self.current_step = i + 1
                self._update_progress(f"Executing: {step.name}")
                self.log_callback(f"Step {self.current_step}/{self.total_steps}: {step.name}", "info")
                
                success = self._execute_step(step)
                
                if not success:
                    self.status = TestStatus.FAILED
                    self.current_test.status = TestStatus.FAILED
                    self.current_test.error_message = f"Failed at step: {step.name}"
                    self.current_test.end_time = datetime.now()
                    self.log_callback(f"Test failed at step: {step.name}", "error")
                    if QT_AVAILABLE:
                        self.test_completed.emit(False, f"Test failed at step: {step.name}")
                    return
                
                # Wait for step duration (with progress updates for long steps)
                if step.duration > 0:
                    if step.duration > 5:  # For long steps, show countdown
                        for remaining in range(int(step.duration), 0, -1):
                            if self.stop_requested:
                                break
                            self._update_progress(f"{step.name} - {remaining}s remaining")
                            time.sleep(1)
                    else:
                        time.sleep(step.duration)
            
            # Test completed successfully
            if not self.stop_requested:
                self.status = TestStatus.COMPLETED
                self.current_test.status = TestStatus.COMPLETED
                self.current_test.end_time = datetime.now()
                self.log_callback("Test scenario completed successfully", "info")
                if QT_AVAILABLE:
                    self.test_completed.emit(True, "Test completed successfully")
            
        except Exception as e:
            self.status = TestStatus.FAILED
            if self.current_test:
                self.current_test.status = TestStatus.FAILED
                self.current_test.error_message = str(e)
            self.log_callback(f"Test execution error: {e}", "error")
            if QT_AVAILABLE:
                self.test_completed.emit(False, f"Test failed: {e}")
        
        finally:
            # Cleanup
            if self.monitoring_active:
                self.monitoring_active = False
            self.status = TestStatus.IDLE
    
    def _execute_step(self, step: TestStep) -> bool:
        """Execute individual test step"""
        try:
            if step.action == "set_hvpm_voltage":
                return self._step_set_hvpm_voltage(step.parameters.get("voltage", 4.0))
            elif step.action == "setup_adb_device":
                return self._step_setup_adb()
            elif step.action == "enable_flight_mode":
                return self._step_enable_flight_mode()
            elif step.action == "clear_recent_apps":
                return self._step_clear_recent_apps()
            elif step.action == "unlock_device":
                return self._step_unlock_device()
            elif step.action == "go_to_home":
                return self._step_go_to_home()
            elif step.action == "wait_stabilization":
                return self._step_wait_stabilization()
            elif step.action == "start_daq_monitoring":
                return self._step_start_daq_monitoring()
            elif step.action == "screen_on_off_cycle":
                return self._step_screen_on_off_cycle()
            elif step.action == "stop_daq_monitoring":
                return self._step_stop_daq_monitoring()
            elif step.action == "export_to_excel":
                return self._step_export_to_excel()
            else:
                self.log_callback(f"Unknown step action: {step.action}", "error")
                return False
                
        except Exception as e:
            self.log_callback(f"Error executing step {step.name}: {e}", "error")
            return False
    
    def _step_set_hvpm_voltage(self, voltage: float) -> bool:
        """Set HVPM voltage"""
        if not self.hvpm_service:
            self.log_callback("HVPM service not available", "error")
            return False
        
        try:
            success = self.hvpm_service.set_voltage(voltage)
            if success:
                self.log_callback(f"HVPM voltage set to {voltage}V", "info")
            else:
                self.log_callback(f"Failed to set HVPM voltage to {voltage}V", "error")
            return success
        except Exception as e:
            self.log_callback(f"Error setting HVPM voltage: {e}", "error")
            return False
    
    def _step_setup_adb(self) -> bool:
        """Setup ADB device connection"""
        try:
            devices = self.adb_service.get_connected_devices()
            if not devices:
                self.log_callback("No ADB devices found", "error")
                return False
            
            success = self.adb_service.connect_device(devices[0])
            if success:
                self.log_callback(f"Connected to ADB device: {devices[0]}", "info")
            else:
                self.log_callback("Failed to connect to ADB device", "error")
            return success
        except Exception as e:
            self.log_callback(f"Error setting up ADB: {e}", "error")
            return False
    
    def _step_enable_flight_mode(self) -> bool:
        """Enable flight mode"""
        try:
            success = self.adb_service.enable_flight_mode()
            if success:
                self.log_callback("Flight mode enabled", "info")
            else:
                self.log_callback("Failed to enable flight mode", "error")
            return success
        except Exception as e:
            self.log_callback(f"Error enabling flight mode: {e}", "error")
            return False
    
    def _step_clear_recent_apps(self) -> bool:
        """Clear recent apps"""
        try:
            success = self.adb_service.clear_recent_apps()
            if success:
                self.log_callback("Recent apps cleared", "info")
            else:
                self.log_callback("Failed to clear recent apps", "error")
            return success
        except Exception as e:
            self.log_callback(f"Error clearing recent apps: {e}", "error")
            return False
    
    def _step_unlock_device(self) -> bool:
        """Unlock device screen"""
        try:
            success = self.adb_service.unlock_screen()
            if success:
                self.log_callback("Device screen unlocked", "info")
            else:
                self.log_callback("Failed to unlock device screen", "error")
            return success
        except Exception as e:
            self.log_callback(f"Error unlocking device: {e}", "error")
            return False
    
    def _step_go_to_home(self) -> bool:
        """Go to home screen"""
        try:
            success = self.adb_service.press_home_key()
            if success:
                self.log_callback("Navigated to home screen", "info")
            else:
                self.log_callback("Failed to navigate to home screen", "error")
            return success
        except Exception as e:
            self.log_callback(f"Error going to home screen: {e}", "error")
            return False
    
    def _step_wait_stabilization(self) -> bool:
        """Wait for current stabilization"""
        self.log_callback("Waiting for current stabilization (20 seconds)...", "info")
        # This step's duration is handled by the main execution loop
        return True
    
    def _step_start_daq_monitoring(self) -> bool:
        """Start DAQ monitoring"""
        if not self.daq_service:
            self.log_callback("DAQ service not available", "error")
            return False
        
        try:
            self.daq_data = []
            self.monitoring_active = True
            
            # Start monitoring in separate thread
            self.monitoring_thread = threading.Thread(target=self._daq_monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            
            self.log_callback("DAQ monitoring started", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error starting DAQ monitoring: {e}", "error")
            return False
    
    def _step_screen_on_off_cycle(self) -> bool:
        """Execute screen on/off cycle"""
        try:
            self.log_callback("Starting screen on/off cycle (20 seconds, 2-second intervals)", "info")
            
            # Start with screen on
            self.adb_service.turn_screen_on()
            time.sleep(1)
            
            # Cycle for 20 seconds with 2-second intervals
            cycles = 10  # 20 seconds / 2 seconds per cycle
            for i in range(cycles):
                if self.stop_requested:
                    break
                
                # Turn screen off
                self.adb_service.turn_screen_off()
                self.log_callback(f"Screen OFF (cycle {i+1}/{cycles})", "info")
                time.sleep(1)
                
                # Turn screen on
                self.adb_service.turn_screen_on()
                self.log_callback(f"Screen ON (cycle {i+1}/{cycles})", "info")
                time.sleep(1)
            
            self.log_callback("Screen on/off cycle completed", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error in screen on/off cycle: {e}", "error")
            return False
    
    def _step_stop_daq_monitoring(self) -> bool:
        """Stop DAQ monitoring"""
        try:
            self.monitoring_active = False
            
            # Wait for monitoring thread to finish
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=3.0)
            
            self.log_callback(f"DAQ monitoring stopped. Collected {len(self.daq_data)} data points", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error stopping DAQ monitoring: {e}", "error")
            return False
    
    def _step_export_to_excel(self) -> bool:
        """Export DAQ data to Excel"""
        try:
            if not self.daq_data:
                self.log_callback("No DAQ data to export", "warn")
                return True
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screen_onoff_test_{timestamp}.xlsx"
            
            if PANDAS_AVAILABLE:
                if XLSXWRITER_AVAILABLE:
                    success = self._export_to_excel_pandas(filename)
                else:
                    # Use basic pandas Excel writer without xlsxwriter
                    success = self._export_to_excel_basic(filename)
            else:
                success = self._export_to_csv_fallback(filename.replace('.xlsx', '.csv'))
            
            if success:
                self.log_callback(f"Test data exported to {filename}", "info")
            else:
                self.log_callback("Failed to export test data", "error")
            
            return success
        except Exception as e:
            self.log_callback(f"Error exporting data: {e}", "error")
            return False
    
    def _daq_monitoring_loop(self):
        """DAQ monitoring loop (runs in separate thread)"""
        try:
            while self.monitoring_active and not self.stop_requested:
                # Get enabled channels from multi-channel monitor
                enabled_channels = self._get_enabled_channels()
                
                if enabled_channels:
                    # Read current from each enabled channel
                    channel_data = {}
                    for channel in enabled_channels:
                        try:
                            # Read current from DAQ service
                            current = self._read_channel_current(channel)
                            channel_data[f"{channel}_current"] = current
                        except Exception as e:
                            self.log_callback(f"Error reading channel {channel}: {e}", "error")
                            channel_data[f"{channel}_current"] = 0.0
                    
                    # Add timestamp
                    data_point = {
                        'timestamp': datetime.now(),
                        'time_elapsed': (datetime.now() - self.current_test.start_time).total_seconds(),
                        **channel_data
                    }
                    
                    self.daq_data.append(data_point)
                
                time.sleep(1.0)  # 1-second interval
                
        except Exception as e:
            self.log_callback(f"Error in DAQ monitoring loop: {e}", "error")
    
    def _get_enabled_channels(self) -> List[str]:
        """Get list of enabled channels from multi-channel monitor"""
        return self._get_enabled_channels_from_monitor()
    
    def _read_channel_current(self, channel: str) -> float:
        """Read current from specific DAQ channel"""
        if not self.daq_service:
            return 0.0
        
        try:
            # Use DAQ service to read current (current implementation doesn't support multi-channel)
            # For now, read from the connected channel regardless of the requested channel
            current_value = self.daq_service.read_current_once()
            return current_value or 0.0
        except Exception as e:
            self.log_callback(f"Error reading current from {channel}: {e}", "error")
            return 0.0
    
    def _export_to_excel_pandas(self, filename: str) -> bool:
        """Export data to Excel using pandas with enhanced formatting"""
        try:
            if not self.daq_data:
                self.log_callback("No data to export", "warn")
                return True
            
            # Create DataFrame
            df = pd.DataFrame(self.daq_data)
            
            # Create Excel writer with xlsxwriter engine for formatting
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Test_Data', index=False)
                
                # Get workbook and worksheet objects
                workbook = writer.book
                worksheet = writer.sheets['Test_Data']
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                # Format headers
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Auto-adjust column widths
                for i, col in enumerate(df.columns):
                    column_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
                    worksheet.set_column(i, i, min(column_len, 50))
                
                # Add test summary sheet
                self._add_test_summary_sheet(writer, workbook)
                
            self.log_callback(f"Enhanced Excel export completed: {filename}", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error exporting to Excel: {e}", "error")
            return False
    
    def _export_to_csv_fallback(self, filename: str) -> bool:
        """Export data to CSV as fallback"""
        try:
            import csv
            
            if not self.daq_data:
                return True
            
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = self.daq_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.daq_data)
            
            return True
        except Exception as e:
            self.log_callback(f"Error exporting to CSV: {e}", "error")
            return False
    
    def is_running(self) -> bool:
        """Check if test is currently running"""
        return self.status in [TestStatus.INITIALIZING, TestStatus.RUNNING]
    
    def get_status(self) -> TestStatus:
        """Get current test status"""
        return self.status
    
    def get_current_test(self) -> Optional[TestResult]:
        """Get current test result"""
        return self.current_test
    
    def connect_progress_callback(self, callback: Callable[[int, str], None]):
        """Connect progress callback to signal"""
        if QT_AVAILABLE:
            self.progress_updated.connect(callback)
    
    def set_multi_channel_monitor(self, monitor):
        """Set multi-channel monitor reference"""
        self.multi_channel_monitor = monitor
    
    def _update_progress(self, step_name: str):
        """Update progress and emit signal"""
        if self.total_steps > 0:
            progress = int((self.current_step / self.total_steps) * 100)
            if QT_AVAILABLE:
                self.progress_updated.emit(progress, step_name)
    
    def _get_enabled_channels_from_monitor(self) -> List[str]:
        """Get enabled channels from multi-channel monitor"""
        if not self.multi_channel_monitor:
            # Return default channels if no monitor available
            return ['ai0', 'ai1']
        
        try:
            enabled_channels = []
            for channel, config in self.multi_channel_monitor.channel_configs.items():
                if config.get('enabled', False):
                    enabled_channels.append(channel)
            return enabled_channels
        except Exception as e:
            self.log_callback(f"Error getting enabled channels: {e}", "error")
            return ['ai0', 'ai1']
    
    def _add_test_summary_sheet(self, writer, workbook):
        """Add test summary sheet to Excel file"""
        try:
            # Create summary sheet
            summary_sheet = workbook.add_worksheet('Test_Summary')
            
            # Formats
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 16,
                'fg_color': '#4CAF50',
                'font_color': 'white'
            })
            
            label_format = workbook.add_format({
                'bold': True,
                'fg_color': '#E8F5E8'
            })
            
            # Test information
            summary_sheet.write('A1', 'Test Summary', title_format)
            summary_sheet.write('A3', 'Test Name:', label_format)
            summary_sheet.write('B3', self.current_test.scenario_name if self.current_test else 'Unknown')
            
            summary_sheet.write('A4', 'Start Time:', label_format)
            summary_sheet.write('B4', self.current_test.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.current_test else 'Unknown')
            
            summary_sheet.write('A5', 'End Time:', label_format)
            end_time = self.current_test.end_time if self.current_test and self.current_test.end_time else datetime.now()
            summary_sheet.write('B5', end_time.strftime('%Y-%m-%d %H:%M:%S'))
            
            summary_sheet.write('A6', 'Duration:', label_format)
            if self.current_test:
                duration = (end_time - self.current_test.start_time).total_seconds()
                summary_sheet.write('B6', f"{duration:.1f} seconds")
            
            summary_sheet.write('A7', 'Status:', label_format)
            summary_sheet.write('B7', self.status.value.upper())
            
            summary_sheet.write('A8', 'Data Points:', label_format)
            summary_sheet.write('B8', len(self.daq_data))
            
            # Channel information
            summary_sheet.write('A10', 'Monitored Channels:', title_format)
            enabled_channels = self._get_enabled_channels()
            for i, channel in enumerate(enabled_channels):
                summary_sheet.write(f'A{11+i}', f'Channel {channel}:', label_format)
                # Calculate average current for this channel
                channel_key = f'{channel}_current'
                if self.daq_data and channel_key in self.daq_data[0]:
                    avg_current = sum(data.get(channel_key, 0) for data in self.daq_data) / len(self.daq_data)
                    summary_sheet.write(f'B{11+i}', f"{avg_current:.3f} A (avg)")
                else:
                    summary_sheet.write(f'B{11+i}', "No data")
            
            # Auto-adjust column widths
            summary_sheet.set_column('A:A', 20)
            summary_sheet.set_column('B:B', 25)
            
        except Exception as e:
            self.log_callback(f"Error creating summary sheet: {e}", "error")
    
    def _export_to_excel_basic(self, filename: str) -> bool:
        """Export data to Excel using basic pandas writer (without xlsxwriter)"""
        try:
            if not self.daq_data:
                self.log_callback("No data to export", "warn")
                return True
            
            # Create DataFrame
            df = pd.DataFrame(self.daq_data)
            
            # Use basic Excel writer (openpyxl engine)
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Test_Data', index=False)
                
                # Create basic summary sheet
                summary_data = {
                    'Test Information': [
                        'Test Name',
                        'Start Time', 
                        'Data Points',
                        'Status'
                    ],
                    'Value': [
                        self.current_test.scenario_name if self.current_test else 'Unknown',
                        self.current_test.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.current_test else 'Unknown',
                        len(self.daq_data),
                        self.status.value.upper()
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Test_Summary', index=False)
            
            self.log_callback(f"Basic Excel export completed: {filename}", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error exporting to Excel (basic): {e}", "error")
            # Fallback to CSV if Excel fails
            csv_filename = filename.replace('.xlsx', '.csv')
            return self._export_to_csv_fallback(csv_filename)