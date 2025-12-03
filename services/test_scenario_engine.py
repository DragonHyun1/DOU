#!/usr/bin/env python3
"""
Test Scenario Engine for Automated Testing
Handles complex test scenarios with ADB, HVPM, and DAQ integration
"""

import time
import logging
import threading
import os
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
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QMetaObject, Qt
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
    monitoring_interval: float = 0.001  # 1ms interval
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
        self._emit_signal_safe(self.log_message, message, level)
    
    def _emit_signal_safe(self, signal, *args):
        """Thread-safe signal emission"""
        if QT_AVAILABLE:
            try:
                # Qt signals are thread-safe by default when using queued connections
                # Just emit directly - Qt will handle the thread safety
                signal.emit(*args)
            except Exception as e:
                # Fallback to print if Qt signals fail
                print(f"Signal emit error: {e}, args: {args}")
    
    def _register_builtin_scenarios(self):
        """Register built-in test scenarios"""
        self.log_callback("Registering built-in test scenarios...", "info")
        
        # Removed Screen On/Off and Browser Performance Test scenarios
        
        # Phone App Test Scenario
        phone_app_config = TestConfig(
            name="Phone App Power Test",
            description="Test power consumption during Phone app usage with init mode setup",
            test_duration=10.0,  # Phone app test duration
            stabilization_time=10.0
        )
        
        phone_app_config.steps = [
            # Init Mode Setup - Scenario-specific settings
            TestStep("init_hvpm", 2.0, "set_hvpm_voltage", {"voltage": 4.0}),
            TestStep("init_adb", 3.0, "setup_adb_device"),
            
            # Default Settings - Clean state (after ADB connection)
            TestStep("default_settings", 5.0, "apply_default_settings"),
            
            TestStep("lcd_on_unlock_early", 3.0, "lcd_on_and_unlock"),  # LCD ON + Unlock first
            TestStep("init_flight_mode", 2.0, "enable_flight_mode"),
            TestStep("init_wifi_2g", 8.0, "connect_wifi_2g"),
            TestStep("home_after_wifi", 2.0, "go_to_home"),  # Home after WiFi
            TestStep("init_bluetooth", 3.0, "enable_bluetooth"),
            TestStep("home_after_bluetooth", 2.0, "go_to_home"),  # Home after Bluetooth
            TestStep("init_screen_timeout", 3.0, "set_screen_timeout_10min"),
            TestStep("init_clear_apps", 8.0, "home_and_clear_apps_only"),  # No unlock (already done)
            
            # Stabilization - 75 seconds for current stabilization after WiFi/Bluetooth
            TestStep("stabilize", 75.0, "wait_stabilization"),
            
            # DAQ Start + Phone App Test + DAQ Stop (separated)
            TestStep("start_daq", 2.0, "start_daq_monitoring"),
            TestStep("phone_app_test", 10.0, "phone_app_scenario_test"),
            TestStep("stop_daq", 2.0, "stop_daq_monitoring"),
            
            # Export results
            TestStep("save_data", 2.0, "export_to_excel")
        ]
        
        self.scenarios["phone_app_test"] = phone_app_config
        self.log_callback(f"Registered scenario: {phone_app_config.name} (key: phone_app_test)", "info")
        
        # Idle Wait Test Scenario (same init as Phone App, but waits 5 minutes after DAQ start)
        idle_wait_config = TestConfig(
            name="Idle Wait Test",
            description="Phone app 시나리오와 동일한 init 부분까지 진행하지만, DAQ 시작 후 앱을 실행하지 않고 5분간 대기",
            test_duration=300.0,  # 5 minutes = 300 seconds
            stabilization_time=10.0
        )
        
        idle_wait_config.steps = [
            # Init Mode Setup (same as Phone App)
            TestStep("init_hvpm", 2.0, "set_hvpm_voltage", {"voltage": 4.0}),
            TestStep("init_adb", 3.0, "setup_adb_device"),
            TestStep("init_flight_mode", 2.0, "enable_flight_mode"),
            TestStep("init_wifi_2g", 8.0, "connect_wifi_2g"),
            TestStep("init_bluetooth", 3.0, "enable_bluetooth"),
            TestStep("init_screen_timeout", 3.0, "set_screen_timeout_10min"),
            TestStep("init_unlock_clear", 10.0, "lcd_on_unlock_home_clear_apps"),
            
            # Stabilization (current stabilization for 10 seconds)
            TestStep("stabilize", 10.0, "wait_stabilization"),
            
            # DAQ Start + Idle Wait (5 minutes) + DAQ Stop
            TestStep("start_daq", 2.0, "start_daq_monitoring"),
            TestStep("idle_wait", 300.0, "idle_wait_test"),  # 5 minutes = 300 seconds
            TestStep("stop_daq", 2.0, "stop_daq_monitoring"),
            
            # Export results
            TestStep("save_data", 2.0, "export_to_excel")
        ]
        
        self.scenarios["idle_wait_test"] = idle_wait_config
        self.log_callback(f"Registered scenario: {idle_wait_config.name} (key: idle_wait_test)", "info")
        
        # Screen On/Off Test Scenario (LCD를 2초마다 켜고 끄는 전력 소비 테스트)
        screen_onoff_config = TestConfig(
            name="Screen On/Off Test",
            description="LCD를 2초마다 켜고 끄는 전력 소비 테스트",
            test_duration=20.0,  # 20초 테스트
            stabilization_time=60.0  # 1분 안정화
        )
        
        screen_onoff_config.steps = [
            # Init Mode Setup - ADB connection first
            TestStep("init_adb", 3.0, "setup_adb_device"),
            
            # Default Settings (after ADB connection)
            TestStep("default_settings", 5.0, "apply_default_settings"),
            
            # Init Mode Setup
            TestStep("lcd_on_unlock", 3.0, "lcd_on_and_unlock"),
            TestStep("flight_mode", 2.0, "enable_flight_mode"),
            TestStep("bluetooth_on", 3.0, "enable_bluetooth"),
            TestStep("clear_apps", 8.0, "clear_recent_apps"),
            TestStep("lcd_off", 2.0, "lcd_off"),
            
            # 전류 안정화 1분
            TestStep("stabilize", 60.0, "wait_stabilization"),
            
            # DAQ Start + Screen On/Off Test + DAQ Stop
            TestStep("start_daq", 2.0, "start_daq_monitoring"),
            TestStep("screen_onoff_test", 20.0, "screen_onoff_test"),
            TestStep("stop_daq", 2.0, "stop_daq_monitoring"),
            
            # Export results
            TestStep("save_data", 2.0, "export_to_excel")
        ]
        
        self.scenarios["screen_onoff_test"] = screen_onoff_config
        self.log_callback(f"Registered scenario: {screen_onoff_config.name} (key: screen_onoff_test)", "info")
        self.log_callback(f"Total scenarios registered: {len(self.scenarios)}", "info")
    
    def get_available_scenarios(self) -> Dict[str, TestConfig]:
        """Get all available test scenarios"""
        self.log_callback(f"get_available_scenarios called, returning {len(self.scenarios)} scenarios", "info")
        for key, config in self.scenarios.items():
            self.log_callback(f"  Available: {key} -> {config.name}", "info")
        return self.scenarios.copy()
    
    def start_test(self, scenario_name: str, repeat_count: int = 1) -> bool:
        """Start test scenario execution with repeat
        
        Args:
            scenario_name: Scenario to execute
            repeat_count: Number of times to repeat (default: 1)
        """
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
        self.current_scenario = scenario_name  # Store current scenario name for DAQ duration
        self.current_test = TestResult(
            scenario_name=scenario_name,
            start_time=datetime.now(),
            daq_data=[]
        )
        
        # Initialize progress tracking
        self.current_step = 0
        self.total_steps = len(scenario.steps)
        
        # Store repeat count
        self.repeat_count = repeat_count
        self.current_repeat = 0
        
        self.status = TestStatus.INITIALIZING
        self.stop_requested = False
        
        # Execute test in separate thread for UI responsiveness
        self.log_callback(f"Starting test scenario: {scenario_name} (Repeat: {repeat_count} times)", "info")
        
        try:
            # Start test in separate thread to prevent UI blocking
            self.test_thread = threading.Thread(
                target=self._execute_test_with_repeat,
                args=(scenario,),
                daemon=True
            )
            self.test_thread.start()
            return True
        except Exception as e:
            self.log_callback(f"Test execution failed to start: {e}", "error")
            self.status = TestStatus.FAILED
            return False
    
    def stop_test(self) -> bool:
        """Stop current test execution"""
        if self.status == TestStatus.IDLE:
            return True
        
        self.log_callback("Stopping test execution...", "info")
        self.stop_requested = True
        self.status = TestStatus.STOPPED
        
        # Stop DAQ monitoring
        if self.monitoring_active:
            self.monitoring_active = False
        
        # Wait for test thread to finish
        if hasattr(self, 'test_thread') and self.test_thread and self.test_thread.is_alive():
            self.log_callback("Waiting for test thread to finish...", "info")
            self.test_thread.join(timeout=3.0)
            if self.test_thread.is_alive():
                self.log_callback("WARNING: Test thread did not finish in time", "warn")
        
        # Wait for monitoring thread to finish
        if hasattr(self, 'monitoring_thread') and self.monitoring_thread and self.monitoring_thread.is_alive():
            self.log_callback("Waiting for monitoring thread to finish...", "info")
            self.monitoring_thread.join(timeout=2.0)
            if self.monitoring_thread.is_alive():
                self.log_callback("WARNING: Monitoring thread did not finish in time", "warn")
        
        if self.current_test:
            self.current_test.end_time = datetime.now()
            self.current_test.status = TestStatus.STOPPED
        
        self.log_callback("Test execution stopped", "info")
        return True
    
    def _interruptible_sleep(self, duration: float) -> bool:
        """
        Sleep for the given duration while checking for stop requests.
        Returns True if completed normally, False if interrupted.
        """
        if duration <= 0:
            return True
        
        # Sleep in small chunks to allow quick response to stop requests
        chunk_size = 0.1  # Check every 100ms
        remaining = duration
        
        while remaining > 0 and not self.stop_requested:
            sleep_time = min(chunk_size, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time
            
            # Note: Do NOT process Qt events here as this runs in a worker thread
            # Qt events can only be processed in the main thread
        
        return not self.stop_requested
    
    def _execute_test_with_repeat(self, scenario: TestConfig):
        """Execute test scenario with repeat logic"""
        try:
            for repeat_idx in range(self.repeat_count):
                if self.stop_requested:
                    self.log_callback("Test stopped by user", "warn")
                    break
                
                self.current_repeat = repeat_idx + 1
                self.log_callback(f"", "info")
                self.log_callback(f"{'='*60}", "info")
                self.log_callback(f"🔄 Test Iteration {self.current_repeat}/{self.repeat_count}", "info")
                self.log_callback(f"{'='*60}", "info")
                
                # First iteration: Full init
                if repeat_idx == 0:
                    self.log_callback("📌 First iteration: Running full initialization", "info")
                    success = self._execute_test_unified(scenario, is_first_iteration=True)
                else:
                    # Subsequent iterations: Quick reset only (no default/init)
                    self.log_callback(f"📌 Iteration {self.current_repeat}: Skip default+init, quick reset only", "info")
                    success = self._execute_test_unified(scenario, is_first_iteration=False)
                
                if not success and not self.stop_requested:
                    self.log_callback(f"❌ Test iteration {self.current_repeat} failed", "error")
                    break
                
                # Brief pause between iterations (except last one)
                if repeat_idx < self.repeat_count - 1:
                    self.log_callback(f"✅ Completed iteration {self.current_repeat}/{self.repeat_count}", "info")
                    if not self._interruptible_sleep(2):
                        break
            
            # All iterations completed
            if not self.stop_requested:
                self.log_callback(f"", "info")
                self.log_callback(f"🎉 All {self.repeat_count} test iterations completed successfully!", "info")
                self.status = TestStatus.COMPLETED
                self._emit_signal_safe(self.test_completed, True, f"Completed {self.repeat_count} iterations")
            else:
                self.status = TestStatus.STOPPED
                self._emit_signal_safe(self.test_completed, False, "Test stopped by user")
                
        except Exception as e:
            self.log_callback(f"Error in repeat test execution: {e}", "error")
            import traceback
            self.log_callback(f"Traceback: {traceback.format_exc()}", "error")
            self.status = TestStatus.FAILED
            self._emit_signal_safe(self.test_completed, False, f"Test failed: {e}")
        finally:
            # CRITICAL: Reset to IDLE state to allow re-running tests
            self.running = False
            self.monitoring_active = False
            self.status = TestStatus.IDLE
            self.log_callback("Test execution completed, status reset to IDLE", "info")
    
    def _execute_test_unified(self, scenario: TestConfig, is_first_iteration: bool = True):
        """Execute test scenario in single thread (unified approach)"""
        try:
            self.status = TestStatus.RUNNING
            self.log_callback(f"Executing scenario: {scenario.name} (Single Thread)", "info")
            
            # Validate scenario before execution
            if not scenario.steps:
                raise ValueError("No test steps defined in scenario")
            
            # Filter steps based on iteration
            if is_first_iteration:
                # First iteration: Execute all steps
                steps_to_execute = scenario.steps
                self.log_callback(f"Starting {len(steps_to_execute)} test steps (full initialization)", "info")
            else:
                # Subsequent iterations: Quick reset + DAQ + Test + Stop DAQ + Export
                # Duration is 0 because waiting is handled inside the step itself
                quick_reset_step = TestStep("quick_reset", 0.0, "quick_reset_before_test")
                
                # Find DAQ and test steps (skip all init/default/stabilization steps)
                # We want to keep: start_daq, test, stop_daq, export
                daq_test_steps = []
                for step in scenario.steps:
                    # Skip init, default, stabilization steps
                    if any(keyword in step.name.lower() for keyword in ['init', 'default', 'stabilize']):
                        self.log_callback(f"  Skipping step: {step.name} (action: {step.action})", "debug")
                        continue
                    
                    # Include DAQ, test, and export steps
                    if step.action in ['start_daq_monitoring', 'phone_app_scenario_test', 
                                       'screen_on_off_with_daq_monitoring', 'screen_on_off_cycle',
                                       'stop_daq_monitoring', 'export_to_excel', 'idle_wait_test']:
                        self.log_callback(f"  Including step: {step.name} (action: {step.action})", "debug")
                        daq_test_steps.append(step)
                
                steps_to_execute = [quick_reset_step] + daq_test_steps
                self.log_callback(f"Iteration {self.current_repeat}/{self.repeat_count}: {len(steps_to_execute)} steps", "info")
                for i, step in enumerate(steps_to_execute):
                    self.log_callback(f"  Step {i+1}: {step.name} (action: {step.action})", "info")
            
            # Execute each step in single thread
            for i, step in enumerate(steps_to_execute):
                if self.stop_requested:
                    break
                
                try:
                    self.current_step = i + 1
                    
                    # Update progress bar
                    progress = int((i / len(steps_to_execute)) * 100) if len(steps_to_execute) > 0 else 0
                    self._emit_signal_safe(self.progress_updated, progress, f"Iter {self.current_repeat}/{self.repeat_count} - Step {i+1}/{len(steps_to_execute)}: {step.name}")
                    
                    self.log_callback(f"Step {self.current_step}/{len(steps_to_execute)}: {step.name}", "info")
                    
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
                    
                    # Don't emit completion signal here, let repeat handler deal with it
                    self.log_callback(f"Step failed: {step.name}", "error")
                    return False
                
                # Wait for step duration with interruptible sleep
                if step.duration > 0:
                    self.log_callback(f"Waiting {step.duration}s for step completion", "info")
                    if not self._interruptible_sleep(step.duration):
                        self.log_callback("Step duration interrupted by stop request", "info")
                        break
            
            # Single iteration completed successfully
            if self.current_test:
                self.current_test.end_time = datetime.now()
            
            self.log_callback(f"Test iteration {self.current_repeat}/{self.repeat_count} completed", "info")
            
            # Return success (let repeat handler deal with completion)
            return True
            
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
            self.log_callback(f"Auto test status changed after error: {old_status.value} ? {self.status.value}", "info")
            
            # Emit failure signal after state reset
            self._emit_signal_safe(self.test_completed, False, f"Test failed: {e}")
        
        finally:
            # Ensure cleanup (redundant but safe)
            self.monitoring_active = False
            if self.status != TestStatus.IDLE:
                old_status = self.status
                self.status = TestStatus.IDLE
                self.log_callback(f"Final auto test state reset: {old_status.value} ? {self.status.value}", "info")

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
                    self.log_callback("WARNING: No enabled channels found, using defaults (ai0-ai5)", "warn")
                    enabled_channels = ['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5']
                    rail_names = {
                        'ai0': 'VDD_CORE', 'ai1': 'VDD_MEM', 'ai2': 'VDD_GPU',
                        'ai3': 'VDD_NPU', 'ai4': 'VDD_CAM', 'ai5': 'VDD_DISP'
                    }
                
                self.log_callback(f"Monitoring {len(enabled_channels)} channels in {measurement_mode} mode", "info")
            except Exception as e:
                self.log_callback(f"Error getting channel info: {e}, using defaults", "warn")
                enabled_channels = ['ai0', 'ai1']
                rail_names = {'ai0': 'Rail_A', 'ai1': 'Rail_B'}
                measurement_mode = 'current'
            
            # Start screen test with integrated DAQ monitoring
            test_duration = 20.0  # 20 seconds total
            data_interval = 0.001  # 1ms intervals (1000 samples per second)
            screen_interval = 2.0 # Screen changes every 2 seconds
            
            # Define actual test data collection period (exclude setup/teardown)
            test_data_start = 2.0  # Start collecting data after 2s setup
            test_data_end = 12.0   # Stop collecting data at 12s (10s of actual test data)
            
            self.log_callback("Starting screen on/off cycle with integrated DAQ monitoring", "info")
            self.log_callback(f"Test duration: {test_duration}s, Data collection: {test_data_start}s-{test_data_end}s", "info")
            
            # Start with screen on
            self.adb_service.turn_screen_on()
            
            start_time = time.time()
            last_screen_change = 0
            screen_state = True  # True = ON, False = OFF
            data_point_count = 0
            last_data_collection_time = -1  # Track last data collection time to prevent duplicates
            
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
                    # 1. Collect DAQ data ONLY during actual test period (exclude setup/teardown)
                    if test_data_start <= elapsed_time <= test_data_end:
                        # Calculate data point index relative to test start
                        test_elapsed = elapsed_time - test_data_start
                        target_data_time = int(test_elapsed)  # Integer seconds only (0, 1, 2, 3, ...)
                        
                        # Only collect if we haven't collected for this exact second yet
                        if target_data_time != last_data_collection_time and target_data_time < 10:
                            # Use exact integer time (0.0s, 1.0s, 2.0s, ..., 9.0s)
                            data_point = self._collect_daq_data_point(enabled_channels, measurement_mode, float(target_data_time))
                            if data_point:
                                self.daq_data.append(data_point)
                                data_point_count += 1
                                last_data_collection_time = target_data_time  # Update last collection time
                                self.log_callback(f"? Collected data point {data_point_count}: {target_data_time}.0s (elapsed: {elapsed_time:.1f}s)", "info")
                    
                    # 2. Screen control every 2 seconds (only during test period)
                    if test_data_start <= elapsed_time <= test_data_end:
                        # Calculate screen cycle relative to test start
                        test_elapsed = elapsed_time - test_data_start
                        screen_cycle_time = int(test_elapsed / screen_interval)
                        if screen_cycle_time > last_screen_change:
                            screen_state = not screen_state
                            if screen_state:
                                self.adb_service.turn_screen_on()
                                self.log_callback(f"Screen ON at test time {test_elapsed:.1f}s (total: {elapsed_time:.1f}s)", "info")
                            else:
                                self.adb_service.turn_screen_off()
                                self.log_callback(f"Screen OFF at test time {test_elapsed:.1f}s (total: {elapsed_time:.1f}s)", "info")
                            last_screen_change = screen_cycle_time
                    
                    # 3. Update progress (pure test progress only)
                    test_progress = int((elapsed_time / test_duration) * 100)
                    self._update_test_progress_only(test_progress, f"Screen Test: {elapsed_time:.1f}s / {test_duration}s")
                    
                    # 4. Sleep with stop check (no Qt events in worker thread)
                    time.sleep(0.2)  # Check every 0.2s for responsive UI but prevent over-sampling
                    
                except Exception as cycle_error:
                    self.log_callback(f"Error in test loop at {elapsed_time:.1f}s: {cycle_error}", "error")
                    time.sleep(0.1)
                    continue
            
            # Test completed - no final data collection (only test period data)
            self.monitoring_active = False
            data_count = len(self.daq_data)
            test_data_duration = test_data_end - test_data_start
            self.log_callback(f"Unified screen test completed. Collected {data_count} data points over {test_data_duration}s test period", "info")
            
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
            
            # Create data point with precise timing (ensure clean integer seconds)
            clean_time = round(elapsed_time, 1)  # Round to 1 decimal place
            data_point = {
                'timestamp': datetime.now(),
                'time_elapsed': clean_time,
                'screen_test_time': clean_time,
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
                    self._emit_signal_safe(self.test_completed, False, f"Test failed at step: {step.name}")
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
                self._emit_signal_safe(self.test_completed, True, "Test completed successfully")
            
        except Exception as e:
            self.status = TestStatus.FAILED
            if self.current_test:
                self.current_test.status = TestStatus.FAILED
                self.current_test.error_message = str(e)
            self.log_callback(f"Test execution error: {e}", "error")
            self._emit_signal_safe(self.test_completed, False, f"Test failed: {e}")
        
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
            elif step.action == "set_screen_timeout_10min":
                return self._step_set_screen_timeout_10min()
            elif step.action == "lcd_on_unlock_home_clear_apps":
                return self._step_lcd_on_unlock_home_clear_apps()
            elif step.action == "wait_current_stabilization":
                return self._step_wait_current_stabilization()
            elif step.action == "execute_phone_app_scenario":
                return self._step_execute_phone_app_scenario()
            elif step.action == "apply_default_settings":
                return self._step_apply_default_settings()
            elif step.action == "clear_all_recent_apps":
                return self._step_clear_all_recent_apps()
            elif step.action == "phone_app_test_with_daq":
                return self._step_phone_app_test_with_daq()
            elif step.action == "phone_app_test_only":
                return self._step_phone_app_test_only()
            elif step.action == "set_screen_timeout_10min":
                return self._step_set_screen_timeout_10min()
            elif step.action == "lcd_on_unlock_home_clear_apps":
                return self._step_lcd_on_unlock_home_clear_apps()
            elif step.action == "phone_app_scenario_test":
                return self._step_phone_app_scenario_test()
            elif step.action == "idle_wait_test":
                return self._step_idle_wait_test()
            elif step.action == "screen_onoff_test":
                return self._step_screen_onoff_test()
            elif step.action == "lcd_off":
                return self._step_lcd_off()
            elif step.action == "screen_on_app_clear_screen_off":
                return self._step_screen_on_app_clear_screen_off()
            elif step.action == "phone_app_test_with_daq_optimized":
                return self._step_phone_app_test_with_daq_optimized()
            elif step.action == "stop_daq_monitoring":
                return self._step_stop_daq_monitoring()
            elif step.action == "turn_screen_off":
                return self._step_turn_screen_off()
            elif step.action == "turn_screen_on":
                return self._step_turn_screen_on()
            elif step.action == "unlock_screen":
                return self._step_unlock_screen()
            elif step.action == "quick_reset_before_test":
                return self._step_quick_reset_before_test()
            elif step.action == "deviceidle_step":
                return self._step_deviceidle_step()
            elif step.action == "unlock_and_clear_apps":
                return self._step_unlock_and_clear_apps()
            elif step.action == "lcd_on_and_unlock":
                return self._step_lcd_on_and_unlock()
            elif step.action == "home_and_clear_apps_only":
                return self._step_home_and_clear_apps_only()
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
    
    def _step_turn_screen_off(self) -> bool:
        """Turn screen OFF"""
        try:
            self.log_callback("Turning screen OFF", "info")
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            success = self.adb_service.turn_screen_off()
            if success:
                self.log_callback("Screen OFF completed", "info")
                return True
            else:
                self.log_callback("Failed to turn screen off", "error")
                return False
        except Exception as e:
            self.log_callback(f"Error turning screen off: {e}", "error")
            return False
    
    def _step_turn_screen_on(self) -> bool:
        """Turn screen ON"""
        try:
            self.log_callback("Turning screen ON", "info")
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            success = self.adb_service.turn_screen_on()
            if success:
                self.log_callback("Screen ON completed", "info")
                return True
            else:
                self.log_callback("Failed to turn screen on", "error")
                return False
        except Exception as e:
            self.log_callback(f"Error turning screen on: {e}", "error")
            return False
    
    def _step_unlock_screen(self) -> bool:
        """Unlock screen"""
        try:
            self.log_callback("Unlocking screen", "info")
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            success = self.adb_service.unlock_screen()
            if success:
                self.log_callback("Screen unlocked", "info")
                return True
            else:
                self.log_callback("Failed to unlock screen", "error")
                return False
        except Exception as e:
            self.log_callback(f"Error unlocking screen: {e}", "error")
            return False
    
    def _step_deviceidle_step(self) -> bool:
        """Execute deviceidle step command for power optimization"""
        try:
            self.log_callback("=== Device Idle Optimization ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Execute: adb shell dumpsys deviceidle step
            self.log_callback("Running: adb shell dumpsys deviceidle step", "info")
            result = self.adb_service._run_adb_command(['shell', 'dumpsys', 'deviceidle', 'step'])
            
            if result is not None:
                self.log_callback("✅ Device idle step executed", "info")
                self.log_callback(f"Output: {result.strip()}", "info")
                return True
            else:
                self.log_callback("⚠️ Device idle step failed, continuing anyway", "warn")
                return True  # Continue even if command fails
                
        except Exception as e:
            self.log_callback(f"Error executing deviceidle step: {e}", "error")
            return True  # Don't fail test for this optimization step
    
    def _step_quick_reset_before_test(self) -> bool:
        """Quick reset between test iterations (clear apps + 10s stabilization)"""
        try:
            self.log_callback("=== Quick Reset for 2nd+ iteration ===", "info")
            self.log_callback("Sequence: Clear apps → 10s stabilization → Test start", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Step 1: Clear all recent apps
            self.log_callback("Step 1: Clearing all recent apps...", "info")
            success = self.adb_service.clear_recent_apps()
            
            if not success:
                self.log_callback("⚠️ Failed to clear apps, continuing anyway", "warn")
            else:
                self.log_callback("✅ Recent apps cleared", "info")
            
            # Step 2: Check if this is Screen On/Off scenario and turn screen off if needed
            is_screen_onoff = False
            if hasattr(self, 'current_test') and self.current_test:
                scenario_name = self.current_test.scenario_name.lower()
                if 'screen' in scenario_name and ('on' in scenario_name or 'off' in scenario_name):
                    is_screen_onoff = True
                    self.log_callback("🔍 Detected Screen On/Off scenario", "info")
            
            # For Screen On/Off scenario, turn screen off after clearing apps
            if is_screen_onoff:
                self.log_callback("Step 2: Turning screen OFF for Screen On/Off scenario...", "info")
                screen_off_success = self.adb_service.turn_screen_off()
                if not screen_off_success:
                    self.log_callback("⚠️ Failed to turn screen off, continuing anyway", "warn")
                else:
                    self.log_callback("✅ Screen turned OFF", "info")
            
            # Step 3: Wait 10 seconds for current stabilization
            self.log_callback(f"Step {3 if is_screen_onoff else 2}: Waiting 10 seconds for current stabilization...", "info")
            if not self._interruptible_sleep(10):
                return False
            
            self.log_callback("✅ Quick reset completed, starting test...", "info")
            return True
                
        except Exception as e:
            self.log_callback(f"Error in quick reset: {e}", "error")
            return True  # Don't fail test for quick reset issues
    
    def _step_wait_stabilization(self) -> bool:
        """Wait for current stabilization (duration handled by main loop)"""
        self.log_callback("Waiting for current stabilization...", "info")
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
            
            # Initialize screen test synchronization
            self._screen_test_started = threading.Event()
            self._screen_test_start_time = None
            
            # Get test duration from current scenario (default 10s for backward compatibility)
            test_duration = 10.0  # Default
            if hasattr(self, 'current_scenario') and self.current_scenario:
                scenario_config = self.scenarios.get(self.current_scenario)
                if scenario_config and hasattr(scenario_config, 'test_duration'):
                    test_duration = scenario_config.test_duration
                    self.log_callback(f"Using scenario test duration: {test_duration}s", "info")
            
            # Store test duration for DAQ monitoring thread
            self._test_duration = test_duration
            
            # Set a reasonable timeout (test duration + 15s buffer)
            self._monitoring_timeout = time.time() + test_duration + 15.0
            
            self.log_callback(f"DAQ monitoring initialized with {test_duration}s test duration", "info")
            
            # Check DAQ service connection
            if hasattr(self.daq_service, 'is_connected') and not self.daq_service.is_connected():
                self.log_callback("WARNING: DAQ service not connected, monitoring may not work", "warn")
            
            # Get enabled channels for monitoring
            enabled_channels = self._get_enabled_channels()
            self.log_callback(f"DAQ monitoring channels: {enabled_channels}", "info")
            
            if not enabled_channels:
                self.log_callback("WARNING: No enabled channels found, using default channels", "warn")
                enabled_channels = ['ai0', 'ai1']  # Default fallback
            
            # Store configuration for monitoring thread
            self._monitoring_channels = enabled_channels
            self._monitoring_mode = 'current'  # Default to current mode
            
            # Start monitoring in separate thread using hardware timing
            self.monitoring_thread = threading.Thread(target=self._daq_monitoring_hardware_timed)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            self.log_callback("DAQ hardware-timed monitoring thread started (1kHz)", "info")
            
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
                    self.log_callback("WARNING: No enabled channels found, using defaults (ai0-ai5)", "warn")
                    enabled_channels = ['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5']
                    rail_names = {
                        'ai0': 'VDD_CORE', 'ai1': 'VDD_MEM', 'ai2': 'VDD_GPU',
                        'ai3': 'VDD_NPU', 'ai4': 'VDD_CAM', 'ai5': 'VDD_DISP'
                    }
                
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
                # Calculate timeout based on test duration + buffer
                test_duration = 10.0  # Phone app test duration
                timeout_buffer = 15.0  # Reduced buffer time from 30s to 15s
                self._monitoring_timeout = time.time() + test_duration + timeout_buffer  # Dynamic timeout
                
                # Create thread for DAQ hardware-timed monitoring (1kHz, 10 seconds)
                monitoring_thread = threading.Thread(
                    target=self._daq_monitoring_hardware_timed,  # Use hardware timing
                    name="DAQ-HW-Timed-Thread"
                )
                monitoring_thread.daemon = True
                monitoring_thread.start()
                self.log_callback("DAQ hardware-timed monitoring started (1kHz, 10s)", "info")
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
                        self._emit_signal_safe(self.progress_updated, progress, f"Screen test cycle {i+1}/{cycles}")
                        
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
                self._emit_signal_safe(self.progress_updated, 90, "Screen test completed, preparing export")
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
    
    def _get_excel_filename_with_repeat(self, base_name: str = "test_results") -> str:
        """Generate CSV filename with repeat iteration number"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        repeat_suffix = f"_iter{self.current_repeat:02d}" if hasattr(self, 'current_repeat') and self.current_repeat > 0 else ""
        return f"{base_name}_{timestamp}{repeat_suffix}.csv"
    
    def _step_export_to_csv(self) -> bool:
        """Export DAQ data to Excel (with scenario-based filename)"""
        try:
            # Check if test was stopped - don't save if stopped
            if self.stop_requested or self.status == TestStatus.STOPPED:
                self.log_callback("Test was stopped - skipping data export", "info")
                return True
            
            # Always export at the end of each iteration
            if hasattr(self, 'repeat_count') and hasattr(self, 'current_repeat'):
                self.log_callback(f"Exporting data for iteration {self.current_repeat}/{self.repeat_count}", "info")
            
            self.log_callback("Starting Excel export...", "info")
            
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
            # Use scenario name for filename with iteration number
            scenario_name = self.current_test.scenario_name if self.current_test else "test"
            safe_name = scenario_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            
            # Add iteration number to filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            repeat_suffix = f"_iter{self.current_repeat:02d}" if hasattr(self, 'current_repeat') and self.current_repeat > 0 else ""
            csv_filename = f"{results_dir}/{safe_name}_{timestamp}{repeat_suffix}.csv"
            
            self.log_callback(f"Exporting to CSV file: {csv_filename}", "info")
            
            # Export to CSV (fast and lightweight, suitable for large datasets)
            csv_success = self._export_to_csv(csv_filename)
            
            if csv_success:
                self.log_callback(f"SUCCESS: Test data exported to {csv_filename}", "success")
            else:
                self.log_callback("FAILED: Could not export CSV data", "error")
            
            return csv_success
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
            sample_count = 0  # Track number of samples collected (0, 1, 2, 3, ...)
            data_collection_start_time = None  # Track when data collection actually starts
            # Use pre-stored configuration (thread-safe)
            enabled_channels = getattr(self, '_monitoring_channels', ['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5'])
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            if not enabled_channels:
                print("ERROR: No enabled channels found for monitoring!")
                return
            
            print(f"Monitoring {len(enabled_channels)} channels in {measurement_mode} mode: {enabled_channels}")
            print(f"Target: 10,000 samples over 10 seconds (Time: 0, 1, 2, 3, ... 9999 ms)")
            
            while self.monitoring_active and not self.stop_requested:
                try:
                    loop_count += 1
                    
                    # Read data from each enabled channel based on mode
                    channel_data = {}
                    successful_reads = 0
                    
                    if measurement_mode == "current":
                        # Current mode - try real DAQ first, then simulation
                        try:
                            # Try reading from real DAQ service
                            # New approach: 30kHz sampling with 30:1 compression
                            # - Sample at 30kHz (30,000 samples/second)
                            # - Read 30 samples per 1ms data point
                            # - Average 30 samples → 1 data point
                            # - Result: 1,000 data points/second (each = 30 samples average)
                            if self.daq_service and hasattr(self.daq_service, 'read_current_channels_direct'):
                                try:
                                    # Match manual measurement settings from NI Trace:
                                    # - SampQuant.SampPerChan = 1000
                                    # - SampClk.Rate = 30000
                                    # - SampClk.ActiveEdge = Rising
                                    # - SampClk.Src = "OnboardClock"
                                    result = self.daq_service.read_current_channels_direct(
                                        channels=enabled_channels,
                                        samples_per_channel=1000  # Match manual: 1000 samples per channel
                                    )
                                    
                                    if result:
                                        for channel in enabled_channels:
                                            if channel in result:
                                                channel_data_result = result[channel]
                                                # Get averaged current from multiple samples
                                                if 'current_data' in channel_data_result:
                                                    # Calculate average of all samples
                                                    current_samples = channel_data_result['current_data']
                                                    if current_samples:
                                                        avg_current = sum(current_samples) / len(current_samples)
                                                        channel_data[f"{channel}_current"] = avg_current
                                                        successful_reads += 1
                                                        if loop_count == 1:
                                                            print(f"Real DAQ current from {channel} (1000-sample avg, 30kHz): {avg_current}A")
                                                elif 'current' in channel_data_result:
                                                    channel_data[f"{channel}_current"] = channel_data_result['current']
                                                    successful_reads += 1
                                                    if loop_count == 1:
                                                        print(f"Real DAQ current from {channel}: {channel_data_result['current']}A")
                                except Exception as multi_read_err:
                                    print(f"Multi-channel read failed, trying individual reads: {multi_read_err}")
                                    # Fallback: Read each channel individually
                                    if self.daq_service and hasattr(self.daq_service, 'read_current'):
                                        for channel in enabled_channels:
                                            try:
                                                # Read 1000 samples to match manual measurement settings
                                                current = self._read_current_from_channel(channel, samples=1000)
                                                channel_data[f"{channel}_current"] = current
                                                successful_reads += 1
                                                if loop_count == 1:
                                                    print(f"Real DAQ current from {channel} (1000-sample avg, 30kHz): {current}A")
                                            except Exception as read_err:
                                                print(f"DAQ read error for {channel}: {read_err}, using fallback")
                                                # Fallback to simulation for this channel
                                                import random
                                                current = round(random.uniform(-0.05, 0.05), 6)
                                                channel_data[f"{channel}_current"] = current
                                                successful_reads += 1
                            elif self.daq_service and hasattr(self.daq_service, 'read_current'):
                                # Fallback: Single sample read if multi-sample not available
                                for channel in enabled_channels:
                                    try:
                                        current = self._read_current_from_channel(channel, samples=1)
                                        channel_data[f"{channel}_current"] = current
                                        successful_reads += 1
                                        if loop_count == 1:
                                            print(f"Real DAQ current from {channel}: {current}A")
                                    except Exception as read_err:
                                        print(f"DAQ read error for {channel}: {read_err}, using fallback")
                                        # Fallback to simulation for this channel
                                        import random
                                        current = round(random.uniform(-0.05, 0.05), 6)
                                        channel_data[f"{channel}_current"] = current
                                        successful_reads += 1
                            else:
                                # No real DAQ, use simulation
                                import random
                                for channel in enabled_channels:
                                    current = round(random.uniform(-0.05, 0.05), 6)  # Simulate microamp values
                                    channel_data[f"{channel}_current"] = current
                                    successful_reads += 1
                                    if loop_count == 1:
                                        print(f"Simulated current from {channel}: {current}A")
                        except Exception as e:
                            print(f"Error in current collection: {e}")
                            # Ensure all channels have data even on error
                            for channel in enabled_channels:
                                if f"{channel}_current" not in channel_data:
                                    channel_data[f"{channel}_current"] = 0.0
                                    print(f"?? WARNING: {channel}_current set to 0.0 due to error")
                    
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
                            screen_test_elapsed = 0  # Initialize with default value
                            if hasattr(self, '_screen_test_start_time') and self._screen_test_start_time is not None:
                                screen_test_elapsed = current_time - self._screen_test_start_time
                                
                                # Set data collection start time if not set
                                if data_collection_start_time is None:
                                    data_collection_start_time = current_time
                                    print(f"Data collection started at screen test time: {screen_test_elapsed:.1f}s")
                                
                                # Calculate actual elapsed time in ms (real-time based)
                                actual_elapsed_time = current_time - data_collection_start_time
                                actual_elapsed_ms = int(actual_elapsed_time * 1000)
                                
                                # Collect samples: only collect when actual time catches up with sample count
                                # This ensures exactly 1 sample per ms over 10 seconds
                                # sample_count starts at 0, so:
                                # - At 0ms: collect sample 0 (sample_count becomes 1)
                                # - At 1ms: collect sample 1 (sample_count becomes 2)
                                # - At 9999ms: collect sample 9999 (sample_count becomes 10000)
                                if sample_count <= actual_elapsed_ms < 10000:
                                    # Use sample count as time (ms): 0, 1, 2, 3, ..., 9999
                                    sample_time_ms = sample_count
                                    
                                    # Validate channel_data before adding
                                    if not channel_data:
                                        continue  # Skip empty data
                                    
                                    # Check if all values are 0 (suspicious) - warn occasionally
                                    if sample_count % 1000 == 0 and sample_count > 0:
                                        all_zero = all(v == 0.0 for v in channel_data.values() if isinstance(v, (int, float)))
                                        if all_zero:
                                            print(f"WARNING: All channel values are 0 at sample {sample_count}")
                                    
                                    # Convert current from A to mA (multiply by 1000)
                                    channel_data_mA = {}
                                    for key, value in channel_data.items():
                                        if '_current' in key:
                                            channel_data_mA[key] = value * 1000  # A ? mA
                                        else:
                                            channel_data_mA[key] = value
                                    
                                    data_point = {
                                        'timestamp': datetime.now(),
                                        'time_elapsed': sample_time_ms,  # Sequential: 0, 1, 2, 3, ..., 9999
                                        'screen_test_time': sample_time_ms,
                                        **channel_data_mA
                                    }
                                    
                                    # Thread-safe data append
                                    if hasattr(self, 'daq_data'):
                                        self.daq_data.append(data_point)
                                        sample_count += 1  # Increment sample counter
                                        
                                        # Log progress every 1000 samples
                                        if sample_count % 1000 == 0:
                                            # Show first 2 channels only in log (in mA)
                                            channel_preview = ', '.join([f"{k}={v:.3f}mA" for k, v in list(channel_data_mA.items())[:2]])
                                            elapsed_sec = actual_elapsed_time
                                            print(f"DAQ: {sample_count} samples at {sample_time_ms}ms (real: {elapsed_sec:.1f}s) [{channel_preview}...]")
                                elif actual_elapsed_ms >= 10000:
                                    # Stop collecting data after 10 seconds (10,000 ms)
                                    print(f"Data collection completed ({sample_count} samples collected over {actual_elapsed_time:.1f}s), stopping monitoring")
                                    self.monitoring_active = False
                                    break
                            else:
                                # Event is set but start time not available yet, wait a bit
                                continue
                        else:
                            # Screen test hasn't started yet, check timeout
                            if hasattr(self, '_monitoring_timeout') and current_time > self._monitoring_timeout:
                                timeout_duration = getattr(self, '_monitoring_timeout', current_time) - (current_time - 25)  # Calculate actual timeout duration
                                print(f"ERROR: Timeout waiting for screen test to start ({timeout_duration:.0f}s), stopping monitoring")
                                self.monitoring_active = False
                                break
                            
                            # Fallback: If we've been waiting too long (>10s), start collecting data anyway
                            if loop_count > 10:  # After 10 seconds of waiting
                                if data_collection_start_time is None:
                                    data_collection_start_time = current_time
                                    print("Fallback: Starting data collection without screen test signal")
                                
                                # Calculate sample-based time (starts at 0 and increments by 1ms)
                                current_sample_count = len(self.daq_data) if hasattr(self, 'daq_data') else 0
                                sample_time_ms = current_sample_count  # 0, 1, 2, 3, ... (in ms)
                                
                                if sample_time_ms < 10000:  # Only collect for 10 seconds (10,000ms)
                                    # Collect EVERY loop iteration (1ms interval = 10,000 samples in 10s)
                                    
                                    # Validate channel_data before adding
                                    if not channel_data:
                                        continue  # Skip empty data
                                    
                                    # Check if all values are 0 (suspicious) - warn occasionally
                                    if current_sample_count % 1000 == 0 and current_sample_count > 0:
                                        all_zero = all(v == 0.0 for v in channel_data.values() if isinstance(v, (int, float)))
                                        if all_zero:
                                            print(f"WARNING: All channel values are 0 at {sample_time_ms}ms (fallback)")
                                    
                                    # Convert current from A to mA (multiply by 1000)
                                    channel_data_mA = {}
                                    for key, value in channel_data.items():
                                        if '_current' in key:
                                            channel_data_mA[key] = value * 1000  # A ? mA
                                        else:
                                            channel_data_mA[key] = value
                                    
                                    data_point = {
                                        'timestamp': datetime.now(),
                                        'time_elapsed': sample_time_ms,  # Integer ms: 0, 1, 2, 3, ...
                                        'screen_test_time': sample_time_ms,  # Fallback timing
                                        **channel_data_mA
                                    }
                                    
                                    # Thread-safe data append
                                    if hasattr(self, 'daq_data'):
                                        self.daq_data.append(data_point)
                                        
                                        # Log progress every 1000 samples (=1 second)
                                        if len(self.daq_data) % 1000 == 0:
                                            # Show first 2 channels only in log (in mA)
                                            channel_preview = ', '.join([f"{k}={v:.3f}mA" for k, v in list(channel_data_mA.items())[:2]])
                                            print(f"Fallback: {len(self.daq_data)} samples, {sample_time_ms}ms [{channel_preview}...]")
                                else:
                                    # Stop fallback collection after 10 seconds (10,000 samples)
                                    print(f"Fallback data collection completed ({len(self.daq_data)} samples, {sample_time_ms}ms)")
                                    self.monitoring_active = False
                                    break
                            
                            # Wait for screen test to start
                            if loop_count % 10 == 1:  # Log every 10 seconds while waiting
                                timeout_time = getattr(self, '_monitoring_timeout', current_time + 25)  # Use dynamic timeout
                                remaining_time = max(0, timeout_time - current_time)
                                print(f"Waiting for screen test to start... ({remaining_time:.0f}s timeout remaining)")
                            
                            # Sleep before continue to avoid tight loop (longer wait for screen test)
                            time.sleep(1.0)  # Keep 1s for waiting state
                            continue
                        
                        # Log progress every 10 seconds
                        if loop_count % 10 == 0:
                            data_count = len(self.daq_data) if hasattr(self, 'daq_data') else 0
                            print(f"DAQ monitoring: {data_count} points collected, {successful_reads}/{len(enabled_channels)} channels OK")
                            
                    except Exception as e:
                        print(f"Error creating data point: {e}")
                    
                    # Small sleep to prevent excessive CPU usage while waiting for next ms
                    # Loop runs fast to check for each ms boundary
                    time.sleep(0.0001)  # 0.1ms sleep to reduce CPU load
                        
                except Exception as loop_error:
                    # Log loop error but continue monitoring
                    print(f"Error in monitoring loop iteration {loop_count}: {loop_error}")
                    time.sleep(0.001)  # Wait before retry
                    
        except Exception as e:
            print(f"Critical error in DAQ monitoring loop: {e}")
        finally:
            self.monitoring_active = False
            print("DAQ monitoring loop ended")
    
    def _daq_monitoring_hardware_timed(self):
        """DAQ monitoring using hardware timing (1kHz, 10,000 samples)"""
        print("=== DAQ Hardware-Timed Collection Started ===")
        
        try:
            # Wait for screen test to start
            print("Waiting for screen test to start...")
            if hasattr(self, '_screen_test_started'):
                wait_success = self._screen_test_started.wait(timeout=25.0)
                if not wait_success:
                    print("ERROR: Screen test start timeout (25s)")
                    self.monitoring_active = False
                    return
            
            # Get enabled channels
            enabled_channels = getattr(self, '_monitoring_channels', ['ai0', 'ai1'])
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            print(f"Collecting from {len(enabled_channels)} channels: {enabled_channels}")
            print(f"Mode: {measurement_mode}")
            
            # Get test duration from engine (configured per scenario)
            test_duration = getattr(self, '_test_duration', 10.0)
            expected_samples = int(test_duration * 1000)  # 1ms intervals
            
            # Use DAQ hardware timing: 1kHz for specified duration
            # Use CURRENT measurement mode (same as Multi-Channel Monitor)
            if hasattr(self, 'daq_service') and self.daq_service:
                print(f"Starting DAQ hardware-timed CURRENT collection (1ms interval, 30 samples avg, {test_duration} seconds)...")
                print(f"Expected samples: {expected_samples} (0 to {expected_samples-1} ms)")

                daq_result = self.daq_service.read_current_channels_hardware_timed(
                    channels=enabled_channels,
                    sample_rate=30000.0,  # 30kHz (30 samples per ms)
                    compress_ratio=30,  # 30:1 compression (average 30 samples → 1 per ms)
                    duration_seconds=test_duration  # Duration from scenario config
                )
                
                if daq_result:
                    print(f"DAQ collection completed: {len(daq_result)} channels")
                    
                    # Convert to daq_data format
                    if hasattr(self, 'daq_data'):
                        self.daq_data = []
                        
                        # Get sample count (depends on test duration: 10s=10000, 20s=20000, etc.)
                        first_channel = list(daq_result.keys())[0]
                        sample_count = daq_result[first_channel]['sample_count']
                        
                        print(f"Processing {sample_count} samples (0 to {sample_count-1} ms)...")
                        
                        # Create data points for each sample
                        for i in range(sample_count):
                            data_point = {
                                'timestamp': datetime.now(),
                                'time_elapsed': i,  # Time in ms: 0, 1, 2, ..., (sample_count-1)
                                'screen_test_time': i
                            }
                            
                            # Add current data for each channel (already in mA from DAQ)
                            for channel in enabled_channels:
                                if channel in daq_result:
                                    current_mA = daq_result[channel]['current_data'][i]
                                    data_point[f'{channel}_current'] = current_mA  # Current in mA
                            
                            self.daq_data.append(data_point)
                            
                            # Log progress every 1000 samples
                            if (i + 1) % 1000 == 0:
                                print(f"Processed {i + 1}/{sample_count} samples")
                        
                        print(f"? Successfully processed {len(self.daq_data)} data points")
                    else:
                        print("ERROR: daq_data attribute not found")
                else:
                    print("ERROR: DAQ collection returned no data")
            else:
                print("ERROR: DAQ service not available, using simulation")
                # Fallback to simulation
                self._daq_monitoring_loop_isolated_simulation()
                
        except Exception as e:
            print(f"ERROR in hardware-timed DAQ collection: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.monitoring_active = False
            print("=== DAQ Hardware-Timed Collection Ended ===")
    
    def _daq_monitoring_loop_isolated_simulation(self):
        """Simulation fallback for when DAQ hardware is not available"""
        print("Using simulation mode for DAQ collection")
        import random
        
        enabled_channels = getattr(self, '_monitoring_channels', ['ai0', 'ai1'])
        test_duration = getattr(self, '_test_duration', 10.0)
        expected_samples = int(test_duration * 1000)
        
        print(f"Simulating {expected_samples} samples for {test_duration}s test")
        
        if hasattr(self, 'daq_data'):
            self.daq_data = []
            for i in range(expected_samples):
                data_point = {
                    'timestamp': datetime.now(),
                    'time_elapsed': i,
                    'screen_test_time': i
                }
                for channel in enabled_channels:
                    data_point[f'{channel}_current'] = random.uniform(-50, 50)  # mA
                self.daq_data.append(data_point)
                
                if (i + 1) % 1000 == 0:
                    print(f"Simulation: {i + 1}/10000 samples")
    
    def _daq_monitoring_loop_isolated(self):
        """Completely isolated DAQ monitoring loop - no Qt dependencies"""
        print("Isolated DAQ monitoring loop started")
        
        try:
            # Completely isolate from Qt
            import threading
            current_thread = threading.current_thread()
            current_thread.name = "DAQ-Isolated"
            
            loop_count = 0
            data_collection_start_time = None  # Track when data collection actually starts
            enabled_channels = getattr(self, '_monitoring_channels', ['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5'])
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
                            
                            # Set data collection start time if not set
                            if data_collection_start_time is None:
                                data_collection_start_time = current_time
                                print(f"Isolated: Data collection started at screen test time: {screen_test_elapsed:.1f}s")
                            
                            # Calculate data collection elapsed time (always starts from 0)
                            data_elapsed_time = current_time - data_collection_start_time
                            
                            # Only collect data during test period (0-10 seconds for Phone app test)
                            if screen_test_elapsed >= 0 and screen_test_elapsed <= 10.0 and data_elapsed_time <= 10.0:
                                data_point = {
                                    'timestamp': datetime.now(),
                                    'time_elapsed': round(data_elapsed_time, 1),  # Time from data collection start (0-10s)
                                    'screen_test_time': round(data_elapsed_time, 1),  # Same as elapsed time
                                    **channel_data
                                }
                                
                                # Thread-safe data append
                                if hasattr(self, 'daq_data'):
                                    self.daq_data.append(data_point)
                                    
                                # Log progress every 10 data points
                                if len(self.daq_data) % 10 == 1:
                                    print(f"Isolated: Data collection: {len(self.daq_data)} points, time: {data_elapsed_time:.1f}s")
                            elif data_elapsed_time > 10.0:
                                print(f"Isolated: Data collection completed ({data_elapsed_time:.1f}s), stopping")
                                self.monitoring_active = False
                                break
                        else:
                            continue
                    else:
                        # Check timeout
                        if hasattr(self, '_monitoring_timeout') and current_time > self._monitoring_timeout:
                            timeout_duration = getattr(self, '_monitoring_timeout', current_time) - (current_time - 25)  # Calculate actual timeout duration
                            print(f"Isolated: ERROR - Timeout waiting for screen test ({timeout_duration:.0f}s)")
                            self.monitoring_active = False
                            break
                        
                        # Wait message (less frequent)
                        if loop_count % 10 == 1:
                            timeout_time = getattr(self, '_monitoring_timeout', current_time + 25)  # Use dynamic timeout
                            remaining = max(0, timeout_time - current_time)
                            print(f"Isolated: Waiting for screen test... ({remaining:.0f}s remaining)")
                        
                        # Sleep before continue to avoid tight loop (longer wait for screen test)
                        time.sleep(1.0)  # Keep 1s for waiting state
                        continue
                    
                    # Progress logging
                    if loop_count % 10 == 0:
                        data_count = len(self.daq_data) if hasattr(self, 'daq_data') else 0
                        print(f"Isolated DAQ: {data_count} points, {successful_reads}/{len(enabled_channels)} channels OK")
                    
                    # Sleep
                    time.sleep(0.001)  # 1ms interval
                    
                except Exception as loop_error:
                    print(f"Isolated DAQ loop error: {loop_error}")
                    time.sleep(0.001)  # 1ms interval
                    
        except Exception as e:
            print(f"Isolated DAQ critical error: {e}")
        finally:
            self.monitoring_active = False
            print("Isolated DAQ monitoring loop ended")
    
    def _get_enabled_channels(self) -> List[str]:
        """Get list of enabled channels from multi-channel monitor"""
        return self._get_enabled_channels_from_monitor()
    
    def _calculate_robust_statistics(self, values: List[float], 
                                     exclude_stabilization: bool = True,
                                     stabilization_seconds: float = 1.0,
                                     remove_outliers: bool = True,
                                     outlier_method: str = 'iqr') -> Dict[str, Any]:
        """
        Calculate robust statistics with outlier removal and stabilization period exclusion
        
        Args:
            values: List of values to analyze
            exclude_stabilization: Whether to exclude initial stabilization period
            stabilization_seconds: Duration of stabilization period in seconds (assuming 1ms sampling)
            remove_outliers: Whether to remove outliers
            outlier_method: Method for outlier detection ('iqr' or 'zscore')
        
        Returns:
            Dictionary with statistics: avg, median, min, max, std, count, filtered_count
        """
        if not values:
            return {
                'avg': 0.0, 'median': 0.0, 'min': 0.0, 'max': 0.0,
                'std': 0.0, 'count': 0, 'filtered_count': 0
            }
        
        # Convert to numpy array for easier processing
        import numpy as np
        values_array = np.array(values)
        
        # Step 1: Exclude stabilization period (first N samples)
        if exclude_stabilization and len(values_array) > 0:
            # Assuming 1ms sampling rate (1000 samples per second)
            stabilization_samples = int(stabilization_seconds * 1000)
            if stabilization_samples < len(values_array):
                values_array = values_array[stabilization_samples:]
                self.log_callback(f"Excluded {stabilization_samples} stabilization samples", "info")
        
        if len(values_array) == 0:
            return {
                'avg': 0.0, 'median': 0.0, 'min': 0.0, 'max': 0.0,
                'std': 0.0, 'count': len(values), 'filtered_count': 0
            }
        
        # Step 2: Remove outliers
        filtered_values = values_array.copy()
        original_count = len(filtered_values)
        
        if remove_outliers and len(filtered_values) > 10:  # Need enough samples for outlier detection
            if outlier_method == 'iqr':
                # IQR (Interquartile Range) method
                Q1 = np.percentile(filtered_values, 25)
                Q3 = np.percentile(filtered_values, 75)
                IQR = Q3 - Q1
                
                # Define outlier bounds (1.5 * IQR is standard)
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # Filter outliers
                mask = (filtered_values >= lower_bound) & (filtered_values <= upper_bound)
                filtered_values = filtered_values[mask]
                
                outlier_count = original_count - len(filtered_values)
                if outlier_count > 0:
                    self.log_callback(f"Removed {outlier_count} outliers using IQR method (bounds: {lower_bound:.3f} to {upper_bound:.3f})", "info")
            
            elif outlier_method == 'zscore':
                # Z-score method (values beyond 3 standard deviations)
                mean = np.mean(filtered_values)
                std = np.std(filtered_values)
                
                if std > 0:
                    z_scores = np.abs((filtered_values - mean) / std)
                    mask = z_scores < 3.0
                    filtered_values = filtered_values[mask]
                    
                    outlier_count = original_count - len(filtered_values)
                    if outlier_count > 0:
                        self.log_callback(f"Removed {outlier_count} outliers using Z-score method", "info")
        
        # Step 3: Calculate statistics on filtered data
        if len(filtered_values) > 0:
            avg = float(np.mean(filtered_values))
            median = float(np.median(filtered_values))
            min_val = float(np.min(filtered_values))
            max_val = float(np.max(filtered_values))
            std = float(np.std(filtered_values))
        else:
            # Fallback to original values if all filtered out
            avg = float(np.mean(values_array))
            median = float(np.median(values_array))
            min_val = float(np.min(values_array))
            max_val = float(np.max(values_array))
            std = float(np.std(values_array))
            filtered_values = values_array
        
        return {
            'avg': avg,
            'median': median,
            'min': min_val,
            'max': max_val,
            'std': std,
            'count': original_count,
            'filtered_count': len(filtered_values)
        }
    
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
                    new_key = f"{rail_name}_Current(mA)"  # Changed to mA
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
                    new_key = f"{rail_name}_Current(mA)"  # Changed to mA
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
                if not threading.current_thread().daemon:
                    self._emit_signal_safe(self.progress_updated, progress, step_name)
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
            if not threading.current_thread().daemon:
                self._emit_signal_safe(self.progress_updated, test_progress, f"Screen Test: {test_progress}%")
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
            
            self._emit_signal_safe(self.progress_updated, progress, step_name)
    
    def _read_current_from_channel(self, channel: str, samples: int = 1000) -> float:
        """Read current from a specific DAQ channel with averaging
        
        Args:
            channel: Channel name (e.g., 'ai0', 'ai1')
            samples: Number of samples to average (default: 1000 to match manual measurement)
                     
                     Matches manual measurement settings from NI Trace:
                     - SampQuant.SampPerChan = 1000
                     - SampClk.Rate = 30000
                     - SampClk.ActiveEdge = Rising
                     - SampClk.Src = "OnboardClock"
                     
                     - Sampling rate: 30kHz = 30,000 samples/second
                     - 1000 samples = 1000 / 30,000 = ~33ms
                     - Each data point = average of 1000 samples
                     - Provides excellent noise reduction and accuracy
            
        Returns:
            Averaged current value in Amps (will be converted to mA later)
        """
        try:
            if not self.daq_service:
                raise Exception("DAQ service not available")
            
            # If samples > 1, use multi-sample averaging for better accuracy
            if samples > 1 and hasattr(self.daq_service, 'read_current_channels_direct'):
                try:
                    # Read multiple samples quickly and average
                    result = self.daq_service.read_current_channels_direct(
                        channels=[channel],
                        samples_per_channel=samples
                    )
                    
                    if result and channel in result:
                        channel_data = result[channel]
                        # Get all samples and calculate average
                        if 'current_data' in channel_data:
                            current_samples = channel_data['current_data']
                            if current_samples:
                                # Calculate average of all samples
                                avg_current = sum(current_samples) / len(current_samples)
                                return avg_current
                        elif 'current' in channel_data:
                            return channel_data['current']
                except Exception as e:
                    # Fallback to single sample if multi-sample fails
                    print(f"Multi-sample read failed for {channel}, using single sample: {e}")
            
            # Fallback: Use single sample read
            readings = self.daq_service.read_single_shot()
            
            if not readings or channel not in readings:
                raise Exception(f"No reading available for channel {channel}")
            
            # Get current value from readings (in Amps)
            channel_reading = readings[channel]
            current = channel_reading.get('current', 0.0)
            
            return current
            
        except Exception as e:
            # Log error and raise to trigger fallback in calling code
            print(f"Error reading current from {channel}: {e}")
            raise
    
    def _get_enabled_channels_from_monitor(self) -> List[str]:
        """Get enabled channels from multi-channel monitor (ONLY enabled channels, no fallback)"""
        if not self.multi_channel_monitor:
            self.log_callback("?? No multi-channel monitor available", "warn")
            return []
        
        try:
            enabled_channels = []
            for channel, config in self.multi_channel_monitor.channel_configs.items():
                if config.get('enabled', False):
                    enabled_channels.append(channel)
                    self.log_callback(f"? Found enabled channel: {channel} -> {config.get('name', 'Unknown')}", "info")
            
            if not enabled_channels:
                self.log_callback("?? No channels enabled in multi-channel monitor", "warn")
                return []
            
            self.log_callback(f"?? Total enabled channels from monitor: {enabled_channels}", "info")
            return enabled_channels
        except Exception as e:
            self.log_callback(f"? Error getting enabled channels: {e}", "error")
            return []
    
    def _get_channel_rail_names(self) -> Dict[str, str]:
        """Get rail names for enabled channels"""
        if not self.multi_channel_monitor:
            return {
                'ai0': 'VDD_CORE', 'ai1': 'VDD_MEM', 'ai2': 'VDD_GPU',
                'ai3': 'VDD_NPU', 'ai4': 'VDD_CAM', 'ai5': 'VDD_DISP'
            }
        
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
                return {
                'ai0': 'VDD_CORE', 'ai1': 'VDD_MEM', 'ai2': 'VDD_GPU',
                'ai3': 'VDD_NPU', 'ai4': 'VDD_CAM', 'ai5': 'VDD_DISP'
            }
                
            return rail_names
        except Exception as e:
            self.log_callback(f"Error getting rail names: {e}", "error")
            return {
                'ai0': 'VDD_CORE', 'ai1': 'VDD_MEM', 'ai2': 'VDD_GPU',
                'ai3': 'VDD_NPU', 'ai4': 'VDD_CAM', 'ai5': 'VDD_DISP'
            }
    
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
                    unit = "mA"  # Changed to milliAmperes
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
                        # Calculate robust statistics with outlier removal and stabilization exclusion
                        stats = self._calculate_robust_statistics(
                            values,
                            exclude_stabilization=True,
                            stabilization_seconds=1.0,  # Exclude first 1 second
                            remove_outliers=True,
                            outlier_method='iqr'
                        )
                        
                        # Write statistics
                        summary_sheet.write(f'A{row}', '  Average (filtered):', label_format)
                        summary_sheet.write(f'B{row}', f"{stats['avg']:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Median:', label_format)
                        summary_sheet.write(f'B{row}', f"{stats['median']:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Minimum:', label_format)
                        summary_sheet.write(f'B{row}', f"{stats['min']:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Maximum:', label_format)
                        summary_sheet.write(f'B{row}', f"{stats['max']:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Range:', label_format)
                        summary_sheet.write(f'B{row}', f"{stats['max'] - stats['min']:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Std Dev:', label_format)
                        summary_sheet.write(f'B{row}', f"{stats['std']:.3f} {unit}")
                        row += 1
                        
                        summary_sheet.write(f'A{row}', '  Samples:', label_format)
                        summary_sheet.write(f'B{row}', f"{stats['filtered_count']}/{stats['count']}")
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
    
    def _export_to_csv(self, filename: str) -> bool:
        """Export data to CSV file (lightweight and fast)"""
        try:
            import pandas as pd
            import csv
            
            if not self.daq_data:
                self.log_callback("No data to export", "warn")
                return True
            
            # Get enabled channels, rail names, and measurement mode
            enabled_channels = self._get_enabled_channels_from_monitor()
            rail_names = self._get_channel_rail_names()
            measurement_mode = getattr(self, '_monitoring_mode', 'current')
            
            self.log_callback(f"CSV export - Enabled channels: {enabled_channels}", "info")
            self.log_callback(f"CSV export - Rail names: {rail_names}", "info")
            self.log_callback(f"CSV export - Measurement mode: {measurement_mode}", "info")
            
            # Create formatted data
            formatted_data = {}
            
            # First column: Time in ms as INTEGER (0, 1, 2, 3, ...)
            formatted_data['Time (ms)'] = []
            for data_point in self.daq_data:
                time_ms = data_point.get('time_elapsed', 0)
                formatted_data['Time (ms)'].append(int(time_ms))
            
            # Additional columns: Rail data based on measurement mode
            for channel in enabled_channels:
                rail_name = rail_names.get(channel, f"Rail_{channel}")
                
                if measurement_mode == "current":
                    column_name = f"{rail_name} (mA)"  # Current in milliAmperes
                    data_key = f"{channel}_current"
                else:
                    column_name = f"{rail_name} (V)"  # Voltage in Volts
                    data_key = f"{channel}_voltage"
                
                formatted_data[column_name] = []
                
                for data_point in self.daq_data:
                    value = data_point.get(data_key, 0.0)
                    formatted_data[column_name].append(value)
            
            # Create DataFrame
            df = pd.DataFrame(formatted_data)
            
            # Export to CSV (fast and lightweight)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            # Log summary info
            file_size_mb = os.path.getsize(filename) / (1024 * 1024)
            self.log_callback(f"CSV export completed: {filename}", "info")
            self.log_callback(f"  - Data points: {len(self.daq_data)}", "info")
            self.log_callback(f"  - Channels: {len(enabled_channels)}", "info")
            self.log_callback(f"  - File size: {file_size_mb:.2f} MB", "info")
            
            return True
            
        except Exception as e:
            self.log_callback(f"Error exporting to CSV: {e}", "error")
            import traceback
            self.log_callback(f"CSV export traceback: {traceback.format_exc()}", "error")
            return False
    
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
            
            # First column: Time in ms as INTEGER (0, 1, 2, 3, ...)
            formatted_data['Time (ms)'] = []
            for data_point in self.daq_data:
                # Use time_elapsed which is already in ms (integer)
                time_ms = data_point.get('time_elapsed', 0)
                formatted_data['Time (ms)'].append(int(time_ms))  # Store as integer ms
            
            # Additional columns: Rail data (current in mA)
            for channel in enabled_channels:
                rail_name = rail_names.get(channel, f"Rail_{channel}")
                
                # Output as Current (mA) - converted from shunt voltage
                column_name = f"{rail_name} (mA)"  # Current in milliAmperes
                data_key = f"{channel}_current"
                
                formatted_data[column_name] = []
                
                for data_point in self.daq_data:
                    value = data_point.get(data_key, 0.0)
                    # Value is already in mA from DAQ conversion
                    formatted_data[column_name].append(value)
            
            # Create DataFrame with custom format
            df = pd.DataFrame(formatted_data)
            
            # Export to Excel with xlsxwriter (includes Summary sheet)
            if not XLSXWRITER_AVAILABLE:
                self.log_callback("xlsxwriter not available, using simple export", "warn")
                df.to_excel(filename, sheet_name='Test_Results', index=False, engine='openpyxl')
                self.log_callback(f"Excel export completed (simple): {filename}", "info")
                return True
            
            # Use xlsxwriter for proper formatting and Summary sheet
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                # Write main data
                df.to_excel(writer, sheet_name='Test_Results', index=False)
                
                # Get workbook and worksheet for formatting
                workbook = writer.book
                worksheet = writer.sheets['Test_Results']
                
                # Format columns
                time_format = workbook.add_format({'num_format': '0.0'})
                value_format = workbook.add_format({'num_format': '0.000'})
                
                worksheet.set_column('A:A', 12, time_format)   # Time column
                worksheet.set_column('B:Z', 15, value_format)  # Value columns
                
                # Create Summary sheet with simple data (no complex structures)
                summary_data = {
                    'Metric': [
                        'Test Name',
                        'Start Time', 
                        'Data Points',
                        'Duration (s)',
                        ''  # Empty row separator
                    ],
                    'Value': [
                        str(self.current_test.scenario_name) if self.current_test else 'Unknown',
                        str(self.current_test.start_time.strftime('%Y-%m-%d %H:%M:%S')) if self.current_test else 'Unknown',
                        int(len(self.daq_data)),
                        int(len(self.daq_data)),
                        ''  # Empty row separator
                    ]
                }
                
                # Add rail statistics with separation
                for i, channel in enumerate(enabled_channels):
                    rail_name = rail_names.get(channel, f"Rail_{channel}")
                    
                    if measurement_mode == "current":
                        channel_key = f'{channel}_current'
                        unit = "mA"  # Changed to milliAmperes
                    else:
                        channel_key = f'{channel}_voltage'
                        unit = "V"
                    
                    column_name = f"{rail_name} ({unit})"
                    if column_name in formatted_data:
                        values = [v for v in formatted_data[column_name] if isinstance(v, (int, float))]
                        
                        if values:
                            # Calculate robust statistics with outlier removal and stabilization exclusion
                            stats = self._calculate_robust_statistics(
                                values,
                                exclude_stabilization=True,
                                stabilization_seconds=1.0,  # Exclude first 1 second
                                remove_outliers=True,
                                outlier_method='iqr'
                            )
                            
                            # Add rail header
                            summary_data['Metric'].append(f'[{rail_name}]')
                            summary_data['Value'].append('')
                            
                            # Add statistics
                            summary_data['Metric'].extend([
                                f'  Average (filtered) ({unit})',
                                f'  Median ({unit})',
                                f'  Minimum ({unit})',
                                f'  Maximum ({unit})',
                                f'  Range ({unit})',
                                f'  Std Dev ({unit})',
                                f'  Samples (filtered/total)'
                            ])
                            summary_data['Value'].extend([
                                float(f'{stats["avg"]:.6f}'),
                                float(f'{stats["median"]:.6f}'),
                                float(f'{stats["min"]:.6f}'),
                                float(f'{stats["max"]:.6f}'),
                                float(f'{stats["max"] - stats["min"]:.6f}'),
                                float(f'{stats["std"]:.6f}'),
                                f"{stats['filtered_count']}/{stats['count']}"
                            ])
                            
                            # Add separator between rails
                            summary_data['Metric'].append('')
                            summary_data['Value'].append('')
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Test_Summary', index=False)
                
                # Format summary sheet
                summary_sheet = writer.sheets['Test_Summary']
                summary_sheet.set_column('A:A', 35)
                
                # Format Value column with proper number format
                num_format = workbook.add_format({'num_format': '0.000000'})
                summary_sheet.set_column('B:B', 20, num_format)
            
            self.log_callback(f"Excel export completed with Summary: {filename}", "info")
            self.log_callback(f"Excel structure: Test_Results + Test_Summary sheets", "info")
            return True
        except Exception as e:
            self.log_callback(f"Error exporting to Excel (basic): {e}", "error")
            # Fallback to CSV if Excel fails
            csv_filename = filename.replace('.xlsx', '.csv')
            return self._export_to_csv_fallback(csv_filename)
    
    def _step_connect_wifi_2g(self) -> bool:
        """Connect to 2.4GHz WiFi network"""
        try:
            # ?? WiFi ?? ??
            wifi_ssid = "0_WIFIFW_RAX40_2nd_2G"  # ?? 2G WiFi ??
            wifi_password = "cppower12"  # ?? WiFi ????
            
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
                self.log_callback("? _step_start_daq_monitoring method exists", "info")
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
                self.log_callback("? _step_start_daq_monitoring method does not exist", "error")
                return False
            
            # Wait a moment for DAQ to stabilize
            if not self._interruptible_sleep(1):
                return False
            
            # Initialize screen test timing for DAQ data collection
            test_start_time = time.time()
            self._screen_test_start_time = test_start_time
            
            # Signal DAQ monitoring that test has started
            if hasattr(self, '_screen_test_started'):
                self._screen_test_started.set()
                self.log_callback("? Phone app test start signal sent to DAQ monitoring", "info")
            else:
                self.log_callback("?? Warning: _screen_test_started event not found", "warn")
            
            # Execute Phone app test sequence
            self.log_callback("=== Phone App Test Sequence Started ===", "info")
            
            # 0?: LCD ON ? Phone app ??
            self.log_callback("Step 1: Turn on LCD and open Phone app", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
            
            if not self._interruptible_sleep(0.5):
                self._step_stop_daq_monitoring()
                return False
            
            if not self.adb_service.open_phone_app():
                self.log_callback("Failed to open Phone app", "error")
            
            # 5? ??
            self.log_callback("Waiting 5 seconds in Phone app...", "info")
            if not self._interruptible_sleep(5):
                self.log_callback("Phone app wait interrupted", "info")
                self._step_stop_daq_monitoring()
                return False
            
            # 5?: Back key ??? ? ???? ??
            self.log_callback("Step 2: Press back key to go to home screen", "info")
            if not self.adb_service.press_back_key():
                self.log_callback("Failed to press back key", "error")
            
            if not self._interruptible_sleep(0.5):
                self._step_stop_daq_monitoring()
                return False
            
            # ? ???? ??? ??
            if not self.adb_service.press_home_key():
                self.log_callback("Failed to press home key", "error")
            
            # 5? ? ?? (? 10?)
            self.log_callback("Waiting 5 more seconds on home screen...", "info")
            if not self._interruptible_sleep(5):
                self.log_callback("Home screen wait interrupted", "info")
                self._step_stop_daq_monitoring()
                return False
            
            self.log_callback("=== Phone App Test Sequence Completed ===", "info")
            
            # Stop DAQ monitoring
            self.log_callback("Stopping DAQ monitoring", "info")
            self._step_stop_daq_monitoring()
            
            # Wait for DAQ to finish
            if not self._interruptible_sleep(2):
                return False
            
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
    
    def _step_phone_app_test_only(self) -> bool:
        """Execute Phone app test without DAQ setup (DAQ already running)"""
        try:
            self.log_callback("Starting Phone app test (DAQ already monitoring)", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Initialize screen test timing for DAQ data collection
            test_start_time = time.time()
            self._screen_test_start_time = test_start_time
            
            # Signal DAQ monitoring that test has started
            if hasattr(self, '_screen_test_started'):
                self._screen_test_started.set()
                self.log_callback("? Phone app test start signal sent to DAQ monitoring", "info")
            else:
                self.log_callback("?? Warning: _screen_test_started event not found", "warn")
            
            # Execute Phone app test sequence
            self.log_callback("=== Phone App Test Sequence Started ===", "info")
            
            # 0?: LCD ON ? Phone app ??
            self.log_callback("Step 1: Turn on LCD and open Phone app", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
            
            if not self._interruptible_sleep(0.5):
                return False
            
            if not self.adb_service.open_phone_app():
                self.log_callback("Failed to open Phone app", "error")
            
            # 5? ??
            self.log_callback("Waiting 5 seconds in Phone app...", "info")
            if not self._interruptible_sleep(5):
                self.log_callback("Phone app wait interrupted", "info")
                return False
            
            # 5?: Back key ??? ? ???? ??
            self.log_callback("Step 2: Press back key to go to home screen", "info")
            if not self.adb_service.press_back_key():
                self.log_callback("Failed to press back key", "error")
            
            if not self._interruptible_sleep(0.5):
                return False
            
            # ? ???? ??? ??
            if not self.adb_service.press_home_key():
                self.log_callback("Failed to press home key", "error")
            
            # 5? ? ?? (? 10?)
            self.log_callback("Waiting 5 more seconds on home screen...", "info")
            if not self._interruptible_sleep(5):
                self.log_callback("Home screen wait interrupted", "info")
                return False
            
            self.log_callback("=== Phone App Test Sequence Completed ===", "info")
            
            # Wait for DAQ to finish collecting data
            if not self._interruptible_sleep(2):
                return False
            
            self.log_callback("Phone app test completed (DAQ still running)", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in Phone app test: {e}", "error")
            return False
    
    def _step_screen_on_app_clear_screen_off(self) -> bool:
        """Screen on -> Home -> Clear all apps -> Screen off"""
        try:
            self.log_callback("=== Init Mode: Screen On + App Clear + Screen Off ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # 1. Screen ON
            self.log_callback("Step 1: Turn screen ON", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 2. Press Home button
            self.log_callback("Step 2: Press Home button", "info")
            if not self.adb_service.press_home_key():
                self.log_callback("Failed to press home key", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 3. Clear all recent apps
            self.log_callback("Step 3: Clear all recent apps", "info")
            if not self.adb_service.clear_recent_apps():
                self.log_callback("Failed to clear recent apps", "error")
            if not self._interruptible_sleep(2):
                return False
            
            # 4. Screen OFF
            self.log_callback("Step 4: Turn screen OFF", "info")
            if not self.adb_service.turn_screen_off():
                self.log_callback("Failed to turn screen off", "error")
            if not self._interruptible_sleep(1):
                return False
            
            self.log_callback("Init mode screen/app setup completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in screen/app setup: {e}", "error")
            return False
    
    def _step_phone_app_test_with_daq_optimized(self) -> bool:
        """Optimized: Screen ON -> DAQ Start -> Phone App Test -> DAQ Stop"""
        try:
            self.log_callback("=== Optimized Phone App Test with DAQ ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # 7. Screen ON (after stabilization)
            self.log_callback("Step 7: Turn screen ON (post-stabilization)", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # Start DAQ monitoring
            self.log_callback("Step 7.1: Starting DAQ monitoring", "info")
            if not self._step_start_daq_monitoring():
                self.log_callback("Failed to start DAQ monitoring", "error")
                return False
            
            # Wait for DAQ to stabilize
            if not self._interruptible_sleep(1):
                self._step_stop_daq_monitoring()
                return False
            
            # Initialize screen test timing for DAQ data collection
            test_start_time = time.time()
            self._screen_test_start_time = test_start_time
            
            # Signal DAQ monitoring that test has started
            if hasattr(self, '_screen_test_started'):
                self._screen_test_started.set()
                self.log_callback("? Phone app test start signal sent to DAQ monitoring", "info")
            else:
                self.log_callback("?? Warning: _screen_test_started event not found", "warn")
            
            # 8. Phone App Test (10 seconds)
            self.log_callback("=== Step 8: Phone App Test Started (10s) ===", "info")
            
            # 0?: Phone app ??
            self.log_callback("0s: Opening Phone app", "info")
            if not self.adb_service.open_phone_app():
                self.log_callback("Failed to open Phone app", "error")
            if not self._interruptible_sleep(0.5):
                self._step_stop_daq_monitoring()
                return False
            
            # 5? ?? (Phone app??)
            self.log_callback("Waiting 5 seconds in Phone app...", "info")
            if not self._interruptible_sleep(5):
                self.log_callback("Phone app wait interrupted", "info")
                self._step_stop_daq_monitoring()
                return False
            
            # 5?: Back key? ? ?? ??
            self.log_callback("5s: Press back key to go to home screen", "info")
            if not self.adb_service.press_back_key():
                self.log_callback("Failed to press back key", "error")
            if not self._interruptible_sleep(0.5):
                self._step_stop_daq_monitoring()
                return False
            
            # ? ???? ??? ??
            if not self.adb_service.press_home_key():
                self.log_callback("Failed to press home key", "error")
            
            # 5? ? ?? (? 10?)
            self.log_callback("Waiting 5 more seconds on home screen...", "info")
            if not self._interruptible_sleep(4.5):  # 0.5?? ?? ?????? 4.5?? ?
                self.log_callback("Home screen wait interrupted", "info")
                self._step_stop_daq_monitoring()
                return False
            
            self.log_callback("=== Phone App Test Completed (10s) ===", "info")
            
            # 9. Stop DAQ monitoring
            self.log_callback("Step 9: Stopping DAQ monitoring", "info")
            self._step_stop_daq_monitoring()
            
            # Wait for DAQ to finish
            if not self._interruptible_sleep(2):
                return False
            
            self.log_callback("Optimized Phone app test with DAQ completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in optimized Phone app test: {e}", "error")
            # Ensure DAQ monitoring is stopped
            try:
                self._step_stop_daq_monitoring()
            except:
                pass
            return False
    def _step_set_screen_timeout_10min(self) -> bool:
        """Set screen timeout to 10 minutes"""
        try:
            self.log_callback("Setting screen timeout to 10 minutes", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # 10 minutes = 600,000 milliseconds
            timeout_ms = 600000
            success = self.adb_service.set_screen_timeout(timeout_ms)
            
            if success:
                self.log_callback("Screen timeout set to 10 minutes successfully", "info")
            else:
                self.log_callback("Failed to set screen timeout", "error")
            
            return success
            
        except Exception as e:
            self.log_callback(f"Error setting screen timeout: {e}", "error")
            return False
    
    def _step_lcd_on_and_unlock(self) -> bool:
        """LCD ON + Unlock (at the beginning)"""
        try:
            self.log_callback("=== LCD ON + Unlock ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # 1. LCD ON
            self.log_callback("Step 1: Turn LCD ON", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 2. Unlock screen
            self.log_callback("Step 2: Unlock screen", "info")
            if not self.adb_service.unlock_screen():
                self.log_callback("Failed to unlock screen", "error")
            if not self._interruptible_sleep(1):
                return False
            
            self.log_callback("LCD ON + Unlock completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in LCD ON + unlock: {e}", "error")
            return False
    
    def _step_home_and_clear_apps_only(self) -> bool:
        """Home -> Clear Apps (without unlock)"""
        try:
            self.log_callback("=== Home + Clear Apps ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # 1. Press Home button
            self.log_callback("Step 1: Press Home button", "info")
            if not self.adb_service.press_home_key():
                self.log_callback("Failed to press home key", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 2. Clear all recent apps
            self.log_callback("Step 2: Clear all recent apps", "info")
            if not self.adb_service.clear_recent_apps():
                self.log_callback("Failed to clear recent apps", "error")
            if not self._interruptible_sleep(2):
                return False
            
            self.log_callback("Home + Clear Apps completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in home + clear apps: {e}", "error")
            return False
    
    def _step_unlock_and_clear_apps(self) -> bool:
        """Unlock -> Home -> Clear Apps (without LCD ON)"""
        try:
            self.log_callback("=== Unlock + Home + Clear Apps ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # 1. Unlock screen
            self.log_callback("Step 1: Unlock screen", "info")
            if not self.adb_service.unlock_screen():
                self.log_callback("Failed to unlock screen", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 2. Press Home button
            self.log_callback("Step 2: Press Home button", "info")
            if not self.adb_service.press_home_key():
                self.log_callback("Failed to press home key", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 3. Clear all recent apps
            self.log_callback("Step 3: Clear all recent apps", "info")
            if not self.adb_service.clear_recent_apps():
                self.log_callback("Failed to clear recent apps", "error")
            if not self._interruptible_sleep(2):
                return False
            
            self.log_callback("Unlock/Home/Clear Apps completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in unlock/home/clear apps: {e}", "error")
            return False
    
    def _step_lcd_on_unlock_home_clear_apps(self) -> bool:
        """LCD ON -> Unlock -> Home -> Clear Apps"""
        try:
            self.log_callback("=== Init Mode: LCD ON + Unlock + Home + Clear Apps ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # 1. LCD ON
            self.log_callback("Step 1: Turn LCD ON", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 2. Unlock screen
            self.log_callback("Step 2: Unlock screen", "info")
            if not self.adb_service.unlock_screen():
                self.log_callback("Failed to unlock screen", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 3. Press Home button
            self.log_callback("Step 3: Press Home button", "info")
            if not self.adb_service.press_home_key():
                self.log_callback("Failed to press home key", "error")
            if not self._interruptible_sleep(1):
                return False
            
            # 4. Clear all recent apps
            self.log_callback("Step 4: Clear all recent apps", "info")
            if not self.adb_service.clear_recent_apps():
                self.log_callback("Failed to clear recent apps", "error")
            if not self._interruptible_sleep(2):
                return False
            
            self.log_callback("Init mode LCD/unlock/clear setup completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in LCD/unlock/clear setup: {e}", "error")
            return False
    
    def _step_idle_wait_test(self) -> bool:
        """Execute idle wait test (5 minutes = 300 seconds) without running any app"""
        try:
            duration_seconds = 300.0  # 5 minutes
            self.log_callback(f"=== Starting Idle Wait ({duration_seconds} seconds / {duration_seconds/60:.1f} minutes) ===", "info")
            self.log_callback("No app will be executed - device will remain idle", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Wait for specified duration with progress updates every 30 seconds
            total_seconds = int(duration_seconds)
            update_interval = 30  # Update progress every 30 seconds
            
            elapsed = 0
            while elapsed < total_seconds:
                if self.stop_requested:
                    self.log_callback("Idle wait stopped by user request", "warn")
                    return False
                
                remaining = total_seconds - elapsed
                progress = int((elapsed / total_seconds) * 100)
                
                if elapsed % update_interval == 0 or elapsed == 0:
                    minutes_elapsed = elapsed // 60
                    seconds_elapsed = elapsed % 60
                    minutes_remaining = remaining // 60
                    seconds_remaining = remaining % 60
                    
                    self.log_callback(
                        f"Idle wait progress: {elapsed}/{total_seconds}s ({progress}%) - "
                        f"Elapsed: {minutes_elapsed}m {seconds_elapsed}s, "
                        f"Remaining: {minutes_remaining}m {seconds_remaining}s",
                        "info"
                    )
                
                # Sleep for 1 second at a time to allow for cancellation/interruption
                time.sleep(1)
                elapsed += 1
            
            self.log_callback(f"✅ Idle wait completed: {total_seconds} seconds ({total_seconds/60:.1f} minutes)", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error during idle wait: {e}", "error")
            import traceback
            traceback.print_exc()
            return False
    
    def _step_screen_onoff_test(self) -> bool:
        """Execute Screen On/Off test (20 seconds)
        0초: LCD on
        2초마다 LCD 끄고 키고 반복
        20초: 테스트 끝
        """
        try:
            self.log_callback("=== Executing Screen On/Off Test (20 seconds) ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Initialize screen test timing for DAQ data collection
            test_start_time = time.time()
            self._screen_test_start_time = test_start_time
            
            # Signal DAQ monitoring that test has started
            if hasattr(self, '_screen_test_started'):
                self._screen_test_started.set()
                self.log_callback("✅ Screen test start signal sent to DAQ monitoring", "info")
            else:
                self.log_callback("⚠️ Warning: _screen_test_started event not found", "warn")
            
            # 테스트 시작 - 2초마다 ON/OFF 토글
            # 0s: ON -> 2s: OFF -> 4s: ON -> 6s: OFF -> ... -> 18s: OFF -> 20s: 종료
            # 총 10번의 동작 (ON 5번, OFF 5번)
            test_duration = 20  # 20초
            toggle_interval = 2  # 2초마다
            
            screen_on = True  # 첫 동작은 ON
            action_count = 0
            
            for elapsed in range(0, test_duration, toggle_interval):
                if self.stop_requested:
                    self.log_callback("Screen On/Off test stopped by user request", "warn")
                    return False
                
                action_count += 1
                
                if screen_on:
                    self.log_callback(f"{elapsed}s: Action {action_count}/10 - Turning LCD ON", "info")
                    if not self.adb_service.turn_screen_on():
                        self.log_callback(f"Failed to turn screen on at {elapsed}s", "error")
                        return False
                else:
                    self.log_callback(f"{elapsed}s: Action {action_count}/10 - Turning LCD OFF", "info")
                    if not self.adb_service.turn_screen_off():
                        self.log_callback(f"Failed to turn screen off at {elapsed}s", "error")
                        return False
                
                # 다음 동작을 위해 토글
                screen_on = not screen_on
                
                # 마지막 동작이 아니면 2초 대기
                if elapsed + toggle_interval < test_duration:
                    time.sleep(toggle_interval)
            
            # 20초: 테스트 끝
            self.log_callback("20s: Screen On/Off test completed", "info")
            
            # Log data collection status
            data_count = len(self.daq_data) if hasattr(self, 'daq_data') else 0
            self.log_callback(f"✅ Screen On/Off test completed. Collected {data_count} data points", "info")
            
            if data_count == 0:
                self.log_callback("⚠️ WARNING: No data was collected during Screen On/Off test!", "warn")
            elif data_count < 20000:
                self.log_callback(f"⚠️ WARNING: Expected 20,000 samples but got {data_count}", "warn")
            else:
                self.log_callback(f"✅ Successfully collected {data_count} data points (0-{data_count-1} ms)", "info")
            
            return True
            
        except Exception as e:
            self.log_callback(f"Error executing Screen On/Off test: {e}", "error")
            import traceback
            traceback.print_exc()
            return False
    
    def _step_lcd_off(self) -> bool:
        """LCD off"""
        try:
            self.log_callback("=== Turning LCD OFF ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Turn screen off
            if not self.adb_service.turn_screen_off():
                self.log_callback("Failed to turn screen off", "error")
                return False
            
            time.sleep(1.0)
            self.log_callback("✅ LCD turned OFF", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error turning LCD off: {e}", "error")
            import traceback
            traceback.print_exc()
            return False
    
    def _step_phone_app_scenario_test(self) -> bool:
        """Phone App scenario test (DAQ already running)"""
        try:
            self.log_callback("=== Phone App Scenario Test Started ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Initialize screen test timing for DAQ data collection
            test_start_time = time.time()
            self._screen_test_start_time = test_start_time
            
            # Signal DAQ monitoring that test has started
            if hasattr(self, '_screen_test_started'):
                self._screen_test_started.set()
                self.log_callback("? Phone app test start signal sent to DAQ monitoring", "info")
            else:
                self.log_callback("?? Warning: _screen_test_started event not found", "warn")
            
            # Phone App Scenario Test (10 seconds)
            self.log_callback("[Phone App Scenario] Starting 10-second test", "info")
            
            # 0?: Phone app ??
            self.log_callback("0s: Click Phone app", "info")
            if not self.adb_service.open_phone_app():
                self.log_callback("Failed to open Phone app", "error")
            time.sleep(0.5)
            
            # 5??? ?? (Phone app??)
            self.log_callback("Waiting until 5s in Phone app...", "info")
            time.sleep(4.5)  # 0.5?? ?? ?????? 4.5? ?
            
            # 5?: Back key ??
            self.log_callback("5s: Click back key", "info")
            if not self.adb_service.press_back_key():
                self.log_callback("Failed to press back key", "error")
            time.sleep(0.5)
            
            # 10??? ?? (? ????)
            self.log_callback("Waiting until 10s on home screen...", "info")
            time.sleep(4.5)  # 0.5?? ?? ?????? 4.5? ?
            
            # 10?: Test end
            self.log_callback("10s: Test end", "info")
            
            self.log_callback("=== Phone App Scenario Test Completed ===", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in Phone app scenario test: {e}", "error")
            return False
    
    # ===== NEW PHONE APP TEST STEP METHODS =====
    
    def _step_connect_wifi_2g(self) -> bool:
        """Connect to 2.4GHz WiFi using improved ADB service method"""
        try:
            self.log_callback("=== Connecting to 2.4GHz WiFi ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Use WiFi config from test_scenarios/configs/wifi_config.py
            try:
                import sys
                import os
                # Add project root to path if not already there
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                
                from test_scenarios.configs.wifi_config import WiFiConfig
                wifi_2g = WiFiConfig.get_2g_primary()
                ssid = wifi_2g['ssid']
                password = wifi_2g['password']
                self.log_callback(f"? Using WiFi network from config: {ssid}", "info")
            except Exception as e:
                # Fallback to hardcoded values
                self.log_callback(f"?? WiFi config not available ({str(e)}), using default", "warn")
                ssid = "0_WIFIFW_RAX40_2nd_2G"
                password = "cppower12"
                self.log_callback(f"Using default WiFi: {ssid}", "info")
            
            # Use improved connect_wifi_2g method from ADB service
            success = self.adb_service.connect_wifi_2g(ssid, password)
            
            if success:
                # Get final WiFi status
                wifi_status = self.adb_service.get_wifi_status()
                self.log_callback(f"? WiFi Status: {wifi_status['connection_state']} - {wifi_status['connected_ssid']}", "info")
                return True
            else:
                self.log_callback("? Failed to connect to 2.4GHz WiFi", "error")
                return False
            
        except Exception as e:
            self.log_callback(f"? Error connecting to 2.4GHz WiFi: {e}", "error")
            return False
    
    def _step_enable_bluetooth(self) -> bool:
        """Enable Bluetooth using improved ADB service method"""
        try:
            self.log_callback("=== Enabling Bluetooth ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Use improved enable_bluetooth method from ADB service
            # This method includes proper verification and retry logic
            success = self.adb_service.enable_bluetooth()
            
            if success:
                # Get final Bluetooth status
                bt_status = self.adb_service.get_bluetooth_status()
                self.log_callback(f"? Bluetooth Status: {bt_status}", "info")
                return True
            else:
                # Get status even on failure for debugging
                bt_status = self.adb_service.get_bluetooth_status()
                self.log_callback(f"? Failed to enable Bluetooth. Status: {bt_status}", "error")
                return False
            
        except Exception as e:
            self.log_callback(f"? Error enabling Bluetooth: {e}", "error")
            return False
    
    def _step_set_screen_timeout_10min(self) -> bool:
        """Set screen timeout to 10 minutes"""
        try:
            self.log_callback("=== Setting screen timeout to 10 minutes ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Set screen timeout to 10 minutes (600000 milliseconds)
            result = self.adb_service._run_adb_command(['shell', 'settings', 'put', 'system', 'screen_off_timeout', '600000'])
            if result is None:
                self.log_callback("Failed to set screen timeout", "error")
                return False
            
            time.sleep(1)
            
            # Verify the setting
            timeout_value = self.adb_service._run_adb_command(['shell', 'settings', 'get', 'system', 'screen_off_timeout'])
            if timeout_value and '600000' in timeout_value:
                self.log_callback("Screen timeout set to 10 minutes successfully", "info")
                return True
            else:
                self.log_callback("Screen timeout verification failed", "warn")
                return False
            
        except Exception as e:
            self.log_callback(f"Error setting screen timeout: {e}", "error")
            return False
    
    def _step_lcd_on_unlock_home_clear_apps(self) -> bool:
        """LCD on -> ??? ?? ?? -> home ?? ?? -> App clear all ??"""
        try:
            self.log_callback("=== LCD ON + Unlock + Home + Clear Apps ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Step 1: LCD on (turn screen on)
            self.log_callback("Step 1: Turning LCD on", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
                return False
            if not self._interruptible_sleep(1):
                return False
            
            # Step 2: ??? ?? ?? (unlock screen)
            self.log_callback("Step 2: Unlocking screen", "info")
            if not self.adb_service.unlock_screen():
                self.log_callback("Failed to unlock screen", "error")
                return False
            if not self._interruptible_sleep(1):
                return False
            
            # Step 3: Home ?? ??
            self.log_callback("Step 3: Pressing home button", "info")
            result = self.adb_service._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_HOME'])
            if result is None:
                self.log_callback("Failed to press home button", "error")
                return False
            if not self._interruptible_sleep(1):
                return False
            
            # Step 4: App clear all ??
            self.log_callback("Step 4: Clearing all apps", "info")
            if not self.adb_service.clear_recent_apps():
                self.log_callback("Failed to clear all apps", "error")
                return False
            
            self.log_callback("LCD on + Unlock + Home + Clear Apps completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in LCD on + unlock + home + clear apps: {e}", "error")
            return False
    
    def _step_wait_current_stabilization(self) -> bool:
        """?? ??? ?? ?? 10?"""
        try:
            self.log_callback("=== Waiting for current stabilization (10 seconds) ===", "info")
            
            # 10? ?? ????? ?? ?? ??
            for i in range(10):
                if self.stop_requested:
                    self.log_callback("Stop requested during stabilization", "warn")
                    return False
                
                progress = int((i + 1) / 10 * 100)
                self.log_callback(f"Current stabilization: {i+1}/10 seconds ({progress}%)", "info")
                if not self._interruptible_sleep(1):
                    self.log_callback("Current stabilization interrupted", "info")
                    return False
            
            self.log_callback("Current stabilization completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error during current stabilization: {e}", "error")
            return False
    
    def _step_execute_phone_app_scenario(self) -> bool:
        """Execute Phone App scenario test (10 seconds)"""
        try:
            self.log_callback("=== Executing Phone App Scenario (10 seconds) ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Initialize test timing for DAQ data collection
            test_start_time = time.time()
            self._screen_test_start_time = test_start_time
            
            # Signal DAQ monitoring that test has started
            if hasattr(self, '_screen_test_started'):
                self._screen_test_started.set()
                self.log_callback("? Phone app test start signal sent to DAQ monitoring", "info")
            else:
                self.log_callback("?? Warning: _screen_test_started event not found", "warn")
            
            # 0?: Phone app ??
            self.log_callback("0s: Clicking Phone app", "info")
            # Open phone app using intent
            result = self.adb_service._run_adb_command(['shell', 'am', 'start', '-a', 'android.intent.action.CALL_BUTTON'])
            if result is None:
                # Fallback: try dialer package
                result = self.adb_service._run_adb_command(['shell', 'am', 'start', '-n', 'com.android.dialer/.DialtactsActivity'])
                if result is None:
                    self.log_callback("Failed to open Phone app", "error")
                    return False
            
            # Wait until 5 seconds
            self.log_callback("Waiting in Phone app until 5s...", "info")
            elapsed = 0
            while elapsed < 5.0:
                if self.stop_requested:
                    self.log_callback("Stop requested during Phone app test", "warn")
                    return False
                
                time.sleep(0.5)
                elapsed = time.time() - test_start_time
                progress = int((elapsed / 10.0) * 100)
                self.log_callback(f"Phone app test progress: {elapsed:.1f}s/10s ({progress}%)", "info")
            
            # 5?: Back key ??
            self.log_callback("5s: Pressing back key", "info")
            result = self.adb_service._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_BACK'])
            if result is None:
                self.log_callback("Failed to press back key", "error")
                return False
            
            # Wait until 10 seconds (test end)
            self.log_callback("Waiting until 10s (test end)...", "info")
            while elapsed < 10.0:
                if self.stop_requested:
                    self.log_callback("Stop requested during Phone app test", "warn")
                    return False
                
                time.sleep(0.5)
                elapsed = time.time() - test_start_time
                progress = int((elapsed / 10.0) * 100)
                self.log_callback(f"Phone app test progress: {elapsed:.1f}s/10s ({progress}%)", "info")
            
            # 10?: Test end
            self.log_callback("10s: Phone app test completed", "info")
            
            # Record test completion time
            test_end_time = time.time()
            actual_duration = test_end_time - test_start_time
            self.log_callback(f"Phone app scenario completed in {actual_duration:.1f} seconds", "info")
            
            return True
            
        except Exception as e:
            self.log_callback(f"Error executing Phone app scenario: {e}", "error")
            return False
    
    def _step_apply_default_settings(self) -> bool:
        """Apply default settings for consistent test environment"""
        try:
            self.log_callback("=== Applying Default Settings ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Verify device connection before applying settings
            if not self.adb_service.verify_device_connection():
                self.log_callback("? Device connection verification failed", "error")
                return False
            
            # Get initial device status
            initial_status = self.adb_service.get_device_status()
            self.log_callback(f"?? Initial device status: {initial_status}", "info")
            
            # Apply default settings using ADB service
            success = self.adb_service.apply_default_settings()
            
            # Get final device status after applying settings
            final_status = self.adb_service.get_device_status()
            self.log_callback(f"?? Final device status: {final_status}", "info")
            
            if success:
                self.log_callback("? Default settings applied successfully", "info")
                self.log_callback("Device is now in consistent initial state for testing", "info")
                return True
            else:
                self.log_callback("?? Default settings partially applied", "warn")
                self.log_callback("Continuing with test (some settings may not be optimal)", "warn")
                return True  # Continue even if some settings failed
                
        except Exception as e:
            self.log_callback(f"? Error applying default settings: {e}", "error")
            self.log_callback("Continuing with test (device may not be in optimal state)", "warn")
            return True  # Don't fail the entire test for default settings
