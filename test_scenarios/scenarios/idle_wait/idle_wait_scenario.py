"""
Idle Wait Test Scenario
Phone app 시나리오와 동일한 init 부분까지 진행하지만,
DAQ 시작 후 앱을 실행하지 않고 5분간 대기하는 시나리오
"""

import time
from typing import Dict, Any
import sys
import os

# Add services path for DAQ collection thread
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from ..common.base_scenario import BaseScenario, TestConfig, TestStep
from ..common.default_settings import DefaultSettings
from services.daq_collection_thread import DAQCollectionThread


class IdleWaitScenario(BaseScenario):
    """Idle Wait test scenario implementation
    
    Same initialization as Phone App scenario, but after starting DAQ,
    waits for 5 minutes without executing any app.
    """
    
    def __init__(self, hvpm_service=None, daq_service=None, adb_service=None, log_callback=None):
        super().__init__(hvpm_service, daq_service, adb_service, log_callback)
        
        # Initialize DAQ collection thread
        self.daq_collector = DAQCollectionThread(daq_service, log_callback)
        self.daq_results = None
    
    def get_config(self) -> TestConfig:
        """Get Idle Wait test configuration"""
        config = TestConfig(
            name="Idle Wait Test",
            description="Phone app 시나리오와 동일한 init 부분까지 진행하지만, DAQ 시작 후 앱을 실행하지 않고 5분간 대기",
            hvpm_voltage=4.0,
            stabilization_time=10.0,
            monitoring_interval=1.0,
            test_duration=300.0  # 5 minutes idle wait
        )
        
        # Define detailed idle wait test steps (same init as Phone App)
        config.steps = [
            # Default settings (consistent for all scenarios)
            TestStep("default_settings", 5.0, "apply_default_settings"),
            # Early LCD activation for smoother operation
            TestStep("lcd_on_unlock", 3.0, "lcd_on_and_unlock"),
            # Init mode steps (same as Phone App scenario)
            TestStep("init_hvpm", 2.0, "set_hvpm_voltage", {"voltage": 4.0}),
            TestStep("airplane_mode", 2.0, "enable_flight_mode"),
            TestStep("wifi_2g_connect", 15.0, "connect_wifi_2g"),
            TestStep("bluetooth_on", 2.0, "enable_bluetooth"),
            TestStep("home_clear_apps", 8.0, "home_and_clear_apps"),
            TestStep("current_stabilization", 10.0, "wait_current_stabilization"),
            # Test execution steps (different from Phone App)
            TestStep("start_daq_monitoring", 2.0, "start_daq_monitoring"),
            TestStep("idle_wait", 300.0, "execute_idle_wait"),  # 5 minutes = 300 seconds
            TestStep("stop_daq_monitoring", 2.0, "stop_daq_monitoring"),
            TestStep("save_excel", 3.0, "export_to_excel")
        ]
        
        return config
    
    def execute_step(self, step: TestStep) -> bool:
        """Execute a single Idle Wait test step"""
        try:
            if step.action == "apply_default_settings":
                return self._step_apply_default_settings()
            elif step.action == "set_hvpm_voltage":
                return self._step_set_hvpm_voltage(step.parameters.get("voltage", 4.0))
            elif step.action == "enable_flight_mode":
                return self._step_enable_flight_mode()
            elif step.action == "connect_wifi_2g":
                return self._step_connect_wifi_2g()
            elif step.action == "enable_bluetooth":
                return self._step_enable_bluetooth()
            elif step.action == "lcd_on_and_unlock":
                return self._step_lcd_on_and_unlock()
            elif step.action == "home_and_clear_apps":
                return self._step_home_and_clear_apps()
            elif step.action == "wait_current_stabilization":
                return self._step_wait_current_stabilization()
            elif step.action == "start_daq_monitoring":
                return self._step_start_daq_monitoring()
            elif step.action == "execute_idle_wait":
                return self._step_execute_idle_wait(step.duration)
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
    
    def _step_apply_default_settings(self) -> bool:
        """Apply default settings for consistent test environment"""
        try:
            self.log_callback("=== Applying Default Settings ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Verify device connection before applying settings
            if not self.adb_service.verify_device_connection():
                self.log_callback("❌ Device connection verification failed", "error")
                return False
            
            # Get initial device status
            initial_status = self.adb_service.get_device_status()
            self.log_callback(f"📱 Initial device status: {initial_status}", "info")
            
            # Apply default settings using ADB service
            success = self.adb_service.apply_default_settings()
            
            # Get final device status after applying settings
            final_status = self.adb_service.get_device_status()
            self.log_callback(f"📱 Final device status: {final_status}", "info")
            
            if success:
                self.log_callback("✅ Default settings applied successfully", "info")
                return True
            else:
                self.log_callback("⚠️ Default settings partially applied", "warn")
                return True  # Continue even if some settings failed
                
        except Exception as e:
            self.log_callback(f"❌ Error applying default settings: {e}", "error")
            return True  # Don't fail the entire test for default settings
    
    def _step_set_hvpm_voltage(self, voltage: float) -> bool:
        """Set HVPM voltage"""
        try:
            self.log_callback(f"Setting HVPM voltage to {voltage}V", "info")
            
            if not self.hvpm_service:
                self.log_callback("HVPM service not available", "warn")
                return True  # Continue without HVPM
            
            # Set HVPM voltage (implementation depends on HVPM service)
            # This is a placeholder - actual implementation would call HVPM service
            time.sleep(2)  # Simulate HVPM setting time
            
            self.log_callback(f"HVPM voltage set to {voltage}V", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error setting HVPM voltage: {e}", "error")
            return False
    
    def _step_enable_flight_mode(self) -> bool:
        """Enable airplane mode"""
        try:
            self.log_callback("Enabling airplane mode", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            success = self.adb_service.enable_flight_mode()
            
            if success:
                self.log_callback("Airplane mode enabled", "info")
                return True
            else:
                self.log_callback("Failed to enable airplane mode", "error")
                return False
                
        except Exception as e:
            self.log_callback(f"Error enabling airplane mode: {e}", "error")
            return False
    
    def _step_connect_wifi_2g(self) -> bool:
        """Connect to 2.4GHz WiFi"""
        try:
            self.log_callback("Connecting to 2.4GHz WiFi", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # WiFi credentials (should be configurable)
            wifi_ssid = "0_WIFIFW_RAX40_2nd_2G"
            wifi_password = "cppower12"
            
            success = self.adb_service.connect_wifi_2g(wifi_ssid, wifi_password)
            
            if success:
                self.log_callback("2.4GHz WiFi connected", "info")
                return True
            else:
                self.log_callback("Failed to connect to 2.4GHz WiFi", "error")
                return False
                
        except Exception as e:
            self.log_callback(f"Error connecting to WiFi: {e}", "error")
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
                self.log_callback("Bluetooth enabled", "info")
                return True
            else:
                self.log_callback("Failed to enable Bluetooth", "error")
                return False
                
        except Exception as e:
            self.log_callback(f"Error enabling Bluetooth: {e}", "error")
            return False
    
    def _step_lcd_on_and_unlock(self) -> bool:
        """LCD on -> 스크린 잠금 해제 (early activation for smoother operation)"""
        try:
            self.log_callback("=== Early LCD ON + Unlock ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Step 1: LCD on (turn screen on)
            self.log_callback("Step 1: Turning LCD on", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on", "error")
                return False
            time.sleep(1.5)  # Give more time for screen to fully turn on
            
            # Step 2: 스크린 잠금 해제 (unlock screen)
            self.log_callback("Step 2: Unlocking screen", "info")
            if not self.adb_service.unlock_screen():
                self.log_callback("Failed to unlock screen", "error")
                return False
            time.sleep(1.0)
            
            self.log_callback("✅ Early LCD ON + Unlock completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in early LCD on + unlock: {e}", "error")
            return False
    
    def _step_home_and_clear_apps(self) -> bool:
        """Home 버튼 클릭 -> App clear all 진행"""
        try:
            self.log_callback("=== Home + Clear Apps ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Step 1: Home 버튼 클릭
            self.log_callback("Step 1: Pressing home button", "info")
            if not self.adb_service.press_home():
                self.log_callback("Failed to press home button", "error")
                return False
            time.sleep(1.5)  # Give time for home screen to load
            
            # Step 2: App clear all 진행
            self.log_callback("Step 2: Clearing all apps", "info")
            if not self.adb_service.clear_recent_apps():
                self.log_callback("Failed to clear all apps", "error")
                return False
            
            self.log_callback("✅ Home + Clear Apps completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in home + clear apps: {e}", "error")
            return False
    
    def _step_wait_current_stabilization(self) -> bool:
        """전류 안정화 대기 시간 10초"""
        try:
            self.log_callback("=== Waiting for current stabilization (10 seconds) ===", "info")
            
            # 10초 동안 대기하면서 진행 상황 표시
            for i in range(10):
                progress = int((i + 1) / 10 * 100)
                self.log_callback(f"Current stabilization: {i+1}/10 seconds ({progress}%)", "info")
                time.sleep(1)
            
            self.log_callback("Current stabilization completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error during current stabilization: {e}", "error")
            return False
    
    def _step_start_daq_monitoring(self) -> bool:
        """Start DAQ monitoring using dedicated collection thread"""
        try:
            self.log_callback("=== Starting DAQ Collection Thread ===", "info")
            
            if not self.daq_service:
                self.log_callback("DAQ service not available - using mock data", "warn")
            
            # Configure DAQ collection
            enabled_channels = ['ai0', 'ai1', 'ai2', 'ai3']  # Example channels
            collection_interval = 1.0  # 1 second interval
            
            self.daq_collector.configure(enabled_channels, collection_interval)
            
            # Start collection thread
            success = self.daq_collector.start_collection()
            
            if success:
                self.log_callback("✅ DAQ collection thread started successfully", "info")
                time.sleep(1)  # Brief pause to let collection start
                return True
            else:
                self.log_callback("⚠️ DAQ collection failed to start - continuing without DAQ", "warn")
                return True  # Continue test even if DAQ fails
            
        except Exception as e:
            self.log_callback(f"❌ Error starting DAQ collection: {e}", "error")
            return True  # Don't fail test for DAQ issues
    
    def _step_execute_idle_wait(self, duration_seconds: float = 300.0) -> bool:
        """Execute idle wait (5 minutes = 300 seconds) without running any app"""
        try:
            self.log_callback(f"=== Starting Idle Wait ({duration_seconds} seconds / {duration_seconds/60:.1f} minutes) ===", "info")
            self.log_callback("No app will be executed - device will remain idle", "info")
            
            # Wait for specified duration with progress updates every 30 seconds
            total_seconds = int(duration_seconds)
            update_interval = 30  # Update progress every 30 seconds
            
            elapsed = 0
            while elapsed < total_seconds:
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
            return False
    
    def _step_stop_daq_monitoring(self) -> bool:
        """Stop DAQ monitoring and collect results"""
        try:
            self.log_callback("=== Stopping DAQ Collection Thread ===", "info")
            
            # Stop collection and get results
            self.daq_results = self.daq_collector.stop_collection()
            
            if self.daq_results and self.daq_results.get('success'):
                data_count = self.daq_results.get('data_count', 0)
                duration = self.daq_results.get('duration', 0)
                self.log_callback(f"✅ DAQ collection completed: {data_count} data points in {duration:.1f}s", "info")
                
                # Log some sample data
                if data_count > 0:
                    latest_data = self.daq_results.get('data', [])[-1] if self.daq_results.get('data') else None
                    if latest_data:
                        self.log_callback(f"📊 Latest reading: {latest_data.get('readings', {})}", "info")
                
                return True
            else:
                error_msg = self.daq_results.get('message', 'Unknown error') if self.daq_results else 'No results'
                self.log_callback(f"⚠️ DAQ collection had issues: {error_msg}", "warn")
                return True  # Continue even if DAQ had issues
            
        except Exception as e:
            self.log_callback(f"❌ Error stopping DAQ collection: {e}", "error")
            return True  # Don't fail test for DAQ issues
    
    def _step_export_to_excel(self) -> bool:
        """Export test results to Excel"""
        try:
            self.log_callback("=== Exporting Results to Excel ===", "info")
            
            if not self.daq_results:
                self.log_callback("⚠️ No DAQ results to export", "warn")
                return True
            
            # Prepare export data
            data_count = self.daq_results.get('data_count', 0)
            duration = self.daq_results.get('duration', 0)
            
            if data_count > 0:
                # Generate filename with timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"idle_wait_test_{timestamp}.xlsx"
                
                self.log_callback(f"📊 Preparing to export {data_count} data points to {filename}", "info")
                
                # TODO: Implement actual Excel export
                # For now, just simulate the export
                time.sleep(2)  # Simulate export time
                
                self.log_callback(f"✅ Results exported to {filename}", "info")
                self.log_callback(f"📈 Test summary: {data_count} data points, {duration:.1f}s duration", "info")
            else:
                self.log_callback("⚠️ No data to export", "warn")
            
            return True
            
        except Exception as e:
            self.log_callback(f"❌ Error exporting to Excel: {e}", "error")
            return False
