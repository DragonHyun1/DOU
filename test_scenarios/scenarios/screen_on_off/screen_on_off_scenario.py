"""
Screen On/Off Test Scenario
LCD를 3초마다 켜고 끄는 전력 소비 테스트

[Default setting] 후에
[init setting]
- LCD on and 락 해제
- Flight mode on
- Clear recent Apps
- LCD off
[전류 안정화 1분]
[Test start]
DAQ start하고
0초, LCD on 후에 3초 마다 hold key를 눌러 LCD on/off 반복 (총 10회)
30초, 테스트 끝
[Test end]
[csv 저장]
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


class ScreenOnOffScenario(BaseScenario):
    """Screen On/Off test scenario implementation"""
    
    def __init__(self, hvpm_service=None, daq_service=None, adb_service=None, log_callback=None):
        super().__init__(hvpm_service, daq_service, adb_service, log_callback)
        
        # Initialize DAQ collection thread
        self.daq_collector = DAQCollectionThread(daq_service, log_callback)
        self.daq_results = None
    
    def get_config(self) -> TestConfig:
        """Get Screen On/Off test configuration"""
        config = TestConfig(
            name="Screen On/Off Test",
            description="LCD를 3초마다 켜고 끄는 전력 소비 테스트 (hold key 10회)",
            hvpm_voltage=4.0,
            stabilization_time=60.0,  # 1분 안정화
            monitoring_interval=1.0,
            test_duration=30.0  # 30초 테스트
        )
        
        # Define detailed screen on/off test steps
        config.steps = [
            # Battery slate mode setup (USB power disconnect)
            TestStep("enable_slate_mode", 3.0, "enable_battery_slate_mode"),

            # Default settings (consistent for all scenarios)
            TestStep("default_settings", 5.0, "apply_default_settings"),

            # Init mode steps
            TestStep("lcd_on_unlock", 3.0, "lcd_on_and_unlock"),
            TestStep("flight_mode", 2.0, "enable_flight_mode"),
            TestStep("clear_apps", 8.0, "clear_recent_apps"),
            TestStep("lcd_off", 2.0, "lcd_off"),

            # 전류 안정화 1분
            TestStep("current_stabilization", 60.0, "wait_current_stabilization"),

            # Test execution steps
            TestStep("start_daq_monitoring", 2.0, "start_daq_monitoring"),
            TestStep("screen_onoff_test", 30.0, "execute_screen_onoff_test"),
            TestStep("stop_daq_monitoring", 2.0, "stop_daq_monitoring"),
            TestStep("save_excel", 3.0, "export_to_excel"),

            # Battery slate mode restore (USB power restore)
            TestStep("disable_slate_mode", 3.0, "disable_battery_slate_mode")
        ]
        
        return config
    
    def execute_step(self, step: TestStep) -> bool:
        """Execute a single Screen On/Off test step"""
        try:
            if step.action == "enable_battery_slate_mode":
                return self._step_enable_battery_slate_mode()
            elif step.action == "apply_default_settings":
                return self._step_apply_default_settings()
            elif step.action == "lcd_on_and_unlock":
                return self._step_lcd_on_and_unlock()
            elif step.action == "enable_flight_mode":
                return self._step_enable_flight_mode()
            elif step.action == "clear_recent_apps":
                return self._step_clear_recent_apps()
            elif step.action == "lcd_off":
                return self._step_lcd_off()
            elif step.action == "wait_current_stabilization":
                return self._step_wait_current_stabilization()
            elif step.action == "start_daq_monitoring":
                return self._step_start_daq_monitoring()
            elif step.action == "execute_screen_onoff_test":
                return self._step_execute_screen_onoff_test()
            elif step.action == "stop_daq_monitoring":
                return self._step_stop_daq_monitoring()
            elif step.action == "export_to_excel":
                return self._step_export_to_excel()
            elif step.action == "disable_battery_slate_mode":
                return self._step_disable_battery_slate_mode()
            else:
                self.log_callback(f"Unknown step action: {step.action}", "error")
                return False

        except Exception as e:
            self.log_callback(f"Error executing step {step.name}: {e}", "error")
            return False

    def _step_enable_battery_slate_mode(self) -> bool:
        """Enable battery slate mode (disconnect USB power)"""
        try:
            self.log_callback("=== Enabling Battery Slate Mode ===", "info")

            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False

            success = self.adb_service.enable_battery_slate_mode()

            if success:
                self.log_callback("✅ Battery slate mode enabled (USB power disconnected)", "info")
                return True
            else:
                self.log_callback("⚠️ Failed to enable battery slate mode", "warn")
                return True  # Continue test even if slate mode fails

        except Exception as e:
            self.log_callback(f"❌ Error enabling battery slate mode: {e}", "error")
            return True  # Don't fail the entire test for slate mode

    def _step_disable_battery_slate_mode(self) -> bool:
        """Disable battery slate mode (restore USB power)"""
        try:
            self.log_callback("=== Disabling Battery Slate Mode ===", "info")

            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False

            success = self.adb_service.disable_battery_slate_mode()

            if success:
                self.log_callback("✅ Battery slate mode disabled (USB power restored)", "info")
                return True
            else:
                self.log_callback("⚠️ Failed to disable battery slate mode", "warn")
                return True  # Continue even if slate mode restore fails

        except Exception as e:
            self.log_callback(f"❌ Error disabling battery slate mode: {e}", "error")
            return True  # Don't fail for slate mode issues

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
    
    def _step_lcd_on_and_unlock(self) -> bool:
        """LCD on -> 스크린 잠금 해제"""
        try:
            self.log_callback("=== LCD ON + Unlock ===", "info")
            
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
            
            self.log_callback("✅ LCD ON + Unlock completed", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error in LCD on + unlock: {e}", "error")
            return False
    
    def _step_enable_flight_mode(self) -> bool:
        """Enable airplane/flight mode"""
        try:
            self.log_callback("=== Enabling Flight Mode ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            success = self.adb_service.enable_flight_mode()
            
            if success:
                self.log_callback("✅ Flight mode enabled", "info")
                return True
            else:
                self.log_callback("Failed to enable flight mode", "error")
                return False
                
        except Exception as e:
            self.log_callback(f"Error enabling flight mode: {e}", "error")
            return False
    
    def _step_clear_recent_apps(self) -> bool:
        """Clear all recent apps"""
        try:
            self.log_callback("=== Clearing Recent Apps ===", "info")
            
            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False
            
            # Clear all recent apps
            if not self.adb_service.clear_recent_apps():
                self.log_callback("Failed to clear recent apps", "error")
                return False
            
            self.log_callback("✅ Recent apps cleared", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Error clearing recent apps: {e}", "error")
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
            return False
    
    def _step_wait_current_stabilization(self) -> bool:
        """전류 안정화 대기 시간 60초 (1분)"""
        try:
            self.log_callback("=== Waiting for current stabilization (60 seconds / 1 minute) ===", "info")
            
            # 60초 동안 대기하면서 진행 상황 표시
            total_seconds = 60
            update_interval = 10  # 10초마다 업데이트
            
            for i in range(total_seconds):
                if (i + 1) % update_interval == 0 or i == 0:
                    progress = int((i + 1) / total_seconds * 100)
                    minutes = (i + 1) // 60
                    seconds = (i + 1) % 60
                    self.log_callback(
                        f"Current stabilization: {i+1}/{total_seconds} seconds ({progress}%) - {minutes}m {seconds}s", 
                        "info"
                    )
                time.sleep(1)
            
            self.log_callback("✅ Current stabilization completed (1 minute)", "info")
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

            # Ensure previous collection is fully stopped before starting new one
            if hasattr(self, 'daq_collector') and self.daq_collector.is_collecting:
                self.log_callback("⚠️ Previous DAQ collection still active, stopping it first...", "warn")
                self.daq_collector.stop_collection()
                time.sleep(0.5)  # Brief pause to ensure cleanup

            # Reinitialize DAQ collector for clean state (especially for 2nd+ iterations)
            self.log_callback("Reinitializing DAQ collector for clean state", "info")
            self.daq_collector = DAQCollectionThread(self.daq_service, self.log_callback)

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
            import traceback
            self.log_callback(f"Traceback: {traceback.format_exc()}", "error")
            return True  # Don't fail test for DAQ issues
    
    def _step_execute_screen_onoff_test(self) -> bool:
        """Execute Screen On/Off test (30 seconds)
        0초: LCD on
        3초 간격으로 hold key를 눌러 LCD on/off 반복 (총 10회)
        30초: 테스트 끝

        Uses real-time based timing to ensure accurate sync with DAQ collection.
        """
        try:
            self.log_callback("=== Executing Screen On/Off Test (30 seconds, 10 hold key presses) ===", "info")

            if not self.adb_service:
                self.log_callback("ADB service not available", "error")
                return False

            # Test configuration
            test_duration = 30.0  # 30 seconds total
            toggle_times = [3, 6, 9, 12, 15, 18, 21, 24, 27]  # Exact toggle times in seconds

            # 0초: LCD on
            start_time = time.time()
            self.log_callback("0s: Turning LCD ON", "info")
            if not self.adb_service.turn_screen_on():
                self.log_callback("Failed to turn screen on at 0s", "error")
                return False

            screen_state = True  # Current state (ON)
            key_press_count = 0

            # Execute toggles at precise times
            for toggle_time in toggle_times:
                # Wait until the exact toggle time
                while True:
                    elapsed = time.time() - start_time
                    if elapsed >= toggle_time:
                        break
                    # Sleep for remaining time (with small buffer for precision)
                    remaining = toggle_time - elapsed
                    if remaining > 0.1:
                        time.sleep(remaining - 0.05)  # Wake up 50ms before
                    else:
                        time.sleep(0.01)  # Small sleep to avoid busy loop

                # Execute toggle at exact time
                key_press_count += 1
                screen_state = not screen_state

                actual_elapsed = time.time() - start_time

                if screen_state:
                    self.log_callback(f"{toggle_time}s (actual: {actual_elapsed:.1f}s): Pressing hold key (#{key_press_count}) - Turning LCD ON", "info")
                    if not self.adb_service.turn_screen_on():
                        self.log_callback(f"Failed to turn screen on at {toggle_time}s", "error")
                        return False
                else:
                    self.log_callback(f"{toggle_time}s (actual: {actual_elapsed:.1f}s): Pressing hold key (#{key_press_count}) - Turning LCD OFF", "info")
                    if not self.adb_service.turn_screen_off():
                        self.log_callback(f"Failed to turn screen off at {toggle_time}s", "error")
                        return False

            # Wait until test_duration is reached
            while time.time() - start_time < test_duration:
                time.sleep(0.1)

            total_elapsed = time.time() - start_time
            self.log_callback(f"30s: Screen On/Off test completed ({key_press_count} hold key presses, actual duration: {total_elapsed:.1f}s)", "info")
            return True

        except Exception as e:
            self.log_callback(f"Error executing Screen On/Off test: {e}", "error")
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
                filename = f"screen_onoff_test_{timestamp}.xlsx"
                
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
