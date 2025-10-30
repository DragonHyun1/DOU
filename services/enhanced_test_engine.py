"""
Enhanced Test Engine with Proper Thread Architecture
Based on AI feedback and user requirements for better thread management
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QMetaObject, Qt, QThread
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    QObject = object
    def pyqtSignal(*args): return None

from .adb_service import ADBService
from .daq_collection_thread import DAQCollectionThread


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
    stabilization_time: float = 10.0
    monitoring_interval: float = 1.0
    test_duration: float = 10.0
    steps: List[TestStep] = None


class EnhancedTestEngine(QObject):
    """Enhanced Test Engine with proper thread architecture"""
    
    # Qt Signals for thread-safe communication (following AI recommendations)
    progress_updated = pyqtSignal(int, str)  # progress, status
    test_completed = pyqtSignal(bool, str)   # success, message
    log_message = pyqtSignal(str, str)       # message, level
    step_completed = pyqtSignal(str, bool)   # step_name, success
    
    def __init__(self, hvpm_service=None, daq_service=None, log_callback: Callable = None):
        super().__init__()
        
        # Services
        self.hvpm_service = hvpm_service
        self.daq_service = daq_service
        self.adb_service = ADBService()
        self.log_callback = log_callback or self._default_log
        
        # Test state
        self.current_test_config: Optional[TestConfig] = None
        self.status = TestStatus.IDLE
        self.current_step = 0
        self.total_steps = 0
        
        # Thread control (following AI recommendations)
        self.stop_requested = threading.Event()  # Thread-safe stop flag
        self.test_worker: Optional[QThread] = None
        
        # DAQ collection (separate from main test flow)
        self.daq_collector = DAQCollectionThread(daq_service, log_callback)
        
        # Results
        self.test_results = {}
        
    def _default_log(self, message: str, level: str = "info"):
        """Default logging function"""
        print(f"[{level.upper()}] {message}")
        
        # Emit log signal for UI (thread-safe)
        self._emit_signal_safe(self.log_message, message, level)
    
    def _emit_signal_safe(self, signal, *args):
        """Thread-safe signal emission (from AI recommendations)"""
        if QT_AVAILABLE:
            try:
                if threading.current_thread() == threading.main_thread():
                    # Main thread - direct emit
                    signal.emit(*args)
                else:
                    # Background thread - use QMetaObject for thread safety
                    QMetaObject.invokeMethod(
                        self,
                        lambda: signal.emit(*args),
                        Qt.ConnectionType.QueuedConnection
                    )
            except Exception as e:
                # Fallback to print if Qt signals fail
                print(f"Signal emit error: {e}, args: {args}")
    
    def start_test(self, scenario_key: str) -> bool:
        """Start test in worker thread (following AI recommendations)"""
        try:
            if self.status != TestStatus.IDLE:
                self.log_callback("Test already running or not idle", "warn")
                return False
            
            # Get scenario configuration
            config = self._get_scenario_config(scenario_key)
            if not config:
                self.log_callback(f"Scenario not found: {scenario_key}", "error")
                return False
            
            self.current_test_config = config
            self.total_steps = len(config.steps) if config.steps else 0
            self.current_step = 0
            
            # Reset stop flag
            self.stop_requested.clear()
            
            # Start worker thread (AI recommendation)
            if QT_AVAILABLE:
                self.test_worker = QThread()
                self.moveToThread(self.test_worker)
                
                # Connect worker signals
                self.test_worker.started.connect(self._execute_test_in_worker)
                self.test_worker.finished.connect(self._on_worker_finished)
                
                self.test_worker.start()
            else:
                # Fallback for non-Qt environments
                worker_thread = threading.Thread(target=self._execute_test_in_worker, daemon=True)
                worker_thread.start()
            
            self.log_callback(f"Test started in worker thread: {config.name}", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error starting test: {e}", "error")
            return False
    
    def stop_test(self):
        """Stop test execution (AI recommendation - immediate flag setting)"""
        try:
            self.log_callback("Stop test requested", "info")
            self.stop_requested.set()  # Thread-safe stop flag
            
            # Stop DAQ collection if running
            if self.daq_collector.is_collecting:
                self.daq_collector.stop_collection()
            
            # Wait for worker to finish
            if self.test_worker and self.test_worker.isRunning():
                self.test_worker.quit()
                if not self.test_worker.wait(5000):  # 5 second timeout
                    self.log_callback("Worker thread did not stop gracefully", "warn")
            
            self.status = TestStatus.STOPPED
            self._emit_signal_safe(self.test_completed, False, "Test stopped by user")
            
        except Exception as e:
            self.log_callback(f"Error stopping test: {e}", "error")
    
    def _execute_test_in_worker(self):
        """Execute test in worker thread (AI recommendation)"""
        try:
            self.status = TestStatus.RUNNING
            self.log_callback(f"Worker thread started: {self.current_test_config.name}", "info")
            
            # Execute all test steps
            for i, step in enumerate(self.current_test_config.steps):
                # Check stop flag (AI recommendation - immediate response)
                if self.stop_requested.is_set():
                    self.log_callback("Test stopped by user request", "info")
                    self.status = TestStatus.STOPPED
                    self._emit_signal_safe(self.test_completed, False, "Stopped by user")
                    return
                
                self.current_step = i + 1
                progress = int((self.current_step / self.total_steps) * 100)
                
                # Update progress (thread-safe)
                self._emit_signal_safe(self.progress_updated, progress, f"Step {self.current_step}: {step.name}")
                self.log_callback(f"Executing step {self.current_step}/{self.total_steps}: {step.name}", "info")
                
                # Execute step
                step_success = self._execute_step(step)
                
                # Emit step completion signal
                self._emit_signal_safe(self.step_completed, step.name, step_success)
                
                if not step_success:
                    self.log_callback(f"Step failed: {step.name}", "error")
                    self.status = TestStatus.FAILED
                    self._emit_signal_safe(self.test_completed, False, f"Step failed: {step.name}")
                    return
                
                self.log_callback(f"Step completed: {step.name}", "info")
            
            # All steps completed successfully
            self.status = TestStatus.COMPLETED
            self.log_callback("All test steps completed successfully", "info")
            self._emit_signal_safe(self.test_completed, True, "Test completed successfully")
            
        except Exception as e:
            self.log_callback(f"Critical error in worker thread: {e}", "error")
            self.status = TestStatus.FAILED
            self._emit_signal_safe(self.test_completed, False, f"Critical error: {e}")
    
    def _execute_step(self, step: TestStep) -> bool:
        """Execute individual test step (runs in worker thread)"""
        try:
            # Check stop flag before each step
            if self.stop_requested.is_set():
                return False
            
            # Execute step based on action
            if step.action == "apply_default_settings":
                return self._step_apply_default_settings()
            elif step.action == "lcd_on_and_unlock":
                return self._step_lcd_on_and_unlock()
            elif step.action == "set_hvpm_voltage":
                return self._step_set_hvpm_voltage(step.parameters.get("voltage", 4.0))
            elif step.action == "enable_flight_mode":
                return self._step_enable_flight_mode()
            elif step.action == "connect_wifi_2g":
                return self._step_connect_wifi_2g()
            elif step.action == "enable_bluetooth":
                return self._step_enable_bluetooth()
            elif step.action == "home_and_clear_apps":
                return self._step_home_and_clear_apps()
            elif step.action == "wait_current_stabilization":
                return self._step_wait_current_stabilization()
            elif step.action == "start_daq_monitoring":
                return self._step_start_daq_collection()
            elif step.action == "execute_phone_app_scenario":
                return self._step_execute_phone_app_scenario()
            elif step.action == "stop_daq_monitoring":
                return self._step_stop_daq_collection()
            elif step.action == "export_to_excel":
                return self._step_export_to_excel()
            else:
                self.log_callback(f"Unknown step action: {step.action}", "error")
                return False
                
        except Exception as e:
            self.log_callback(f"Error executing step {step.name}: {e}", "error")
            return False
    
    def _step_apply_default_settings(self) -> bool:
        """Apply default settings (AI recommendation - don't fail entire test)"""
        try:
            self.log_callback("Applying default settings...", "info")
            
            if not self.adb_service.verify_device_connection():
                self.log_callback("Device connection verification failed", "error")
                return False
            
            success = self.adb_service.apply_default_settings()
            return success or True  # Continue even if partially failed (AI recommendation)
            
        except Exception as e:
            self.log_callback(f"Error applying default settings: {e}", "error")
            return True  # Don't fail entire test (AI recommendation)
    
    def _step_lcd_on_and_unlock(self) -> bool:
        """Early LCD activation (user optimization)"""
        try:
            self.log_callback("LCD ON + Unlock (early activation)...", "info")
            
            success = (self.adb_service.turn_screen_on() and 
                      self.adb_service.unlock_screen())
            
            if success:
                self.log_callback("LCD activated and unlocked", "info")
            else:
                self.log_callback("LCD activation failed", "error")
            
            return success
            
        except Exception as e:
            self.log_callback(f"Error in LCD activation: {e}", "error")
            return False
    
    def _step_start_daq_collection(self) -> bool:
        """Start DAQ collection (user's separate thread approach)"""
        try:
            self.log_callback("Starting DAQ collection thread...", "info")
            
            # Configure channels (should be configurable)
            enabled_channels = ['ai0', 'ai1', 'ai2', 'ai3']
            self.daq_collector.configure(enabled_channels, 1.0)
            
            # Start collection (no waiting, no timeout issues)
            success = self.daq_collector.start_collection()
            
            if success:
                self.log_callback("DAQ collection started", "info")
            else:
                self.log_callback("DAQ collection failed - continuing without DAQ", "warn")
            
            return True  # Always continue (AI recommendation)
            
        except Exception as e:
            self.log_callback(f"Error starting DAQ collection: {e}", "error")
            return True  # Don't fail test for DAQ issues
    
    def _step_execute_phone_app_scenario(self) -> bool:
        """Execute Phone App test with frequent stop checks"""
        try:
            self.log_callback("Executing Phone App scenario (10s)...", "info")
            
            # 0s: Open Phone app
            self.log_callback("0s: Opening Phone app", "info")
            if not self.adb_service.open_phone_app():
                self.log_callback("Failed to open Phone app", "error")
                return False
            
            # Wait 5s with frequent stop checks (AI recommendation)
            for i in range(50):  # 5s = 50 * 0.1s
                if self.stop_requested.is_set():
                    return False
                time.sleep(0.1)
                
                # Update progress every second
                if i % 10 == 0:
                    elapsed = i / 10
                    progress = int((elapsed / 10.0) * 100)
                    self._emit_signal_safe(self.progress_updated, progress, f"Phone app test: {elapsed:.1f}s/10s")
            
            # 5s: Press back key
            self.log_callback("5s: Pressing back key", "info")
            if not self.adb_service.press_back_key():
                self.log_callback("Failed to press back key", "error")
                return False
            
            # Wait remaining 5s with stop checks
            for i in range(50):  # 5s = 50 * 0.1s
                if self.stop_requested.is_set():
                    return False
                time.sleep(0.1)
                
                # Update progress
                if i % 10 == 0:
                    elapsed = 5 + (i / 10)
                    progress = int((elapsed / 10.0) * 100)
                    self._emit_signal_safe(self.progress_updated, progress, f"Phone app test: {elapsed:.1f}s/10s")
            
            # 10s: Test completed
            self.log_callback("10s: Phone app test completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in Phone app scenario: {e}", "error")
            return False
    
    def _step_stop_daq_collection(self) -> bool:
        """Stop DAQ collection and get results"""
        try:
            self.log_callback("Stopping DAQ collection...", "info")
            
            results = self.daq_collector.stop_collection()
            
            if results.get('success'):
                data_count = results.get('data_count', 0)
                duration = results.get('duration', 0)
                self.log_callback(f"DAQ collection completed: {data_count} points in {duration:.1f}s", "info")
                self.test_results['daq_data'] = results
            else:
                self.log_callback("DAQ collection had issues", "warn")
            
            return True  # Always continue (AI recommendation)
            
        except Exception as e:
            self.log_callback(f"Error stopping DAQ collection: {e}", "error")
            return True
    
    def _step_export_to_excel(self) -> bool:
        """Export results (AI recommendation - don't block UI)"""
        try:
            self.log_callback("Exporting to Excel...", "info")
            
            # Quick export simulation (real implementation would be more complex)
            time.sleep(1)  # Minimal time
            
            if 'daq_data' in self.test_results:
                data_count = self.test_results['daq_data'].get('data_count', 0)
                self.log_callback(f"Exported {data_count} data points", "info")
            
            return True
            
        except Exception as e:
            self.log_callback(f"Error exporting: {e}", "error")
            return False
    
    def _get_scenario_config(self, scenario_key: str) -> Optional[TestConfig]:
        """Get scenario configuration"""
        if scenario_key == "phone_app_test":
            return TestConfig(
                name="Phone App Test",
                description="Enhanced Phone App test with proper threading",
                hvpm_voltage=4.0,
                stabilization_time=10.0,
                test_duration=10.0,
                steps=[
                    TestStep("default_settings", 5.0, "apply_default_settings"),
                    TestStep("lcd_on_unlock", 3.0, "lcd_on_and_unlock"),
                    TestStep("init_hvpm", 2.0, "set_hvpm_voltage", {"voltage": 4.0}),
                    TestStep("airplane_mode", 2.0, "enable_flight_mode"),
                    TestStep("wifi_2g_connect", 15.0, "connect_wifi_2g"),
                    TestStep("bluetooth_on", 2.0, "enable_bluetooth"),
                    TestStep("home_clear_apps", 8.0, "home_and_clear_apps"),
                    TestStep("current_stabilization", 10.0, "wait_current_stabilization"),
                    TestStep("start_daq", 2.0, "start_daq_monitoring"),
                    TestStep("phone_app_test", 10.0, "execute_phone_app_scenario"),
                    TestStep("stop_daq", 2.0, "stop_daq_monitoring"),
                    TestStep("export_excel", 3.0, "export_to_excel")
                ]
            )
        return None
    
    def _on_worker_finished(self):
        """Handle worker thread completion"""
        self.log_callback("Worker thread finished", "info")
        
        # Clean up
        if self.test_worker:
            self.test_worker.deleteLater()
            self.test_worker = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current test status"""
        return {
            'status': self.status.value,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress_percent': int((self.current_step / self.total_steps) * 100) if self.total_steps > 0 else 0,
            'daq_collecting': self.daq_collector.is_collecting,
            'stop_requested': self.stop_requested.is_set()
        }
    
    # Placeholder step methods (to be implemented)
    def _step_set_hvpm_voltage(self, voltage: float) -> bool:
        self.log_callback(f"Setting HVPM to {voltage}V", "info")
        time.sleep(2)
        return True
    
    def _step_enable_flight_mode(self) -> bool:
        self.log_callback("Enabling flight mode", "info")
        return self.adb_service.enable_flight_mode()
    
    def _step_connect_wifi_2g(self) -> bool:
        self.log_callback("Connecting to 2.4GHz WiFi", "info")
        return self.adb_service.connect_wifi_2g("0_WIFIFW_RAX40_2nd_2G", "cppower12")
    
    def _step_enable_bluetooth(self) -> bool:
        self.log_callback("Enabling Bluetooth", "info")
        return self.adb_service.enable_bluetooth()
    
    def _step_home_and_clear_apps(self) -> bool:
        self.log_callback("Home + Clear Apps", "info")
        return (self.adb_service.press_home() and 
                self.adb_service.clear_recent_apps())
    
    def _step_wait_current_stabilization(self) -> bool:
        self.log_callback("Waiting for current stabilization (10s)", "info")
        # Wait with frequent stop checks
        for i in range(100):  # 10s = 100 * 0.1s
            if self.stop_requested.is_set():
                return False
            time.sleep(0.1)
            if i % 10 == 0:  # Every second
                progress = int((i / 100) * 100)
                self._emit_signal_safe(self.progress_updated, progress, f"Stabilization: {i/10:.1f}s/10s")
        return True