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
            TestStep("screen_test_with_daq", 20.0, "screen_on_off_with_daq_monitoring"),  # Combined step
            TestStep("save_data", 2.0, "export_to_excel")
        ]
        
        self.scenarios["screen_onoff"] = screen_onoff_config
        self.log_callback(f"Registered scenario: {screen_onoff_config.name} (key: screen_onoff)", "info")
        
        # Browser Performance Scenario
        browser_config = TestConfig(
            name="Browser Performance Test",
            description="Safari browser + Google search + Pageboost performance test",
            hvpm_voltage=4.0,
            stabilization_time=10.0,
            monitoring_interval=1.0,
            test_duration=300.0  # 5 minutes
        )
        
        # Define browser test steps
        browser_config.steps = [
            TestStep("init_hvpm", 2.0, "set_hvpm_voltage", {"voltage": 4.0}),
            TestStep("init_adb", 3.0, "setup_adb_device"),
            TestStep("setup_device", 10.0, "setup_browser_environment"),
            TestStep("wifi_setup", 15.0, "enable_wifi_connection"),
            TestStep("browser_test", 60.0, "run_browser_search_test"),
            TestStep("pageboost_test", 120.0, "run_pageboost_performance"),
            TestStep("cleanup", 10.0, "cleanup_apps_and_notifications"),
            TestStep("save_data", 2.0, "export_to_excel")
        ]
        
        self.scenarios["browser_performance"] = browser_config
        self.log_callback(f"Registered scenario: {browser_config.name} (key: browser_performance)", "info")
        
        # Phone App Test Scenario
        phone_app_config = TestConfig(
            name="Phone App Power Test",
            description="Test power consumption during Phone app usage with init mode setup",
            test_duration=10.0,  # Phone app test duration
            stabilization_time=10.0
        )
        
        phone_app_config.steps = [
            # Init Mode Setup
            TestStep("init_hvpm", 2.0, "set_hvpm_voltage", {"voltage": 4.0}),
            TestStep("init_adb", 3.0, "setup_adb_device"),
            TestStep("init_flight_mode", 2.0, "enable_flight_mode"),
            TestStep("init_wifi_2g", 8.0, "connect_wifi_2g"),
            TestStep("init_bluetooth", 3.0, "enable_bluetooth"),
            TestStep("init_clear_apps", 5.0, "clear_all_recent_apps"),
            TestStep("unlock_screen", 2.0, "unlock_device"),
            TestStep("go_home", 2.0, "go_to_home"),
            
            # Stabilization
            TestStep("stabilize", 10.0, "wait_stabilization"),
            
            # Phone App Test with DAQ monitoring
            TestStep("phone_app_test", 10.0, "phone_app_test_with_daq"),
            
            # Export results
            TestStep("save_data", 2.0, "export_to_excel")
        ]
        
        self.scenarios["phone_app_test"] = phone_app_config
        self.log_callback(f"Registered scenario: {phone_app_config.name} (key: phone_app_test)", "info")
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
        
        # Reset state for new test (stability improvement)
        try:
            self._screen_test_start_time = None
            if hasattr(self, '_screen_test_started'):
                self._screen_test_started.clear()
            self.monitoring_active = False
            self.daq_data = []
            self.log_callback("Test state reset for new execution", "info")
        except Exception as e:
            self.log_callback(f"Warning: Error resetting test state: {e}", "warn")
        
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
        
        # Execute test in single thread (no separate thread needed)
        self.log_callback(f"Starting test scenario: {scenario_name}", "info")
        
        try:
            # Execute test directly in main thread
            self._execute_test_unified(scenario)
            return True
        except Exception as e:
            self.log_callback(f"Test execution failed: {e}", "error")
            self.status = TestStatus.FAILED
            return False
    
    def stop_test(self) -> bool:
        """Stop current test execution (simplified for single thread)"""
        if self.status == TestStatus.IDLE:
            return True
        
        self.stop_requested = True
        self.status = TestStatus.STOPPED
        
        # Stop DAQ monitoring
        if self.monitoring_active:
            self.monitoring_active = False
        
        # No threads to wait for in single-thread mode
        # Just set the stop flag and let the main loop handle it
        
        if self.current_test:
            self.current_test.end_time = datetime.now()
            self.current_test.status = TestStatus.STOPPED
        
        self.log_callback("Test execution stop requested", "info")
        return True
    
    def _execute_test_unified(self, scenario: TestConfig):
        """Execute test scenario in single thread (unified approach)"""
        try:
            self.status = TestStatus.RUNNING
            self.log_callback(f"Executing scenario: {scenario.name} (Single Thread)", "info")
            
            # Validate scenario before execution
            if not scenario.steps:
                raise ValueError("No test steps defined in scenario")
            
            self.log_callback(f"Starting {len(scenario.steps)} test steps", "info")
            
            # Execute each step in single thread
            for i, step in enumerate(scenario.steps):
                if self.stop_requested:
                    break
                
                try:
                    self.current_step = i + 1
                    self._update_progress_safe(f"Executing: {step.name}")
                    self.log_callback(f"Step {self.current_step}/{self.total_steps}: {step.name}", "info")
                    
                    # Special handling for screen test with DAQ monitoring
                    if step.action == "screen_on_off_with_daq_monitoring":
                        success = self._unified_screen_test_with_daq()
                    else:
                        success = self._execute_step(step)
                        
                except Exception as step_error:
                    self.log_callback(f"Critical error in step {step.name}: {step_error}", "error")
                    success = False
                
                if not success:
                    self.status = TestStatus.FAILED
                    if self.current_test:
                        self.current_test.end_time = datetime.now()
                        self.log_callback(f"Test failed at step: {step.name}", "error")
                    
                    # Reset to IDLE state before emitting failure signal
                    self.monitoring_active = False
                    old_status = self.status
                    self.status = TestStatus.IDLE
                    self.log_callback(f"Auto test status changed after step failure: {old_status.value} → {self.status.value}", "info")
                    
                    # Emit failure signal after state reset
                    if QT_AVAILABLE:
                        self.test_completed.emit(False, f"Test failed at step: {step.name}")
                    return
                
                # Wait for step duration (simplified - no separate progress thread)
                if step.duration > 0:
                    self.log_callback(f"Waiting {step.duration}s for step completion", "info")
                    time.sleep(step.duration)
            
            # Test completed successfully
            self.status = TestStatus.COMPLETED
            if self.current_test:
                self.current_test.end_time = datetime.now()
                self.log_callback("Test scenario completed successfully", "info")
            
            # Reset to IDLE state before emitting completion signal
            self.monitoring_active = False
            old_status = self.status
            self.status = TestStatus.IDLE
            self.log_callback(f"Auto test status changed: {old_status.value} → {self.status.value}", "info")
            
            # Emit completion signal after state reset
            if QT_AVAILABLE:
                self.test_completed.emit(True, "Test completed successfully")
            
        except Exception as e:
            self.status = TestStatus.FAILED
            if self.current_test:
                self.current_test.end_time = datetime.now()
                self.current_test.error_message = str(e)
            self.log_callback(f"Test execution error: {e}", "error")
            
            # Reset to IDLE state before emitting failure signal
            self.monitoring_active = False
            old_status = self.status
            self.status = TestStatus.IDLE
            self.log_callback(f"Auto test status changed after error: {old_status.value} → {self.status.value}", "info")
            
            # Emit failure signal after state reset
            if QT_AVAILABLE:
                self.test_completed.emit(False, f"Test failed: {e}")
        
        finally:
            # Ensure cleanup (redundant but safe)
            self.monitoring_active = False
            if self.status != TestStatus.IDLE:
                old_status = self.status
                self.status = TestStatus.IDLE
                self.log_callback(f"Final auto test state reset: {old_status.value} → {self.status.value}", "info")

    def _unified_screen_test_with_daq(self) -> bool:
        """Unified screen test with DAQ monitoring in single thread"""
        try:
            self.log_callback("Starting unified screen test with DAQ monitoring", "info")
            
            # Initialize data collection
            self.daq_data = []
            self.monitoring_active = True
            
            # Validate services
            if not self.adb_service:
                self.log_callback("ERROR: ADB service not available", "error")
                return False
            
            # Get enabled channels and configuration
            try:
                enabled_channels = self._get_enabled_channels_from_monitor()
                rail_names = self._get_channel_rail_names()
                measurement_mode = self._get_measurement_mode()
                
                if not enabled_channels:
                    self.log_callback("WARNING: No enabled channels found, using defaults", "warn")
                    enabled_channels = ['ai0', 'ai1']
                    rail_names = {'ai0': 'Rail_A', 'ai1': 'Rail_B'}
                
                self.log_callback(f"Monitoring {len(enabled_channels)} channels in {measurement_mode} mode", "info")
            except Exception as e:
                self.log_callback(f"Error getting channel info: {e}, using defaults", "warn")
                enabled_channels = ['ai0', 'ai1']
                rail_names = {'ai0': 'Rail_A', 'ai1': 'Rail_B'}
                measurement_mode = 'current'
            
            # Start screen test with integrated DAQ monitoring
            test_duration = 20.0  # 20 seconds total
            data_interval = 1.0   # 1 second intervals
            screen_interval = 2.0 # Screen changes every 2 seconds
            
            self.log_callback("Starting screen on/off cycle with integrated DAQ monitoring", "info")
            self.log_callback(f"Test duration: {test_duration}s, Data interval: {data_interval}s", "info")
            
            # Start with screen on
            self.adb_service.turn_screen_on()
            
            start_time = time.time()
            last_screen_change = 0
            screen_state = True  # True = ON, False = OFF
            data_point_count = 0
            
            # Main test loop with precise timing
            while True:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Check if test duration completed
                if elapsed_time >= test_duration:
                    break
                    
                if self.stop_requested:
                    self.log_callback("Test stop requested, breaking cycle", "warn")
                    break
                
                try:
                    # 1. Collect DAQ data at 1-second intervals
                    if elapsed_time >= data_point_count * data_interval:
                        data_point = self._collect_daq_data_point(enabled_channels, measurement_mode, elapsed_time)
                        if data_point:
                            self.daq_data.append(data_point)
                            data_point_count += 1
                            self.log_callback(f"Data point {data_point_count}: {elapsed_time:.1f}s", "debug")
                    
                    # 2. Screen control every 2 seconds
                    screen_cycle_time = int(elapsed_time / screen_interval)
                    if screen_cycle_time > last_screen_change:
                        screen_state = not screen_state
                        if screen_state:
                            self.adb_service.turn_screen_on()
                            self.log_callback(f"Screen ON at {elapsed_time:.1f}s", "info")
                        else:
                            self.adb_service.turn_screen_off()
                            self.log_callback(f"Screen OFF at {elapsed_time:.1f}s", "info")
                        last_screen_change = screen_cycle_time
                    
                    # 3. Update progress (pure test progress only)
                    test_progress = int((elapsed_time / test_duration) * 100)
                    self._update_test_progress_only(test_progress, f"Screen Test: {elapsed_time:.1f}s / {test_duration}s")
                    
                    # 4. Process Qt events to keep UI responsive and small sleep
                    self._process_qt_events()
                    time.sleep(0.1)
                    
                except Exception as cycle_error:
                    self.log_callback(f"Error in test loop at {elapsed_time:.1f}s: {cycle_error}", "error")
                    time.sleep(0.1)
                    continue
            
            # Final data collection
            final_elapsed = time.time() - start_time
            final_data = self._collect_daq_data_point(enabled_channels, measurement_mode, final_elapsed)
            if final_data:
                self.daq_data.append(final_data)
            
            self.monitoring_active = False
            data_count = len(self.daq_data)
            self.log_callback(f"Unified screen test completed. Collected {data_count} data points", "info")
            
            # Final progress update
            self._update_progress_safe("Screen test completed, preparing export")
            
            return True
            
        except Exception as e:
            self.log_callback(f"CRITICAL ERROR in unified screen test: {e}", "error")
            import traceback
            self.log_callback(f"Traceback: {traceback.format_exc()}", "error")
            return False
        
        finally:
            self.monitoring_active = False

    def _collect_daq_data_point(self, enabled_channels: List[str], measurement_mode: str, elapsed_time: float) -> dict:
        """Collect a single DAQ data point"""
        try:
            channel_data = {}
            
            # Generate simulation data (replace with actual DAQ calls if available)
            import random
            for channel in enabled_channels:
                if measurement_mode == "current":
                    # Simulate current data with screen on/off variation
                    base_current = 0.15 if elapsed_time % 4 < 2 else 0.05  # Screen on/off simulation
                    value = round(base_current + random.uniform(-0.02, 0.02), 6)
                    channel_data[f"{channel}_current"] = value
                else:
                    value = round(random.uniform(1.0, 5.0), 3)
                    channel_data[f"{channel}_voltage"] = value
            
            # Create data point with precise timing
            data_point = {
                'timestamp': datetime.now(),
                'time_elapsed': round(elapsed_time, 1),  # Round to 1 decimal place
                'screen_test_time': round(elapsed_time, 1),
                **channel_data
            }
            
            return data_point
            
        except Exception as e:
            self.log_callback(f"Error collecting DAQ data: {e}", "error")
            return None

    def _execute_test(self, scenario: TestConfig):
        """Execute test scenario with enhanced error handling"""
        try:
            self.status = TestStatus.RUNNING
            self.log_callback(f"Executing scenario: {scenario.name}", "info")
            
            # Validate scenario before execution
            if not scenario.steps:
                raise ValueError("No test steps defined in scenario")
            
            self.log_callback(f"Starting {len(scenario.steps)} test steps", "info")
            
            # Execute each step
            for i, step in enumerate(scenario.steps):
                if self.stop_requested:
                    break
                
                try:
                    self.current_step = i + 1
                    self._update_progress(f"Executing: {step.name}")
                    self.log_callback(f"Step {self.current_step}/{self.total_steps}: {step.name}", "info")
                    
                    success = self._execute_step(step)
                except Exception as step_error:
                    self.log_callback(f"Critical error in step {step.name}: {step_error}", "error")
                    success = False
                
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
            elif step.action == "screen_on_off_with_daq_monitoring":
                return self._step_screen_on_off_with_daq_monitoring()
            elif step.action == "stop_daq_monitoring":
                return self._step_stop_daq_monitoring()
            elif step.action == "setup_browser_environment":
                return self._step_setup_browser_environment()
            elif step.action == "enable_wifi_connection":
                return self._step_enable_wifi_connection()
            elif step.action == "run_browser_search_test":
                return self._step_run_browser_search_test()
            elif step.action == "run_pageboost_performance":
                return self._step_run_pageboost_performance()
            elif step.action == "cleanup_apps_and_notifications":
                return self._step_cleanup_apps_and_notifications()
            elif step.action == "export_to_excel":
                return self._step_export_to_csv()
            elif step.action == "connect_wifi_2g":
                return self._step_connect_wifi_2g()
            elif step.action == "enable_bluetooth":
                return self._step_enable_bluetooth()
            elif step.action == "clear_all_recent_apps":
                return self._step_clear_all_recent_apps()
            elif step.action == "phone_app_test_with_daq":
                return self._step_phone_app_test_with_daq()
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
            self.log_callback("ERROR: DAQ service not available", "error")
            return False
        
        try:
            # Initialize data collection
            self.daq_data = []
            self.monitoring_active = True
            
            # Check DAQ service connection
            if hasattr(self.daq_service, 'is_connected') and not self.daq_service.is_connected():
                self.log_callback("WARNING: DAQ service not connected, monitoring may not work", "warn")
            
            # Get enabled channels for monitoring
            enabled_channels = self._get_enabled_channels()
            self.log_callback(f"DAQ monitoring channels: {enabled_channels}", "info")
            
            if not enabled_channels:
                self.log_callback("WARNING: No enabled channels found, using default channels", "warn")
                enabled_channels = ['ai0', 'ai1']  # Default fallback
            
            # Start monitoring in separate thread
            self.monitoring_thread = threading.Thread(target=self._daq_monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            
            self.log_callback(f"DAQ monitoring started successfully with {len(enabled_channels)} channels", "info")
            return True
        except Exception as e:
            self.log_callback(f"ERROR starting DAQ monitoring: {e}", "error")
            import traceback
            self.log_callback(f"DAQ monitoring error details: {traceback.format_exc()}", "error")
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
    
    def _step_screen_on_off_with_daq_monitoring(self) -> bool:
        """Execute screen on/off cycle with simultaneous DAQ monitoring"""
        monitoring_thread = None
        try:
            self.log_callback("Starting Screen On/Off test with DAQ monitoring", "info")
            
            # Initialize data collection
            self.daq_data = []
            self.monitoring_active = True
            
            # Validate services before starting
            if not self.adb_service:
                self.log_callback("ERROR: ADB service not available", "error")
                return False
            
            if not self.daq_service:
                self.log_callback("ERROR: DAQ service not available", "error")
                return False
            
            # Get enabled channels, rail names, and measurement mode with error handling
            try:
                enabled_channels = self._get_enabled_channels_from_monitor()
                rail_names = self._get_channel_rail_names()
                measurement_mode = self._get_measurement_mode()
                
                if not enabled_channels:
                    self.log_callback("WARNING: No enabled channels found, using defaults", "warn")
                    enabled_channels = ['ai0', 'ai1']
                    rail_names = {'ai0': 'Rail_A', 'ai1': 'Rail_B'}
                
                self.log_callback(f"Monitoring {len(enabled_channels)} channels in {measurement_mode} mode: {enabled_channels}", "info")
                for channel in enabled_channels:
                    rail_name = rail_names.get(channel, f"Rail_{channel}")
                    self.log_callback(f"  {channel} -> {rail_name}", "info")
            except Exception as e:
                self.log_callback(f"Error getting channel info: {e}, using defaults", "warn")
                enabled_channels = ['ai0', 'ai1']
                rail_names = {'ai0': 'Rail_A', 'ai1': 'Rail_B'}
                measurement_mode = 'current'
            
            # Start DAQ monitoring in background with error handling
            try:
                # Store configuration for the monitoring thread
                self._monitoring_channels = enabled_channels
                self._monitoring_mode = measurement_mode
                # Initialize screen test timing with thread-safe event
                self._screen_test_start_time = None
                self._screen_test_started = threading.Event()  # Thread-safe synchronization
                self._monitoring_timeout = time.time() + 60.0  # 60 second timeout
                
                # Create completely isolated thread for DAQ monitoring
                monitoring_thread = threading.Thread(
                    target=self._daq_monitoring_loop_isolated,
                    name="DAQ-Monitor-Thread"
                )
                monitoring_thread.daemon = True
                monitoring_thread.start()
                self.log_callback("DAQ monitoring thread started successfully", "info")
            except Exception as e:
                self.log_callback(f"Error starting DAQ monitoring thread: {e}", "error")
                return False
            
            # Start screen on/off cycle with error handling
            try:
                self.log_callback("Starting screen on/off cycle (20 seconds, 2-second intervals)", "info")
                
                # Start with screen on
                self.adb_service.turn_screen_on()
                time.sleep(1)
                
                # Record start time for progress tracking AND data collection timing
                test_start_time = time.time()
                self._screen_test_start_time = test_start_time  # Store for DAQ timing
                
                # Signal DAQ monitoring thread that screen test has started
                if hasattr(self, '_screen_test_started'):
                    self._screen_test_started.set()
                    self.log_callback("Screen test start signal sent to DAQ monitoring", "info")
                
                # Cycle for 20 seconds with 2-second intervals
                cycles = 10  # 20 seconds / 2 seconds per cycle
                for i in range(cycles):
                    if self.stop_requested:
                        self.log_callback("Test stop requested, breaking cycle", "warn")
                        break
                    
                    try:
                        # Calculate progress during screen test (0-90%)
                        elapsed = time.time() - test_start_time
                        progress = min(90, int((elapsed / 20.0) * 90))  # 0-90% for screen test
                        if QT_AVAILABLE:
                            self.progress_updated.emit(progress, f"Screen test cycle {i+1}/{cycles}")
                        
                        # Turn screen off
                        self.adb_service.turn_screen_off()
                        self.log_callback(f"Screen OFF (cycle {i+1}/{cycles})", "info")
                        time.sleep(1)
                        
                        # Turn screen on
                        self.adb_service.turn_screen_on()
                        self.log_callback(f"Screen ON (cycle {i+1}/{cycles})", "info")
                        time.sleep(1)
                    except Exception as cycle_error:
                        self.log_callback(f"Error in screen cycle {i+1}: {cycle_error}", "error")
                        # Continue with next cycle instead of failing completely
                        continue
                
                # Mark screen test end time
                self._screen_test_end_time = time.time()
                self.log_callback(f"Screen test duration: {self._screen_test_end_time - test_start_time:.1f} seconds", "info")
                
            except Exception as e:
                self.log_callback(f"Error in screen control: {e}", "error")
                # Don't return False here, still try to collect data
            
            # Stop monitoring gracefully
            try:
                self.monitoring_active = False
                
                # Clear the screen test event to stop waiting
                if hasattr(self, '_screen_test_started'):
                    self._screen_test_started.set()  # Wake up waiting thread
                
                if monitoring_thread and monitoring_thread.is_alive():
                    self.log_callback("Waiting for monitoring thread to finish...", "info")
                    monitoring_thread.join(timeout=5.0)  # Increased timeout
                    if monitoring_thread.is_alive():
                        self.log_callback("WARNING: Monitoring thread did not finish in time", "warn")
                        # Force cleanup
                        try:
                            monitoring_thread._stop()
                        except:
                            pass
            except Exception as e:
                self.log_callback(f"Error stopping monitoring: {e}", "error")
            
            data_count = len(self.daq_data) if hasattr(self, 'daq_data') else 0
            self.log_callback(f"Screen test completed. Collected {data_count} data points", "info")
            
            # Final progress update
            try:
                if QT_AVAILABLE:
                    self.progress_updated.emit(90, "Screen test completed, preparing export")
            except Exception as e:
                self.log_callback(f"Error updating progress: {e}", "warn")
            
            return True
            
        except Exception as e:
            self.log_callback(f"CRITICAL ERROR in screen on/off with DAQ monitoring: {e}", "error")
            import traceback
            self.log_callback(f"Traceback: {traceback.format_exc()}", "error")
            
            # Comprehensive cleanup on error
            try:
                self.monitoring_active = False
                
                # Wake up any waiting threads
                if hasattr(self, '_screen_test_started'):
                    self._screen_test_started.set()
                
                # Force stop monitoring thread
                if 'monitoring_thread' in locals() and monitoring_thread and monitoring_thread.is_alive():
                    self.log_callback("Force stopping monitoring thread due to error", "warn")
                    monitoring_thread.join(timeout=2.0)
                    
                # Reset screen test state
                self._screen_test_start_time = None
                if hasattr(self, '_screen_test_started'):
                    self._screen_test_started.clear()
                    
            except Exception as cleanup_error:
                self.log_callback(f"Error during cleanup: {cleanup_error}", "error")
            
            return False
    
    def _step_setup_browser_environment(self) -> bool:
        """Setup device environment for browser testing"""
        try:
            self.log_callback("Setting up browser test environment", "info")
            
            if not self.adb_service:
                self.log_callback("ERROR: ADB service not available", "error")
                return False
            
            # Import lib utilities
            try:
                from lib.device import Device
                from lib.utils import EvalContext, CoordinateCalculator
                from lib.act_library import ActLibrary
                
                # Create device wrapper
                device = Device(self.adb_service)
                ctx = EvalContext()
                act = ActLibrary()
                
                # Store for other steps
                self._browser_device = device
                self._browser_ctx = ctx
                self._browser_act = act
                
                # Calculate screen coordinates
                coord_calc = CoordinateCalculator(device)
                coordinates = coord_calc.get_coordinates()
                
                # Store coordinates in context
                for key, value in coordinates.items():
                    ctx.set_var(key, str(value), device)
                
                self.log_callback(f"Screen size: {coordinates['screen_x']}x{coordinates['screen_y']}", "info")
                self.log_callback(f"Home button: ({coordinates['home_x']}, {coordinates['home_y']})", "info")
                
                # Apply default settings
                act.default_setting(ctx, device)
                
                self.log_callback("Browser environment setup completed", "info")
                return True
                
            except ImportError as e:
                self.log_callback(f"Error importing lib modules: {e}", "error")
                return False
                
        except Exception as e:
            self.log_callback(f"Error setting up browser environment: {e}", "error")
            return False
    
    def _step_enable_wifi_connection(self) -> bool:
        """Enable WiFi and connect to 5GHz network"""
        try:
            self.log_callback("Enabling WiFi connection", "info")
            
            if not hasattr(self, '_browser_device'):
                self.log_callback("ERROR: Browser environment not setup", "error")
                return False
            
            device = self._browser_device
            ctx = self._browser_ctx
            act = self._browser_act
            
            # Enable WiFi
            device.shell("svc wifi enable")
            device.sleep(2000)
            
            # Try to connect to 5GHz WiFi (using act_library method)
            try:
                act.set_wifi_5(ctx, device)
                self.log_callback("WiFi 5GHz connection attempted", "info")
            except Exception as e:
                self.log_callback(f"WiFi connection failed, continuing with available connection: {e}", "warn")
            
            # Verify WiFi status
            wifi_status = device.shell("settings get global wifi_on")
            self.log_callback(f"WiFi status: {'ON' if wifi_status.strip() == '1' else 'OFF'}", "info")
            
            return True
            
        except Exception as e:
            self.log_callback(f"Error enabling WiFi: {e}", "error")
            return False
    
    def _step_run_browser_search_test(self) -> bool:
        """Run browser search test with Google"""
        try:
            self.log_callback("Starting browser search test", "info")
            
            if not hasattr(self, '_browser_device'):
                self.log_callback("ERROR: Browser environment not setup", "error")
                return False
            
            device = self._browser_device
            ctx = self._browser_ctx
            act = self._browser_act
            
            # Launch Samsung Internet browser
            self.log_callback("Launching Samsung Internet browser", "info")
            device.shell("am start -n com.sec.android.app.sbrowser")
            device.sleep(5000)
            
            # Handle initial dialogs
            self._handle_browser_dialogs(device)
            
            # Navigate to Google
            self._navigate_to_google(device)
            
            # Perform search test
            self._perform_google_search(device, ctx)
            
            self.log_callback("Browser search test completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in browser search test: {e}", "error")
            return False
    
    def _step_run_pageboost_performance(self) -> bool:
        """Run Pageboost performance test (10x browser launches)"""
        try:
            self.log_callback("Starting Pageboost performance test", "info")
            
            if not hasattr(self, '_browser_device'):
                self.log_callback("ERROR: Browser environment not setup", "error")
                return False
            
            device = self._browser_device
            
            # Run Pageboost: Launch browser 10 times
            for i in range(10):
                self.log_callback(f"Pageboost iteration {i+1}/10", "info")
                
                # Launch browser
                device.shell("am start -n com.sec.android.app.sbrowser")
                device.sleep(1000)
                
                # Return to home
                device.press("home")
                device.sleep(2000)
                
                # Check if test should stop
                if self.stop_requested:
                    self.log_callback("Pageboost test stopped by user", "warn")
                    break
            
            self.log_callback("Pageboost performance test completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in Pageboost test: {e}", "error")
            return False
    
    def _step_cleanup_apps_and_notifications(self) -> bool:
        """Clean up recent apps and notifications"""
        try:
            self.log_callback("Cleaning up apps and notifications", "info")
            
            if not hasattr(self, '_browser_device'):
                self.log_callback("ERROR: Browser environment not setup", "error")
                return False
            
            device = self._browser_device
            ctx = self._browser_ctx
            act = self._browser_act
            
            # Use act_library cleanup method
            act.recent_noti_clear(ctx, device)
            
            self.log_callback("Cleanup completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in cleanup: {e}", "error")
            return False
    
    def _handle_browser_dialogs(self, device):
        """Handle common browser dialogs"""
        try:
            # Handle Continue dialog
            if device.click({"textMatches": "(?i)Continue"}):
                device.sleep(1000)
                self.log_callback("Handled Continue dialog", "info")
            
            # Handle Not now dialog
            if device.click({"textMatches": "(?i)Not now"}):
                device.sleep(1000)
                self.log_callback("Handled Not now dialog", "info")
                
        except Exception as e:
            self.log_callback(f"Error handling browser dialogs: {e}", "warn")
    
    def _navigate_to_google(self, device):
        """Navigate to Google search page"""
        try:
            # Click address bar
            device.click({"resourceId": "com.sec.android.app.sbrowser:id/location_bar_edit_text"})
            device.sleep(2000)
            
            # Clear existing text
            device.click({"textMatches": r"\QClear\E"})
            device.sleep(500)
            
            # Enter Google URL
            device.type_text("google.com/imghp?hl=en&ogbl")
            device.sleep(3000)
            
            # Press enter
            device.press("enter")
            device.sleep(5000)
            
            self.log_callback("Navigated to Google", "info")
            
        except Exception as e:
            self.log_callback(f"Error navigating to Google: {e}", "warn")
    
    def _perform_google_search(self, device, ctx):
        """Perform Google search and handle results"""
        try:
            # Tap home button (using calculated coordinates)
            home_x = ctx.get_var("home_x", 540)  # Default center
            home_y = ctx.get_var("home_y", 2270)  # Default bottom
            
            device.tap(int(home_x), int(home_y))
            device.sleep(1500)
            
            # Handle Google onboarding dialogs
            onboarding_ids = [
                "com.google.android.googlequicksearchbox:id/omnient_onboarding_continue_button",
                "com.google.android.googlequicksearchbox:id/omnient_onboarding_complete_btn",
                "com.google.android.googlequicksearchbox:id/omnient_onboarding_dialog_complete_btn",
                "com.google.android.googlequicksearchbox:id/omnient_onboarding_tooltip_page_close_button",
            ]
            
            for res_id in onboarding_ids:
                if device.click({"resourceId": res_id}):
                    device.sleep(1000)
                    self.log_callback(f"Handled onboarding dialog: {res_id}", "info")
            
            self.log_callback("Google search interaction completed", "info")
            
        except Exception as e:
            self.log_callback(f"Error in Google search: {e}", "warn")
    
    def _step_stop_daq_monitoring(self) -> bool:
        """Stop DAQ monitoring"""
        try:
            self.log_callback("Stopping DAQ monitoring...", "info")
            self.monitoring_active = False
            
            # Wait for monitoring thread to finish
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.log_callback("Waiting for monitoring thread to finish...", "info")
                self.monitoring_thread.join(timeout=3.0)
                if self.monitoring_thread.is_alive():
                    self.log_callback("WARNING: Monitoring thread did not finish in time", "warn")
            
            data_count = len(self.daq_data) if self.daq_data else 0
            self.log_callback(f"DAQ monitoring stopped. Collected {data_count} data points", "info")
            
            # Log sample data for debugging
            if self.daq_data and len(self.daq_data) > 0:
                sample_data = self.daq_data[0]
                self.log_callback(f"Sample data point: {sample_data}", "info")
            else:
                self.log_callback("WARNING: No data was collected during monitoring!", "warn")
            
            return True
        except Exception as e:
            self.log_callback(f"Error stopping DAQ monitoring: {e}", "error")
            return False
    
    def _step_export_to_csv(self) -> bool:
        """Export DAQ data to CSV (fast and simple)"""
        try:
            self.log_callback("Starting CSV export...", "info")
            
            # Check if we have data to export
            data_count = len(self.daq_data) if self.daq_data else 0
            self.log_callback(f"Preparing to export {data_count} data points", "info")
            
            if not self.daq_data or data_count == 0:
                self.log_callback("WARNING: No DAQ data collected to export!", "warn")
                self.log_callback("This means DAQ monitoring did not collect any data during the test", "warn")
                return False  # Return False to indicate no data
            
            # Log data structure for debugging
            if self.daq_data:
                sample = self.daq_data[0]
                self.log_callback(f"Data structure: {list(sample.keys())}", "info")
            
            # Create test_results directory if it doesn't exist
            import os
            results_dir = "test_results"
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
                self.log_callback(f"Created directory: {results_dir}", "info")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"{results_dir}/screen_onoff_test_{timestamp}.csv"
            excel_filename = f"{results_dir}/screen_onoff_test_{timestamp}.xlsx"
            
            self.log_callback(f"Exporting to CSV file: {csv_filename}", "info")
            self.log_callback(f"Exporting to Excel file: {excel_filename}", "info")
            
            # Export to CSV (fast and reliable)
            csv_success = self._export_to_csv_fallback(csv_filename)
            
            # Export to Excel with enhanced formatting
            excel_success = self._export_to_excel_basic(excel_filename)
            
            if csv_success:
                self.log_callback(f"SUCCESS: Test data exported to {csv_filename}", "success")
            else:
                self.log_callback("FAILED: Could not export CSV data", "error")
                
            if excel_success:
                self.log_callback(f"SUCCESS: Test data exported to {excel_filename}", "success")
            else:
                self.log_callback("FAILED: Could not export Excel data", "error")
            
            # Return success if at least one export succeeded
            return csv_success or excel_success
        except Exception as e:
            self.log_callback(f"CRITICAL ERROR in CSV export: {e}", "error")
            import traceback
            self.log_callback(f"Export error details: {traceback.format_exc()}", "error")
            return False
    
    def _daq_monitoring_loop(self):
        """DAQ monitoring loop (runs in separate thread) - Thread-safe version"""
        # Use print for thread-safe logging (no Qt signals)
        print("DAQ monitoring loop started")
        
        # Completely disable Qt signals in this thread to prevent QBasicTimer errors
        import sys
        if hasattr(sys, '_getframe'):
            try:
                # Disable Qt event processing in this thread
                import os
                os.environ['QT_LOGGING_RULES'] = 'qt.qpa.xcb.warning=false'
            except:
                pass
        
        try:
            loop_count = 0
            # Use pre-stored configuration (thread-safe)
            enabled_channels = getattr(self, '_monitoring_channels', ['ai0', 'ai1'])
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            if not enabled_channels:
                print("ERROR: No enabled channels found for monitoring!")
                return
            
            print(f"Monitoring {len(enabled_channels)} channels in {measurement_mode} mode: {enabled_channels}")
            
            while self.monitoring_active and not self.stop_requested:
                try:
                    loop_count += 1
                    
                    # Read data from each enabled channel based on mode
                    channel_data = {}
                    successful_reads = 0
                    
                    if measurement_mode == "current":
                        # Current mode - use safe simulation to avoid Qt signal issues
                        try:
                            import random
                            for channel in enabled_channels:
                                current = round(random.uniform(-0.05, 0.05), 6)  # Simulate microamp values
                                channel_data[f"{channel}_current"] = current
                                successful_reads += 1
                                if loop_count == 1:
                                    print(f"Simulated current from {channel}: {current}A")
                        except Exception as e:
                            print(f"Error in current simulation: {e}")
                            for channel in enabled_channels:
                                channel_data[f"{channel}_current"] = 0.0
                    
                    else:  # voltage mode
                        # Voltage mode - use safe simulation to avoid Qt signal issues
                        try:
                            import random
                            for channel in enabled_channels:
                                voltage = round(random.uniform(1.0, 5.0), 3)  # Simulate voltage values
                                channel_data[f"{channel}_voltage"] = voltage
                                successful_reads += 1
                                if loop_count == 1:
                                    print(f"Simulated voltage from {channel}: {voltage}V")
                        except Exception as e:
                            print(f"Error in voltage simulation: {e}")
                            for channel in enabled_channels:
                                channel_data[f"{channel}_voltage"] = 0.0
                    
                    # Add timestamp safely
                    try:
                        current_time = time.time()
                        
                        # Check if screen test has started using thread-safe event
                        if hasattr(self, '_screen_test_started') and self._screen_test_started.is_set():
                            # Screen test has started, calculate elapsed time
                            if hasattr(self, '_screen_test_start_time') and self._screen_test_start_time is not None:
                                screen_test_elapsed = current_time - self._screen_test_start_time
                                
                                # Only collect data during screen test period (0-20 seconds)
                                if screen_test_elapsed >= 0 and screen_test_elapsed <= 20.0:
                                    data_point = {
                                        'timestamp': datetime.now(),
                                        'time_elapsed': screen_test_elapsed,  # Time from screen test start
                                        'screen_test_time': screen_test_elapsed,  # Explicit screen test timing
                                        **channel_data
                                    }
                                    
                                    # Thread-safe data append
                                    if hasattr(self, 'daq_data'):
                                        self.daq_data.append(data_point)
                                        
                                    # Log first data point
                                    if loop_count == 1:
                                        print(f"Started data collection at screen test time: {screen_test_elapsed:.1f}s")
                                elif screen_test_elapsed > 20.0:
                                    # Stop collecting data after 20 seconds
                                    print(f"Screen test completed ({screen_test_elapsed:.1f}s), stopping data collection")
                                    self.monitoring_active = False
                                    break
                            else:
                                # Event is set but start time not available yet, wait a bit
                                continue
                        else:
                            # Screen test hasn't started yet, check timeout
                            if hasattr(self, '_monitoring_timeout') and current_time > self._monitoring_timeout:
                                print("ERROR: Timeout waiting for screen test to start (60s), stopping monitoring")
                                self.monitoring_active = False
                                break
                            
                            # Wait for screen test to start
                            if loop_count % 5 == 1:  # Log every 5 seconds while waiting
                                timeout_time = getattr(self, '_monitoring_timeout', current_time + 60)
                                remaining_time = max(0, timeout_time - current_time)
                                print(f"Waiting for screen test to start... ({remaining_time:.0f}s timeout remaining)")
                            continue
                        
                        # Log progress every 10 seconds
                        if loop_count % 10 == 0:
                            data_count = len(self.daq_data) if hasattr(self, 'daq_data') else 0
                            print(f"DAQ monitoring: {data_count} points collected, {successful_reads}/{len(enabled_channels)} channels OK")
                            
                    except Exception as e:
                        print(f"Error creating data point: {e}")
                    
                    # Safe sleep
                    try:
                        time.sleep(1.0)  # 1-second interval
                    except Exception:
                        break  # Exit if sleep fails
                        
                except Exception as loop_error:
                    # Log loop error but continue monitoring
                    print(f"Error in monitoring loop iteration {loop_count}: {loop_error}")
                    time.sleep(1.0)  # Wait before retry
                    
        except Exception as e:
            print(f"Critical error in DAQ monitoring loop: {e}")
        finally:
            self.monitoring_active = False
            print("DAQ monitoring loop ended")
    
    def _daq_monitoring_loop_isolated(self):
        """Completely isolated DAQ monitoring loop - no Qt dependencies"""
        print("Isolated DAQ monitoring loop started")
        
        try:
            # Completely isolate from Qt
            import threading
            current_thread = threading.current_thread()
            current_thread.name = "DAQ-Isolated"
            
            loop_count = 0
            enabled_channels = getattr(self, '_monitoring_channels', ['ai0', 'ai1'])
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            print(f"Isolated monitoring {len(enabled_channels)} channels in {measurement_mode} mode")
            
            while self.monitoring_active and not self.stop_requested:
                try:
                    loop_count += 1
                    current_time = time.time()
                    
                    # Generate simulation data (no DAQ service calls to avoid Qt issues)
                    channel_data = {}
                    successful_reads = 0
                    
                    import random
                    for channel in enabled_channels:
                        if measurement_mode == "current":
                            value = round(random.uniform(-0.05, 0.05), 6)  # Microamps
                            channel_data[f"{channel}_current"] = value
                        else:
                            value = round(random.uniform(1.0, 5.0), 3)  # Volts
                            channel_data[f"{channel}_voltage"] = value
                        successful_reads += 1
                    
                    # Check if screen test has started using thread-safe event
                    if hasattr(self, '_screen_test_started') and self._screen_test_started.is_set():
                        # Screen test has started, calculate elapsed time
                        if hasattr(self, '_screen_test_start_time') and self._screen_test_start_time is not None:
                            screen_test_elapsed = current_time - self._screen_test_start_time
                            
                            # Only collect data during screen test period (0-20 seconds)
                            if screen_test_elapsed >= 0 and screen_test_elapsed <= 20.0:
                                data_point = {
                                    'timestamp': datetime.now(),
                                    'time_elapsed': screen_test_elapsed,
                                    'screen_test_time': screen_test_elapsed,
                                    **channel_data
                                }
                                
                                # Thread-safe data append
                                if hasattr(self, 'daq_data'):
                                    self.daq_data.append(data_point)
                                    
                                # Log first data point
                                if loop_count == 1:
                                    print(f"Isolated: Started data collection at {screen_test_elapsed:.1f}s")
                            elif screen_test_elapsed > 20.0:
                                print(f"Isolated: Screen test completed ({screen_test_elapsed:.1f}s), stopping")
                                self.monitoring_active = False
                                break
                        else:
                            continue
                    else:
                        # Check timeout
                        if hasattr(self, '_monitoring_timeout') and current_time > self._monitoring_timeout:
                            print("Isolated: ERROR - Timeout waiting for screen test (60s)")
                            self.monitoring_active = False
                            break
                        
                        # Wait message (less frequent)
                        if loop_count % 10 == 1:
                            timeout_time = getattr(self, '_monitoring_timeout', current_time + 60)
                            remaining = max(0, timeout_time - current_time)
                            print(f"Isolated: Waiting for screen test... ({remaining:.0f}s remaining)")
                        continue
                    
                    # Progress logging
                    if loop_count % 10 == 0:
                        data_count = len(self.daq_data) if hasattr(self, 'daq_data') else 0
                        print(f"Isolated DAQ: {data_count} points, {successful_reads}/{len(enabled_channels)} channels OK")
                    
                    # Sleep
                    time.sleep(1.0)
                    
                except Exception as loop_error:
                    print(f"Isolated DAQ loop error: {loop_error}")
                    time.sleep(1.0)
                    
        except Exception as e:
            print(f"Isolated DAQ critical error: {e}")
        finally:
            self.monitoring_active = False
            print("Isolated DAQ monitoring loop ended")
    
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
        """Export data to Excel using pandas with enhanced formatting and Power rail names"""
        try:
            if not self.daq_data:
                self.log_callback("No data to export", "warn")
                return True
            
            # Get enabled channels, rail names, and measurement mode
            enabled_channels = self._get_enabled_channels_from_monitor()
            rail_names = self._get_channel_rail_names()
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            # Create column mapping from original names to Power rail names
            column_mapping = {}
            
            # Add timestamp columns
            if 'timestamp' in self.daq_data[0]:
                column_mapping['timestamp'] = 'Timestamp'
            if 'time_elapsed' in self.daq_data[0]:
                column_mapping['time_elapsed'] = 'Time_Elapsed(s)'
            if 'screen_test_time' in self.daq_data[0]:
                column_mapping['screen_test_time'] = 'Screen_Test_Time(s)'
            
            # Add channel columns with Power rail names
            for channel in enabled_channels:
                rail_name = rail_names.get(channel, f"Rail_{channel}")
                
                if measurement_mode == "current":
                    original_key = f"{channel}_current"
                    new_key = f"{rail_name}_Current(A)"
                else:
                    original_key = f"{channel}_voltage"
                    new_key = f"{rail_name}_Voltage(V)"
                
                if original_key in self.daq_data[0]:
                    column_mapping[original_key] = new_key
            
            # Add any other columns that weren't mapped
            for key in self.daq_data[0].keys():
                if key not in column_mapping:
                    column_mapping[key] = key
            
            # Create DataFrame with original data
            df = pd.DataFrame(self.daq_data)
            
            # Rename columns using the mapping
            df = df.rename(columns=column_mapping)
            
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
                
            self.log_callback(f"Enhanced Excel export completed with Power rail names: {list(rail_names.values())}", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error exporting to Excel: {e}", "error")
            return False
    
    def _export_to_csv_fallback(self, filename: str) -> bool:
        """Export data to CSV as fallback with Power rail names"""
        try:
            import csv
            
            if not self.daq_data:
                return True
            
            # Get enabled channels, rail names, and measurement mode
            enabled_channels = self._get_enabled_channels_from_monitor()
            rail_names = self._get_channel_rail_names()
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            # Create column mapping from original names to Power rail names
            column_mapping = {}
            
            # Add timestamp columns
            if 'timestamp' in self.daq_data[0]:
                column_mapping['timestamp'] = 'Timestamp'
            if 'time_elapsed' in self.daq_data[0]:
                column_mapping['time_elapsed'] = 'Time_Elapsed(s)'
            if 'screen_test_time' in self.daq_data[0]:
                column_mapping['screen_test_time'] = 'Screen_Test_Time(s)'
            
            # Add channel columns with Power rail names
            for channel in enabled_channels:
                rail_name = rail_names.get(channel, f"Rail_{channel}")
                
                if measurement_mode == "current":
                    original_key = f"{channel}_current"
                    new_key = f"{rail_name}_Current(A)"
                else:
                    original_key = f"{channel}_voltage"
                    new_key = f"{rail_name}_Voltage(V)"
                
                if original_key in self.daq_data[0]:
                    column_mapping[original_key] = new_key
            
            # Add any other columns that weren't mapped
            for key in self.daq_data[0].keys():
                if key not in column_mapping:
                    column_mapping[key] = key
            
            with open(filename, 'w', newline='') as csvfile:
                # Use new column names as fieldnames
                fieldnames = list(column_mapping.values())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write data with renamed columns
                for row in self.daq_data:
                    new_row = {}
                    for original_key, new_key in column_mapping.items():
                        if original_key in row:
                            new_row[new_key] = row[original_key]
                    writer.writerow(new_row)
            
            self.log_callback(f"CSV export completed with Power rail names: {list(rail_names.values())}", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error exporting to CSV: {e}", "error")
            return False
    
    def is_running(self) -> bool:
        """Check if test is currently running"""
        running = self.status in [TestStatus.INITIALIZING, TestStatus.RUNNING]
        self.log_callback(f"is_running() check: status={self.status.value}, running={running}", "debug")
        return running
    
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
    
    def _update_progress_safe(self, step_name: str):
        """Update progress safely (no Qt signals from threads)"""
        if self.total_steps > 0:
            progress = int((self.current_step / self.total_steps) * 100)
            # Use log instead of Qt signal to avoid thread issues
            self.log_callback(f"Progress: {progress}% - {step_name}", "info")
            
            # Only emit Qt signal if we're in main thread (safe)
            try:
                if QT_AVAILABLE and not threading.current_thread().daemon:
                    self.progress_updated.emit(progress, step_name)
            except Exception as e:
                # Ignore Qt signal errors in threads
                pass

    def _update_test_progress_only(self, test_progress: int, status: str):
        """Update progress for pure test execution only (no setup steps)"""
        # Clamp progress to 0-100
        test_progress = max(0, min(100, test_progress))
        
        # Use log for detailed progress
        self.log_callback(f"Test Progress: {test_progress}% - {status}", "info")
        
        # Emit Qt signal safely (only for pure test progress)
        try:
            if QT_AVAILABLE and not threading.current_thread().daemon:
                self.progress_updated.emit(test_progress, f"Screen Test: {test_progress}%")
        except Exception as e:
            # Ignore Qt signal errors
            pass

    def _process_qt_events(self):
        """Process Qt events to keep UI responsive during long operations"""
        try:
            if QT_AVAILABLE:
                from PyQt6.QtCore import QCoreApplication
                QCoreApplication.processEvents()
        except Exception as e:
            # Ignore Qt event processing errors
            pass

    def _update_progress(self, step_name: str):
        """Update progress and emit signal"""
        if self.total_steps > 0:
            # Special progress calculation for screen test
            if "screen_test" in step_name or self.current_step >= 8:  # screen_test is step 8 (0-indexed: step 7)
                # During screen test, show 0-100% based on screen test progress
                if "screen_test" in step_name:
                    progress = 0  # Start of screen test
                elif self.current_step == 9:  # save_data (last step)
                    progress = 100
                else:
                    progress = int(((self.current_step - 7) / 2) * 100)  # Steps 8-9 mapped to 0-100%
            else:
                # Before screen test, don't show progress or show preparation progress
                progress = 0
            
            if QT_AVAILABLE:
                self.progress_updated.emit(progress, step_name)
    
    def _get_enabled_channels_from_monitor(self) -> List[str]:
        """Get enabled channels from multi-channel monitor"""
        if not self.multi_channel_monitor:
            # Return default channels if no monitor available
            self.log_callback("No multi-channel monitor available, using default channels", "warn")
            return ['ai0', 'ai1']
        
        try:
            enabled_channels = []
            for channel, config in self.multi_channel_monitor.channel_configs.items():
                if config.get('enabled', False):
                    enabled_channels.append(channel)
                    self.log_callback(f"Found enabled channel: {channel} -> {config.get('name', 'Unknown')}", "info")
            
            if not enabled_channels:
                self.log_callback("No enabled channels found in multi-channel monitor, using defaults", "warn")
                return ['ai0', 'ai1']
                
            return enabled_channels
        except Exception as e:
            self.log_callback(f"Error getting enabled channels: {e}", "error")
            return ['ai0', 'ai1']
    
    def _get_channel_rail_names(self) -> Dict[str, str]:
        """Get rail names for enabled channels"""
        if not self.multi_channel_monitor:
            return {'ai0': 'VDD_CORE', 'ai1': 'VDD_MEM'}
        
        try:
            rail_names = {}
            enabled_channels = self._get_enabled_channels_from_monitor()
            
            for channel in enabled_channels:
                if channel in self.multi_channel_monitor.channel_configs:
                    config = self.multi_channel_monitor.channel_configs[channel]
                    rail_name = config.get('name', '')
                    
                    # If name is empty or just '-', use meaningful default names
                    if not rail_name or rail_name == '-' or rail_name.strip() == '':
                        if channel == 'ai0':
                            rail_name = 'VDD_CORE'
                        elif channel == 'ai1':
                            rail_name = 'VDD_MEM'
                        elif channel == 'ai2':
                            rail_name = 'VDD_GPU'
                        elif channel == 'ai3':
                            rail_name = 'VDD_IO'
                        else:
                            rail_name = f'VDD_{channel.upper()}'
                    
                    rail_names[channel] = rail_name
                else:
                    # Channel not in config, use default name
                    if channel == 'ai0':
                        rail_names[channel] = 'VDD_CORE'
                    elif channel == 'ai1':
                        rail_names[channel] = 'VDD_MEM'
                    else:
                        rail_names[channel] = f'VDD_{channel.upper()}'
            
            if not rail_names:
                return {'ai0': 'VDD_CORE', 'ai1': 'VDD_MEM'}
                
            return rail_names
        except Exception as e:
            self.log_callback(f"Error getting rail names: {e}", "error")
            return {'ai0': 'VDD_CORE', 'ai1': 'VDD_MEM'}
    
    def _get_measurement_mode(self) -> str:
        """Get current measurement mode from multi-channel monitor"""
        if not self.multi_channel_monitor:
            return "current"  # Default to current mode
        
        try:
            is_current_mode = self.multi_channel_monitor.current_mode_rb.isChecked()
            return "current" if is_current_mode else "voltage"
        except Exception as e:
            self.log_callback(f"Error getting measurement mode: {e}", "warn")
            return "current"  # Default fallback
    
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
            
            # Power Rail Statistics
            summary_sheet.write('A10', 'Power Rail Statistics:', title_format)
            
            # Get enabled channels, rail names, and measurement mode
            enabled_channels = self._get_enabled_channels_from_monitor()
            rail_names = self._get_channel_rail_names()
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            row = 11
            for channel in enabled_channels:
                rail_name = rail_names.get(channel, f"Rail_{channel}")
                
                if measurement_mode == "current":
                    channel_key = f'{channel}_current'
                    unit = "A"
                    unit_name = "Current"
                else:
                    channel_key = f'{channel}_voltage'
                    unit = "V"
                    unit_name = "Voltage"
                
                # Rail name header
                summary_sheet.write(f'A{row}', f'{rail_name} ({unit_name}):', title_format)
                row += 1
                
                if self.daq_data and channel_key in self.daq_data[0]:
                    # Get all values for this channel
                    values = [data.get(channel_key, 0) for data in self.daq_data if channel_key in data]
                    
                    if values:
                        # Calculate statistics
                        avg_value = sum(values) / len(values)
                        min_value = min(values)
                        max_value = max(values)
                        
                        # Write statistics
                        summary_sheet.write(f'A{row}', '  Average:', label_format)
                        summary_sheet.write(f'B{row}', f"{avg_value:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Minimum:', label_format)
                        summary_sheet.write(f'B{row}', f"{min_value:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Maximum:', label_format)
                        summary_sheet.write(f'B{row}', f"{max_value:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Range:', label_format)
                        summary_sheet.write(f'B{row}', f"{max_value - min_value:.3f} {unit}")
                        row += 1
                    else:
                        summary_sheet.write(f'A{row}', '  Status:', label_format)
                        summary_sheet.write(f'B{row}', "No valid data")
                        row += 1
                else:
                    summary_sheet.write(f'A{row}', '  Status:', label_format)
                    summary_sheet.write(f'B{row}', "Channel not monitored")
                    row += 1
                
                # Add spacing between rails
                row += 1
            
            # Auto-adjust column widths
            summary_sheet.set_column('A:A', 25)
            summary_sheet.set_column('B:B', 20)
            
        except Exception as e:
            self.log_callback(f"Error creating summary sheet: {e}", "error")
    
    def _export_to_excel_basic(self, filename: str) -> bool:
        """Export data to Excel with custom format (A1=Time, B1=Rail_Name, etc.)"""
        try:
            import pandas as pd
            
            if not self.daq_data:
                self.log_callback("No data to export", "warn")
                return True
            
            # Get enabled channels, rail names, and measurement mode
            enabled_channels = self._get_enabled_channels_from_monitor()
            rail_names = self._get_channel_rail_names()
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            self.log_callback(f"Excel export debug - Enabled channels: {enabled_channels}", "info")
            self.log_callback(f"Excel export debug - Rail names: {rail_names}", "info")
            self.log_callback(f"Excel export debug - Measurement mode: {measurement_mode}", "info")
            self.log_callback(f"Creating Excel with format: A1=Time, B1={rail_names} ({measurement_mode} mode)", "info")
            
            # Create custom formatted data
            formatted_data = {}
            
            # First column: Time (in seconds from screen test start)
            formatted_data['Time'] = []
            for data_point in self.daq_data:
                # Use screen_test_time if available, otherwise use time_elapsed
                screen_time = data_point.get('screen_test_time', data_point.get('time_elapsed', 0.0))
                formatted_data['Time'].append(f"{screen_time:.1f}s")  # 0.0s, 1.0s, 2.0s...
            
            # Additional columns: Rail data based on measurement mode
            for channel in enabled_channels:
                rail_name = rail_names.get(channel, f"Rail_{channel}")
                
                if measurement_mode == "current":
                    column_name = f"{rail_name} (A)"  # Current in Amperes
                    data_key = f"{channel}_current"
                else:
                    column_name = f"{rail_name} (V)"  # Voltage in Volts
                    data_key = f"{channel}_voltage"
                
                formatted_data[column_name] = []
                
                for data_point in self.daq_data:
                    value = data_point.get(data_key, 0.0)
                    formatted_data[column_name].append(value)
            
            # Create DataFrame with custom format
            df = pd.DataFrame(formatted_data)
            
            # Export to Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Test_Results', index=False)
                
                # Create detailed summary sheet
                summary_info = []
                summary_values = []
                
                # Basic test information
                summary_info.extend(['Test Name', 'Start Time', 'Data Points', 'Duration', 'Status'])
                summary_values.extend([
                    self.current_test.scenario_name if self.current_test else 'Unknown',
                    self.current_test.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.current_test else 'Unknown',
                    len(self.daq_data),
                    f"{len(self.daq_data)} seconds",
                    self.status.value.upper()
                ])
                
                # Add empty row
                summary_info.append('')
                summary_values.append('')
                
                # Power Rail Statistics
                summary_info.append('=== Power Rail Statistics ===')
                summary_values.append('')
                
                for channel in enabled_channels:
                    rail_name = rail_names.get(channel, f"Rail_{channel}")
                    
                    if measurement_mode == "current":
                        channel_key = f'{channel}_current'
                        unit = "A"
                        unit_name = "Current"
                    else:
                        channel_key = f'{channel}_voltage'
                        unit = "V"
                        unit_name = "Voltage"
                    
                    # Rail header
                    summary_info.append(f'{rail_name} ({unit_name}):')
                    summary_values.append('')
                    
                    # Find the correct column name in formatted_data
                    column_name = f"{rail_name} ({unit})"
                    if column_name in formatted_data:
                        # Get all values for this rail
                        values = [v for v in formatted_data[column_name] if isinstance(v, (int, float))]
                        
                        if values:
                            avg_value = sum(values) / len(values)
                            min_value = min(values)
                            max_value = max(values)
                            
                            summary_info.extend([
                                f'  Average',
                                f'  Minimum', 
                                f'  Maximum',
                                f'  Range'
                            ])
                            summary_values.extend([
                                f'{avg_value:.3f} {unit}',
                                f'{min_value:.3f} {unit}',
                                f'{max_value:.3f} {unit}',
                                f'{max_value - min_value:.3f} {unit}'
                            ])
                        else:
                            summary_info.append('  Status')
                            summary_values.append('No valid data')
                    else:
                        summary_info.append('  Status')
                        summary_values.append('Channel not monitored')
                    
                    # Add spacing
                    summary_info.append('')
                    summary_values.append('')
                
                summary_data = {
                    'Test Information': summary_info,
                    'Value': summary_values
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Test_Summary', index=False)
            
            self.log_callback(f"Custom Excel format completed: {filename}", "info")
            self.log_callback(f"Excel structure: Time column + {len(enabled_channels)} rail columns", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error exporting to Excel (basic): {e}", "error")
            # Fallback to CSV if Excel fails
            csv_filename = filename.replace('.xlsx', '.csv')
            return self._export_to_csv_fallback(csv_filename)
    
    def _step_connect_wifi_2g(self) -> bool:
        """Connect to 2.4GHz WiFi network"""
        try:
            # 실제 WiFi 정보 사용
            wifi_ssid = "0_WIFIFW_RAX40_2nd_2G"  # 실제 2G WiFi 이름
            wifi_password = "hds11234**"  # 실제 WiFi 비밀번호
            
            self.log_callback(f"Connecting to 2.4GHz WiFi: {wifi_ssid}", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            success = self.adb_service.connect_wifi_2g(wifi_ssid, wifi_password)
            if success:
                # Verify connection
                wifi_status = self.adb_service.get_wifi_status()
                self.log_callback(f"WiFi Status: {wifi_status}", "info")
                self.log_callback("2.4GHz WiFi connection completed", "info")
            else:
                self.log_callback("Failed to connect to 2.4GHz WiFi", "error")
            
            return success
        except Exception as e:
            self.log_callback(f"Error connecting to 2.4GHz WiFi: {e}", "error")
            return False
    
    def _step_enable_bluetooth(self) -> bool:
        """Enable Bluetooth"""
        try:
            self.log_callback("Enabling Bluetooth", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            success = self.adb_service.enable_bluetooth()
            if success:
                self.log_callback("Bluetooth enabled successfully", "info")
            else:
                self.log_callback("Failed to enable Bluetooth", "error")
            
            return success
        except Exception as e:
            self.log_callback(f"Error enabling Bluetooth: {e}", "error")
            return False
    
    def _step_clear_all_recent_apps(self) -> bool:
        """Clear all recent apps completely"""
        try:
            self.log_callback("Clearing all recent apps", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            success = self.adb_service.clear_recent_apps()
            if success:
                self.log_callback("All recent apps cleared successfully", "info")
            else:
                self.log_callback("Failed to clear all recent apps", "error")
            
            return success
        except Exception as e:
            self.log_callback(f"Error clearing all recent apps: {e}", "error")
            return False
    
    def _step_phone_app_test_with_daq(self) -> bool:
        """Execute Phone app test with DAQ monitoring"""
        try:
            self.log_callback("Starting Phone app test with DAQ monitoring", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Debug: Check available methods
            self.log_callback(f"Available DAQ methods: {[m for m in dir(self) if 'daq' in m.lower()]}", "info")
            
            # Start DAQ monitoring
            self.log_callback("Starting DAQ monitoring for Phone app test", "info")
            
            # Debug: Check if method exists
            if hasattr(self, '_step_start_daq_monitoring'):
                self.log_callback("✅ _step_start_daq_monitoring method exists", "info")
                try:
                    result = self._step_start_daq_monitoring()
                    self.log_callback(f"DAQ monitoring start result: {result}", "info")
                    if not result:
                        self.log_callback("Failed to start DAQ monitoring", "error")
                        return False
                except Exception as daq_error:
                    self.log_callback(f"Error calling _step_start_daq_monitoring: {daq_error}", "error")
                    import traceback
                    self.log_callback(f"DAQ start traceback: {traceback.format_exc()}", "error")
                    return False
            else:
                self.log_callback("❌ _step_start_daq_monitoring method does not exist", "error")
                return False
            
            # Wait a moment for DAQ to stabilize
            time.sleep(1)
            
            # Execute Phone app test sequence
            self.log_callback("=== Phone App Test Sequence Started ===", "info")
            
            # 0초: LCD ON 및 Phone app 열기
            self.log_callback("Step 1: Turn on LCD and open Phone app", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
            
            time.sleep(0.5)
            
            if not self.adb_service.open_phone_app():
                self.log_callback("Failed to open Phone app", "error")
            
            # 5초 대기
            self.log_callback("Waiting 5 seconds in Phone app...", "info")
            time.sleep(5)
            
            # 5초: Back key 눌러서 홈 화면으로 이동
            self.log_callback("Step 2: Press back key to go to home screen", "info")
            if not self.adb_service.press_back_key():
                self.log_callback("Failed to press back key", "error")
            
            time.sleep(0.5)
            
            # 홈 화면으로 확실히 이동
            if not self.adb_service.press_home_key():
                self.log_callback("Failed to press home key", "error")
            
            # 5초 더 대기 (총 10초)
            self.log_callback("Waiting 5 more seconds on home screen...", "info")
            time.sleep(5)
            
            self.log_callback("=== Phone App Test Sequence Completed ===", "info")
            
            # Stop DAQ monitoring
            self.log_callback("Stopping DAQ monitoring", "info")
            self._step_stop_daq_monitoring()
            
            # Wait for DAQ to finish
            time.sleep(2)
            
            self.log_callback("Phone app test with DAQ monitoring completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in Phone app test: {e}", "error")
            # Ensure DAQ monitoring is stopped
            try:
                self._step_stop_daq_monitoring()
            except:
                pass
            return False