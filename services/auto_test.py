# Auto Test Service for HVPM Monitor
import time
import threading
from typing import Callable, Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from services import adb

class TestScenario:
    """Base class for test scenarios"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.is_running = False
        
    def execute(self, device: str, log_callback: Callable, progress_callback: Callable = None) -> bool:
        """Execute the test scenario"""
        raise NotImplementedError
        
    def stop(self):
        """Stop the test scenario"""
        self.is_running = False

class ScreenOnOffTest(TestScenario):
    """Screen On/Off repetitive test scenario"""
    
    def __init__(self, cycles: int = 5, on_duration: int = 10, off_duration: int = 5):
        super().__init__(
            "Screen On/Off Test", 
            f"Repeat screen on ({on_duration}s) and off ({off_duration}s) for {cycles} cycles"
        )
        self.cycles = cycles
        self.on_duration = on_duration
        self.off_duration = off_duration
        
    def execute(self, device: str, log_callback: Callable, progress_callback: Callable = None) -> bool:
        """Execute screen on/off test"""
        self.is_running = True
        
        try:
            log_callback(f"🔄 Starting {self.name} - {self.cycles} cycles", "info")
            
            for cycle in range(self.cycles):
                if not self.is_running:
                    log_callback("⏹️ Test stopped by user", "warn")
                    return False
                    
                # Update progress
                if progress_callback:
                    progress = int((cycle / self.cycles) * 100)
                    progress_callback(progress, f"Cycle {cycle + 1}/{self.cycles}")
                
                log_callback(f"📱 Cycle {cycle + 1}/{self.cycles}: Screen ON", "info")
                
                # Turn screen on
                success = adb.execute_command(device, "input keyevent KEYCODE_WAKEUP")
                if not success:
                    log_callback("❌ Failed to turn screen on", "error")
                    return False
                
                # Wait for on duration
                for i in range(self.on_duration):
                    if not self.is_running:
                        return False
                    time.sleep(1)
                    if progress_callback:
                        sub_progress = int((i / self.on_duration) * 50)
                        progress_callback(progress + sub_progress, f"Cycle {cycle + 1}/{self.cycles} - Screen ON ({i+1}s)")
                
                log_callback(f"📱 Cycle {cycle + 1}/{self.cycles}: Screen OFF", "info")
                
                # Turn screen off
                success = adb.execute_command(device, "input keyevent KEYCODE_POWER")
                if not success:
                    log_callback("❌ Failed to turn screen off", "error")
                    return False
                
                # Wait for off duration (except last cycle)
                if cycle < self.cycles - 1:
                    for i in range(self.off_duration):
                        if not self.is_running:
                            return False
                        time.sleep(1)
                        if progress_callback:
                            sub_progress = int((i / self.off_duration) * 50)
                            progress_callback(progress + 50 + sub_progress, f"Cycle {cycle + 1}/{self.cycles} - Screen OFF ({i+1}s)")
            
            if progress_callback:
                progress_callback(100, "Test completed")
            log_callback(f"✅ {self.name} completed successfully", "success")
            return True
            
        except Exception as e:
            log_callback(f"❌ Test failed: {e}", "error")
            return False
        finally:
            self.is_running = False

class CPUStressTest(TestScenario):
    """CPU stress test scenario"""
    
    def __init__(self, duration: int = 60):
        super().__init__(
            "CPU Stress Test", 
            f"Run CPU stress test for {duration} seconds"
        )
        self.duration = duration
        
    def execute(self, device: str, log_callback: Callable, progress_callback: Callable = None) -> bool:
        """Execute CPU stress test"""
        self.is_running = True
        
        try:
            log_callback(f"🔥 Starting {self.name} - {self.duration}s", "info")
            
            # Start CPU stress (using a simple busy loop command)
            stress_cmd = "while true; do echo 'stress' > /dev/null; done &"
            success = adb.execute_command(device, f"sh -c '{stress_cmd}'")
            
            if not success:
                log_callback("❌ Failed to start CPU stress", "error")
                return False
            
            # Monitor for duration
            for i in range(self.duration):
                if not self.is_running:
                    # Kill stress processes
                    adb.execute_command(device, "pkill -f 'stress'")
                    log_callback("⏹️ CPU stress test stopped", "warn")
                    return False
                    
                time.sleep(1)
                if progress_callback:
                    progress = int((i / self.duration) * 100)
                    progress_callback(progress, f"CPU Stress: {i+1}s/{self.duration}s")
            
            # Stop stress test
            adb.execute_command(device, "pkill -f 'stress'")
            
            if progress_callback:
                progress_callback(100, "CPU stress test completed")
            log_callback(f"✅ {self.name} completed successfully", "success")
            return True
            
        except Exception as e:
            log_callback(f"❌ CPU stress test failed: {e}", "error")
            return False
        finally:
            self.is_running = False

class CustomScriptTest(TestScenario):
    """Custom ADB script test scenario"""
    
    def __init__(self, script_commands: list, name: str = "Custom Script Test"):
        super().__init__(name, f"Execute custom ADB commands: {len(script_commands)} commands")
        self.script_commands = script_commands
        
    def execute(self, device: str, log_callback: Callable, progress_callback: Callable = None) -> bool:
        """Execute custom script commands"""
        self.is_running = True
        
        try:
            log_callback(f"🔧 Starting {self.name} - {len(self.script_commands)} commands", "info")
            
            for i, command in enumerate(self.script_commands):
                if not self.is_running:
                    log_callback("⏹️ Custom script stopped by user", "warn")
                    return False
                
                # Update progress
                if progress_callback:
                    progress = int((i / len(self.script_commands)) * 100)
                    progress_callback(progress, f"Executing command {i + 1}/{len(self.script_commands)}")
                
                command = command.strip()
                if not command or command.startswith('#'):
                    continue  # Skip empty lines and comments
                
                log_callback(f"📱 Executing: {command}", "info")
                
                # Handle special commands
                if command.startswith('sleep '):
                    try:
                        sleep_time = int(command.split()[1])
                        for s in range(sleep_time):
                            if not self.is_running:
                                return False
                            time.sleep(1)
                            if progress_callback:
                                sub_progress = int((s / sleep_time) * (100 / len(self.script_commands)))
                                progress_callback(progress + sub_progress, f"Sleeping... {s+1}s/{sleep_time}s")
                    except (ValueError, IndexError):
                        log_callback(f"❌ Invalid sleep command: {command}", "error")
                        continue
                else:
                    # Execute ADB command
                    success = adb.execute_command(device, command)
                    if not success:
                        log_callback(f"❌ Command failed: {command}", "error")
                        return False
                
                # Small delay between commands
                time.sleep(0.5)
            
            if progress_callback:
                progress_callback(100, "Custom script completed")
            log_callback(f"✅ {self.name} completed successfully", "success")
            return True
            
        except Exception as e:
            log_callback(f"❌ Custom script failed: {e}", "error")
            return False
        finally:
            self.is_running = False

class AutoTestService(QObject):
    """Service for managing automated tests with HVPM monitoring"""
    
    # Signals for UI updates
    progress_updated = pyqtSignal(int, str)  # progress, status
    test_completed = pyqtSignal(bool, str)   # success, message
    voltage_stabilized = pyqtSignal(float)   # voltage
    
    def __init__(self, hvpm_service, log_callback: Callable):
        super().__init__()
        self.hvpm_service = hvpm_service
        self.log_callback = log_callback
        
        # Test configuration
        self.stabilization_voltage = 4.8  # V
        self.test_voltage = 4.0  # V
        self.stabilization_time = 10  # seconds
        
        # Available test scenarios
        self.scenarios = {
            "screen_onoff": ScreenOnOffTest(cycles=5, on_duration=10, off_duration=5),
            "screen_onoff_long": ScreenOnOffTest(cycles=10, on_duration=15, off_duration=10),
            "cpu_stress": CPUStressTest(duration=60),
            "cpu_stress_long": CPUStressTest(duration=300),
            "custom_script": None,  # Will be created dynamically
        }
        
        # Test state
        self.current_test = None
        self.is_running = False
        self.test_thread = None
        self.selected_device = None
        
        # Connect signals
        self.progress_updated.connect(self._on_progress_updated)
        self.test_completed.connect(self._on_test_completed)
        
    def get_available_scenarios(self) -> Dict[str, TestScenario]:
        """Get available test scenarios"""
        return self.scenarios.copy()
    
    def set_voltages(self, stabilization_voltage: float, test_voltage: float):
        """Set voltage configuration"""
        self.stabilization_voltage = stabilization_voltage
        self.test_voltage = test_voltage
        self.log_callback(f"⚙️ Voltage config: Stabilization={stabilization_voltage}V, Test={test_voltage}V", "info")
    
    def set_device(self, device: str):
        """Set target ADB device"""
        self.selected_device = device
        self.log_callback(f"📱 Target device set: {device}", "info")
    
    def start_test(self, scenario_key: str, custom_script: str = None) -> bool:
        """Start automated test"""
        if self.is_running:
            self.log_callback("⚠️ Test already running", "warn")
            return False
            
        if not self.selected_device:
            self.log_callback("❌ No ADB device selected", "error")
            return False
            
        if not self.hvpm_service.is_connected():
            self.log_callback("❌ HVPM not connected", "error")
            return False
            
        if scenario_key not in self.scenarios:
            self.log_callback(f"❌ Unknown test scenario: {scenario_key}", "error")
            return False
        
        # Handle custom script scenario
        if scenario_key == "custom_script":
            if not custom_script or not custom_script.strip():
                self.log_callback("❌ Custom script is empty", "error")
                return False
            
            # Parse script commands
            commands = [cmd.strip() for cmd in custom_script.split('\n') if cmd.strip()]
            if not commands:
                self.log_callback("❌ No valid commands in custom script", "error")
                return False
            
            self.current_test = CustomScriptTest(commands)
        else:
            self.current_test = self.scenarios[scenario_key]
        
        self.is_running = True
        
        # Start test in separate thread
        self.test_thread = threading.Thread(target=self._run_test, daemon=True)
        self.test_thread.start()
        
        self.log_callback(f"🚀 Starting automated test: {self.current_test.name}", "info")
        return True
    
    def stop_test(self):
        """Stop current test"""
        if not self.is_running:
            return
            
        self.log_callback("⏹️ Stopping automated test...", "warn")
        self.is_running = False
        
        if self.current_test:
            self.current_test.stop()
            
        # Wait for thread to finish
        if self.test_thread and self.test_thread.is_alive():
            self.test_thread.join(timeout=5)
    
    def _run_test(self):
        """Run the complete test sequence"""
        try:
            # Phase 1: Voltage stabilization
            self.progress_updated.emit(0, "Initializing voltage stabilization...")
            
            if not self._stabilize_voltage():
                self.test_completed.emit(False, "Voltage stabilization failed")
                return
            
            # Phase 2: Set test voltage
            self.progress_updated.emit(20, f"Setting test voltage: {self.test_voltage}V")
            
            if not self._set_test_voltage():
                self.test_completed.emit(False, "Failed to set test voltage")
                return
            
            # Phase 3: Execute test scenario
            self.progress_updated.emit(30, f"Executing test: {self.current_test.name}")
            
            success = self.current_test.execute(
                self.selected_device,
                self.log_callback,
                self._on_test_progress
            )
            
            if success:
                self.test_completed.emit(True, f"Test '{self.current_test.name}' completed successfully")
            else:
                self.test_completed.emit(False, f"Test '{self.current_test.name}' failed")
                
        except Exception as e:
            self.log_callback(f"❌ Test execution error: {e}", "error")
            self.test_completed.emit(False, f"Test execution error: {e}")
        finally:
            self.is_running = False
    
    def _stabilize_voltage(self) -> bool:
        """Stabilize voltage before test"""
        try:
            # Set stabilization voltage
            self.log_callback(f"⚡ Setting stabilization voltage: {self.stabilization_voltage}V", "info")
            success = self.hvpm_service.set_voltage(self.stabilization_voltage, self.log_callback)
            
            if not success:
                return False
            
            # Wait for stabilization
            self.log_callback(f"⏳ Waiting {self.stabilization_time}s for voltage stabilization...", "info")
            
            for i in range(self.stabilization_time):
                if not self.is_running:
                    return False
                    
                time.sleep(1)
                progress = 5 + int((i / self.stabilization_time) * 15)  # 5-20%
                self.progress_updated.emit(progress, f"Stabilizing voltage... {i+1}s/{self.stabilization_time}s")
            
            # Verify voltage
            actual_voltage = self.hvpm_service.read_voltage(self.log_callback)
            if actual_voltage is not None:
                self.voltage_stabilized.emit(actual_voltage)
                self.log_callback(f"✅ Voltage stabilized at {actual_voltage:.2f}V", "success")
                return True
            else:
                self.log_callback("❌ Failed to read stabilized voltage", "error")
                return False
                
        except Exception as e:
            self.log_callback(f"❌ Voltage stabilization error: {e}", "error")
            return False
    
    def _set_test_voltage(self) -> bool:
        """Set test voltage"""
        try:
            self.log_callback(f"⚡ Setting test voltage: {self.test_voltage}V", "info")
            success = self.hvpm_service.set_voltage(self.test_voltage, self.log_callback)
            
            if success:
                # Brief wait for voltage to settle
                time.sleep(2)
                actual_voltage = self.hvpm_service.read_voltage(self.log_callback)
                if actual_voltage is not None:
                    self.log_callback(f"✅ Test voltage set: {actual_voltage:.2f}V", "success")
                    return True
            
            return False
            
        except Exception as e:
            self.log_callback(f"❌ Test voltage setting error: {e}", "error")
            return False
    
    def _on_test_progress(self, progress: int, status: str):
        """Handle test scenario progress updates"""
        # Map test progress to overall progress (30-100%)
        overall_progress = 30 + int((progress / 100) * 70)
        self.progress_updated.emit(overall_progress, status)
    
    def _on_progress_updated(self, progress: int, status: str):
        """Handle progress updates (for logging)"""
        self.log_callback(f"📊 Progress: {progress}% - {status}", "info")
    
    def _on_test_completed(self, success: bool, message: str):
        """Handle test completion"""
        level = "success" if success else "error"
        self.log_callback(f"🏁 Test completed: {message}", level)
        self.is_running = False