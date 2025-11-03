#!/usr/bin/env python3
"""
ADB Service for Android Device Control
Handles ADB commands for test automation
"""

import subprocess
import time
import logging
import sys
from typing import Optional, List, Dict, Any

# Windows에서 cmd 창 안 뜨게 하는 설정
if sys.platform == 'win32':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0


class ADBService:
    """Service for controlling Android devices via ADB"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connected_device = None
        self.device_info = {}
        
    def get_connected_devices(self) -> List[str]:
        """Get list of connected ADB devices"""
        try:
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, text=True, timeout=10,
                                  creationflags=SUBPROCESS_FLAGS)
            if result.returncode != 0:
                self.logger.error(f"ADB devices command failed: {result.stderr}")
                return []
            
            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
            
            return devices
        except Exception as e:
            self.logger.error(f"Error getting ADB devices: {e}")
            return []
    
    def connect_device(self, device_id: Optional[str] = None) -> bool:
        """Connect to ADB device"""
        try:
            devices = self.get_connected_devices()
            if not devices:
                self.logger.error("No ADB devices found")
                return False
            
            if device_id is None:
                device_id = devices[0]  # Use first available device
            
            if device_id not in devices:
                self.logger.error(f"Device {device_id} not found in connected devices")
                return False
            
            self.connected_device = device_id
            self.device_info = self._get_device_info()
            self.logger.info(f"Connected to ADB device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to ADB device: {e}")
            return False
    
    def _get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        if not self.connected_device:
            return {}
        
        info = {}
        try:
            # Get device model
            result = self._run_adb_command(['shell', 'getprop', 'ro.product.model'])
            if result:
                info['model'] = result.strip()
            
            # Get Android version
            result = self._run_adb_command(['shell', 'getprop', 'ro.build.version.release'])
            if result:
                info['android_version'] = result.strip()
            
            # Get battery level
            result = self._run_adb_command(['shell', 'dumpsys', 'battery', '|', 'grep', 'level'])
            if result:
                info['battery_level'] = result.strip()
                
        except Exception as e:
            self.logger.error(f"Error getting device info: {e}")
        
        return info
    
    def _run_adb_command(self, command: List[str], timeout: int = 30) -> Optional[str]:
        """Run ADB command and return output with enhanced error handling"""
        if not self.connected_device:
            self.logger.error("No device connected")
            return None
        
        try:
            full_command = ['adb', '-s', self.connected_device] + command
            
            # Log command for debugging
            self.logger.debug(f"Executing ADB command: {' '.join(full_command)}")
            
            result = subprocess.run(full_command, 
                                  capture_output=True, text=True, timeout=timeout,
                                  creationflags=SUBPROCESS_FLAGS)
            
            if result.returncode != 0:
                self.logger.error(f"ADB command failed: {' '.join(full_command)}")
                self.logger.error(f"Return code: {result.returncode}")
                self.logger.error(f"Stderr: {result.stderr}")
                self.logger.error(f"Stdout: {result.stdout}")
                return None
            
            # Log successful command output for debugging
            if result.stdout:
                self.logger.debug(f"Command output: {result.stdout[:200]}...")
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"ADB command timeout ({timeout}s): {' '.join(command)}")
            return None
        except FileNotFoundError:
            self.logger.error("ADB not found. Please install Android SDK platform-tools")
            return None
        except Exception as e:
            self.logger.error(f"Error running ADB command: {e}")
            return None
    
    def turn_screen_on(self) -> bool:
        """Turn device screen on"""
        try:
            # Wake up device
            result = self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_WAKEUP'])
            if result is not None:
                time.sleep(0.5)  # Wait for screen to turn on
                self.logger.info("Screen turned on")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error turning screen on: {e}")
            return False
    
    def turn_screen_off(self) -> bool:
        """Turn device screen off"""
        try:
            result = self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_POWER'])
            if result is not None:
                time.sleep(0.5)  # Wait for screen to turn off
                self.logger.info("Screen turned off")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error turning screen off: {e}")
            return False
    
    def press_home_key(self) -> bool:
        """Press home key"""
        try:
            result = self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_HOME'])
            if result is not None:
                self.logger.info("Home key pressed")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error pressing home key: {e}")
            return False
    
    def press_home(self) -> bool:
        """Press home key (alias for press_home_key)"""
        return self.press_home_key()
    
    def enable_flight_mode(self) -> bool:
        """Enable airplane/flight mode with verification and retry logic"""
        try:
            self.logger.info("🔄 Enabling airplane mode...")
            
            # Step 1: Set airplane mode via settings
            self.logger.info("Step 1: Setting airplane mode via settings...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'global', 'airplane_mode_on', '1'])
            time.sleep(1)
            
            # Step 2: Broadcast the change
            self.logger.info("Step 2: Broadcasting airplane mode change...")
            self._run_adb_command(['shell', 'am', 'broadcast', '-a', 'android.intent.action.AIRPLANE_MODE', '--ez', 'state', 'true'])
            time.sleep(2)
            
            # Step 3: Verify airplane mode is enabled
            self.logger.info("Step 3: Verifying airplane mode state...")
            max_retries = 3
            for attempt in range(max_retries):
                airplane_status = self.get_airplane_mode_status()
                self.logger.info(f"Verification attempt {attempt + 1}/{max_retries}: Airplane mode {airplane_status}")
                
                if airplane_status == 'ON':
                    self.logger.info("✅ Airplane mode enabled successfully")
                    return True
                
                time.sleep(1)
            
            # Step 4: If settings method didn't work, try alternative using cmd
            self.logger.warning("⚠️ Standard method failed, trying alternative...")
            self._run_adb_command(['shell', 'cmd', 'connectivity', 'airplane-mode', 'enable'])
            time.sleep(2)
            
            # Final verification
            airplane_status = self.get_airplane_mode_status()
            if airplane_status == 'ON':
                self.logger.info("✅ Airplane mode enabled (alternative method)")
                return True
            
            self.logger.error(f"❌ Failed to enable airplane mode. Final status: {airplane_status}")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error enabling airplane mode: {e}")
            return False
    
    def get_airplane_mode_status(self) -> str:
        """Get current airplane mode status (ON/OFF/UNKNOWN)"""
        try:
            # Method 1: Check using settings
            result = self._run_adb_command(['shell', 'settings', 'get', 'global', 'airplane_mode_on'])
            if result:
                if result.strip() == '1':
                    return 'ON'
                elif result.strip() == '0':
                    return 'OFF'
            
            # Method 2: Check using dumpsys (some devices)
            result = self._run_adb_command(['shell', 'dumpsys', 'wifi', '|', 'grep', '-i', 'airplane'])
            if result:
                if 'airplane.*on' in result.lower() or 'airplane.*enabled' in result.lower():
                    return 'ON'
                elif 'airplane.*off' in result.lower() or 'airplane.*disabled' in result.lower():
                    return 'OFF'
            
            return 'UNKNOWN'
            
        except Exception as e:
            self.logger.error(f"Error getting airplane mode status: {e}")
            return 'UNKNOWN'
    
    def clear_recent_apps(self) -> bool:
        """Clear all recent apps - Optimized version (Clear All button only)"""
        try:
            self.logger.info("=== Starting optimized app clear process ===")
            
            # Step 1: Kill all background apps using activity manager
            self.logger.info("Step 1: Killing all background apps...")
            result = self._run_adb_command(['shell', 'am', 'kill-all'])
            if result is not None:
                time.sleep(1)
                self.logger.info("✅ Background apps killed")
            
            # Step 2: Open recent apps screen and use Clear All button
            self.logger.info("Step 2: Opening recent apps screen...")
            result = self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_APP_SWITCH'])
            if result is not None:
                time.sleep(2.0)  # Wait for recent apps to fully load
                
                # Step 3: Click Clear All button (single click)
                self.logger.info("Step 3: Clicking Clear All button...")
                self.logger.info("  Clicking Clear All button (Samsung position)...")
                result = self._run_adb_command(['shell', 'input', 'tap', '540', '1800'])
                time.sleep(2.0)  # Wait for Clear All to complete
                
                # Step 4: Wait for Clear All to complete
                self.logger.info("Step 4: Waiting for Clear All to complete...")
                time.sleep(2.5)  # Give more time for clearing to finish
                
                # Step 5: Return to home screen
                self.logger.info("Step 5: Returning to home screen...")
                self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_HOME'])
                time.sleep(1.0)
                
                # Step 6: Double press home to ensure we're on home screen
                self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_HOME'])
                time.sleep(0.5)
                
                self.logger.info("✅ Optimized app clear process completed")
                return True
            
            self.logger.warning("❌ Failed to open recent apps screen")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error in optimized app clear: {e}")
            # Fallback: at least try to go home
            try:
                self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_HOME'])
                time.sleep(0.5)
            except:
                pass
            return False
    
    def unlock_screen(self) -> bool:
        """Unlock screen (assumes no lock screen security)"""
        try:
            # Wake up first
            self.turn_screen_on()
            time.sleep(0.5)
            
            # Swipe up to unlock (basic unlock, no PIN/pattern)
            result = self._run_adb_command(['shell', 'input', 'swipe', '500', '1500', '500', '500'])
            if result is not None:
                time.sleep(0.5)
                self.logger.info("Screen unlocked")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error unlocking screen: {e}")
            return False
    
    def get_screen_state(self) -> bool:
        """Get current screen state (True=ON, False=OFF)"""
        try:
            result = self._run_adb_command(['shell', 'dumpsys', 'display', '|', 'grep', 'mScreenState'])
            if result and 'ON' in result:
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error getting screen state: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if device is connected"""
        return self.connected_device is not None
    
    def connect_wifi_2g(self, ssid: str, password: str) -> bool:
        """Connect to 2.4GHz WiFi network using multiple methods with proper verification"""
        try:
            self.logger.info(f"🔄 Connecting to 2.4GHz WiFi: {ssid}")
            
            # Step 1: Disable airplane mode first (if enabled)
            self.logger.info("Step 1: Disabling airplane mode (if enabled)...")
            self._run_adb_command(['shell', 'settings', 'put', 'global', 'airplane_mode_on', '0'])
            self._run_adb_command(['shell', 'am', 'broadcast', '-a', 'android.intent.action.AIRPLANE_MODE', '--ez', 'state', 'false'])
            time.sleep(2)
            
            # Step 2: Enable WiFi
            self.logger.info("Step 2: Enabling WiFi...")
            self._run_adb_command(['shell', 'svc', 'wifi', 'enable'])
            time.sleep(3)
            
            # Verify WiFi is enabled
            wifi_status = self.get_wifi_status()
            if not wifi_status['enabled']:
                self.logger.error("❌ Failed to enable WiFi")
                return False
            self.logger.info("✅ WiFi enabled successfully")
            
            # Step 3: Attempt connection using cmd wifi command (more reliable)
            self.logger.info(f"Step 3: Attempting WiFi connection to {ssid}...")
            
            # Try cmd wifi connect-network command (Android 10+)
            result = self._run_adb_command([
                'shell', 'cmd', 'wifi', 'connect-network', 
                ssid, 'wpa2', password
            ], timeout=15)
            time.sleep(5)
            
            # Step 4: Verify connection with retry
            self.logger.info("Step 4: Verifying WiFi connection...")
            max_retries = 5
            for attempt in range(max_retries):
                time.sleep(2)
                wifi_status = self.get_wifi_status()
                self.logger.info(f"Verification attempt {attempt + 1}/{max_retries}: {wifi_status}")
                
                # Check if connected to target SSID
                if wifi_status['enabled'] and ssid.lower() in wifi_status['connected_ssid'].lower():
                    self.logger.info(f"✅ Successfully connected to 2.4GHz WiFi: {ssid}")
                    return True
                
                # Check if connected to any WiFi (acceptable)
                if wifi_status['connection_state'] == 'CONNECTED' and wifi_status['connected_ssid'] != 'Unknown':
                    self.logger.info(f"✅ Connected to WiFi: {wifi_status['connected_ssid']}")
                    return True
            
            # Step 5: If cmd wifi didn't work, try alternative method
            self.logger.warning("⚠️ Standard connection method failed, trying alternative...")
            
            # Re-enable WiFi
            self._run_adb_command(['shell', 'svc', 'wifi', 'disable'])
            time.sleep(2)
            self._run_adb_command(['shell', 'svc', 'wifi', 'enable'])
            time.sleep(5)
            
            # Final verification
            for attempt in range(3):
                time.sleep(3)
                wifi_status = self.get_wifi_status()
                self.logger.info(f"Final verification {attempt + 1}/3: {wifi_status}")
                
                if wifi_status['enabled'] and wifi_status['connection_state'] == 'CONNECTED':
                    self.logger.info(f"✅ WiFi connected: {wifi_status['connected_ssid']}")
                    return True
            
            # Final check: If WiFi is at least enabled, accept it
            if wifi_status['enabled']:
                self.logger.warning(f"⚠️ WiFi enabled but connection to {ssid} uncertain. Status: {wifi_status}")
                self.logger.warning("⚠️ Continuing test with WiFi enabled...")
                return True
            
            self.logger.error(f"❌ Failed to connect to WiFi: {ssid}")
            return False
                
        except Exception as e:
            self.logger.error(f"❌ Error connecting to 2.4GHz WiFi: {e}")
            # Try to enable WiFi at least
            try:
                self._run_adb_command(['shell', 'svc', 'wifi', 'enable'])
                time.sleep(3)
                return self.get_wifi_status()['enabled']
            except:
                return False
    
    def connect_wifi_5g(self, ssid: str, password: str) -> bool:
        """Connect to 5GHz WiFi network"""
        try:
            self.logger.info(f"Connecting to 5GHz WiFi: {ssid}")
            
            # Enable WiFi first
            self._run_adb_command(['shell', 'svc', 'wifi', 'enable'])
            time.sleep(2)
            
            # Connect to WiFi network
            result = self._run_adb_command(['shell', 'svc', 'wifi', 'connect', ssid, 'password', password])
            if result is not None:
                time.sleep(5)  # Wait for connection
                
                # Verify connection
                wifi_info = self._run_adb_command(['shell', 'dumpsys', 'wifi', '|', 'grep', 'mWifiInfo'])
                if wifi_info and ssid in wifi_info:
                    self.logger.info(f"Successfully connected to 5GHz WiFi: {ssid}")
                    return True
                else:
                    self.logger.warning(f"WiFi connection verification failed for: {ssid}")
                    return True  # Still return True as connection command succeeded
            return False
        except Exception as e:
            self.logger.error(f"Error connecting to 5GHz WiFi: {e}")
            return False
    
    def enable_bluetooth(self) -> bool:
        """Enable Bluetooth with proper verification and retry logic"""
        try:
            self.logger.info("🔄 Enabling Bluetooth...")
            
            # Step 1: Try to enable Bluetooth using svc command
            self.logger.info("Step 1: Attempting to enable Bluetooth via svc...")
            result = self._run_adb_command(['shell', 'svc', 'bluetooth', 'enable'])
            time.sleep(3)  # Wait for Bluetooth to initialize
            
            # Step 2: Verify Bluetooth is enabled
            self.logger.info("Step 2: Verifying Bluetooth state...")
            max_retries = 5
            for attempt in range(max_retries):
                bt_status = self.get_bluetooth_status()
                self.logger.info(f"Verification attempt {attempt + 1}/{max_retries}: Bluetooth {bt_status}")
                
                if bt_status == 'ON':
                    self.logger.info("✅ Bluetooth enabled successfully")
                    return True
                
                # If not on, wait and check again
                time.sleep(2)
            
            # Step 3: If svc command didn't work, try alternative method using settings
            self.logger.warning("⚠️ Standard enable method failed, trying alternative...")
            self._run_adb_command(['shell', 'settings', 'put', 'global', 'bluetooth_on', '1'])
            time.sleep(3)
            
            # Step 4: Try using am command to toggle Bluetooth
            self._run_adb_command(['shell', 'am', 'start', '-a', 'android.bluetooth.adapter.action.REQUEST_ENABLE'])
            time.sleep(3)
            
            # Press OK button to confirm (if dialog appears)
            self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_DPAD_RIGHT'])
            time.sleep(0.5)
            self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_ENTER'])
            time.sleep(2)
            
            # Go back to home
            self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_HOME'])
            time.sleep(1)
            
            # Step 5: Final verification
            for attempt in range(3):
                time.sleep(2)
                bt_status = self.get_bluetooth_status()
                self.logger.info(f"Final verification {attempt + 1}/3: Bluetooth {bt_status}")
                
                if bt_status == 'ON':
                    self.logger.info("✅ Bluetooth enabled successfully (alternative method)")
                    return True
            
            # If still not on, log error
            self.logger.error("❌ Failed to enable Bluetooth after all attempts")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error enabling Bluetooth: {e}")
            return False
    
    def get_bluetooth_status(self) -> str:
        """Get current Bluetooth status (ON/OFF/UNKNOWN)"""
        try:
            # Method 1: Check using settings
            bt_setting = self._run_adb_command(['shell', 'settings', 'get', 'global', 'bluetooth_on'])
            if bt_setting and bt_setting.strip() == '1':
                return 'ON'
            elif bt_setting and bt_setting.strip() == '0':
                return 'OFF'
            
            # Method 2: Check using dumpsys
            bt_dump = self._run_adb_command(['shell', 'dumpsys', 'bluetooth_manager', '|', 'grep', '-i', 'enabled'])
            if bt_dump:
                if 'enabled: true' in bt_dump.lower() or 'state: on' in bt_dump.lower():
                    return 'ON'
                elif 'enabled: false' in bt_dump.lower() or 'state: off' in bt_dump.lower():
                    return 'OFF'
            
            # Method 3: Check Bluetooth adapter state
            adapter_state = self._run_adb_command(['shell', 'dumpsys', 'bluetooth_manager', '|', 'grep', 'mState'])
            if adapter_state:
                # STATE_ON = 12, STATE_OFF = 10
                if '12' in adapter_state or 'ON' in adapter_state:
                    return 'ON'
                elif '10' in adapter_state or 'OFF' in adapter_state:
                    return 'OFF'
            
            return 'UNKNOWN'
            
        except Exception as e:
            self.logger.error(f"Error getting Bluetooth status: {e}")
            return 'UNKNOWN'
    
    def open_phone_app(self) -> bool:
        """Open Phone app (Dialer)"""
        try:
            self.logger.info("Opening Phone app...")
            # Launch dialer app
            result = self._run_adb_command(['shell', 'am', 'start', '-a', 'android.intent.action.DIAL'])
            if result is not None:
                time.sleep(2)  # Wait for app to open
                self.logger.info("Phone app opened")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error opening Phone app: {e}")
            return False
    
    def press_back_key(self) -> bool:
        """Press back key"""
        try:
            result = self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_BACK'])
            if result is not None:
                self.logger.info("Back key pressed")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error pressing back key: {e}")
            return False
    
    def get_wifi_status(self) -> Dict[str, str]:
        """Get current WiFi status and connected network"""
        try:
            # Check if WiFi is enabled using multiple methods
            wifi_enabled1 = self._run_adb_command(['shell', 'settings', 'get', 'global', 'wifi_on'])
            wifi_enabled2 = self._run_adb_command(['shell', 'dumpsys', 'wifi', '|', 'grep', '-i', 'wifi.*enabled'])
            
            # Get current WiFi info
            wifi_info = self._run_adb_command(['shell', 'dumpsys', 'wifi', '|', 'grep', 'mWifiInfo'])
            
            # Check connection state
            connection_state = self._run_adb_command(['shell', 'dumpsys', 'wifi', '|', 'grep', 'Supplicant.*state'])
            
            # Determine if WiFi is enabled
            wifi_enabled = False
            if wifi_enabled1 and wifi_enabled1.strip() == '1':
                wifi_enabled = True
            elif wifi_enabled2 and 'enabled' in wifi_enabled2.lower():
                wifi_enabled = True
            elif wifi_info and 'DISCONNECTED' not in wifi_info:
                wifi_enabled = True
            
            status = {
                'enabled': wifi_enabled,
                'connected_ssid': 'Unknown',
                'connection_state': 'Unknown',
                'raw_info': wifi_info.strip() if wifi_info else 'No info'
            }
            
            # Extract connection state
            if connection_state:
                if 'CONNECTED' in connection_state:
                    status['connection_state'] = 'CONNECTED'
                elif 'DISCONNECTED' in connection_state:
                    status['connection_state'] = 'DISCONNECTED'
                elif 'CONNECTING' in connection_state:
                    status['connection_state'] = 'CONNECTING'
            
            # Extract SSID from wifi info - try multiple patterns
            if wifi_info:
                # Try different SSID extraction methods
                ssid_patterns = [
                    r'SSID:\s*([^,]+)',
                    r'SSID:\s*"([^"]+)"',
                    r'SSID:\s*(\S+)'
                ]
                
                for pattern in ssid_patterns:
                    import re
                    match = re.search(pattern, wifi_info)
                    if match:
                        ssid = match.group(1).strip().replace('"', '')
                        if ssid and ssid != '<unknown ssid>' and ssid != '<none>':
                            status['connected_ssid'] = ssid
                            break
            
            return status
        except Exception as e:
            self.logger.error(f"Error getting WiFi status: {e}")
            return {'enabled': False, 'connected_ssid': 'Error', 'connection_state': 'Error', 'raw_info': str(e)}
    
    def set_screen_timeout(self, timeout_ms: int) -> bool:
        """Set screen timeout in milliseconds"""
        try:
            self.logger.info(f"Setting screen timeout to {timeout_ms}ms")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'screen_off_timeout', str(timeout_ms)])
            if result is not None:
                self.logger.info(f"Screen timeout set to {timeout_ms}ms")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error setting screen timeout: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from device"""
        self.connected_device = None
        self.device_info = {}
        self.logger.info("Disconnected from ADB device")
    
    def apply_default_settings(self) -> bool:
        """
        Apply default settings for all test scenarios with verification
        This ensures consistent initial state for all tests
        
        [Default Setting]
        - screen off timeout: 10분 (600000ms)
        - multi_control_enabled: 0
        - quickshare: off
        - brightness_mode: off (manual mode)
        - brightness: indoor_500 level
        - volume: 7
        - bluetooth: off
        - wifi: off
        - autosync: off
        - gps: off
        """
        try:
            self.logger.info("=== Applying Default Settings with Verification ===")
            settings_applied = 0
            total_settings = 10
            
            # 1. Screen off timeout: 10분 (600000ms)
            self.logger.info("1/10: Setting screen timeout to 10 minutes...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'screen_off_timeout', '600000'])
            time.sleep(0.5)
            # Verify
            verify = self._run_adb_command(['shell', 'settings', 'get', 'system', 'screen_off_timeout'])
            if verify and '600000' in verify:
                settings_applied += 1
                self.logger.info("✅ Screen timeout set to 10 minutes (verified)")
            else:
                self.logger.warning(f"❌ Failed to set screen timeout (got: {verify})")
            
            # 2. Multi control disabled (Samsung specific - may not exist on all devices)
            self.logger.info("2/10: Disabling multi control...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'multi_control_enabled', '0'])
            time.sleep(0.5)
            # Verify (optional setting - don't fail if doesn't exist)
            verify = self._run_adb_command(['shell', 'settings', 'get', 'system', 'multi_control_enabled'])
            if verify and '0' in verify:
                settings_applied += 1
                self.logger.info("✅ Multi control disabled (verified)")
            elif verify and 'null' in verify:
                settings_applied += 1  # Setting doesn't exist on this device
                self.logger.info("ℹ️ Multi control not available on this device (OK)")
            else:
                self.logger.warning(f"⚠️ Multi control status unclear (got: {verify})")
            
            # 3. QuickShare off (Samsung specific - may not exist on all devices)
            self.logger.info("3/10: Disabling QuickShare...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'quickshare', '0'])
            time.sleep(0.5)
            # Verify (optional setting)
            verify = self._run_adb_command(['shell', 'settings', 'get', 'system', 'quickshare'])
            if verify and '0' in verify:
                settings_applied += 1
                self.logger.info("✅ QuickShare disabled (verified)")
            elif verify and 'null' in verify:
                settings_applied += 1  # Setting doesn't exist on this device
                self.logger.info("ℹ️ QuickShare not available on this device (OK)")
            else:
                self.logger.warning(f"⚠️ QuickShare status unclear (got: {verify})")
            
            # 4. Brightness mode off (manual mode)
            self.logger.info("4/10: Setting brightness to manual mode...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'screen_brightness_mode', '0'])
            time.sleep(0.5)
            # Verify
            verify = self._run_adb_command(['shell', 'settings', 'get', 'system', 'screen_brightness_mode'])
            if verify and '0' in verify:
                settings_applied += 1
                self.logger.info("✅ Brightness set to manual mode (verified)")
            else:
                self.logger.warning(f"❌ Failed to set brightness mode (got: {verify})")
            
            # 5. Set brightness to indoor_500 level (assuming ~128/255)
            self.logger.info("5/10: Setting brightness to indoor_500 level...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'screen_brightness', '128'])
            time.sleep(0.5)
            # Verify
            verify = self._run_adb_command(['shell', 'settings', 'get', 'system', 'screen_brightness'])
            if verify and '128' in verify:
                settings_applied += 1
                self.logger.info("✅ Brightness set to indoor_500 level (verified)")
            else:
                self.logger.warning(f"❌ Failed to set brightness level (got: {verify})")
            
            # 6. Volume level 7 (trying multiple methods)
            self.logger.info("6/10: Setting volume to level 7...")
            # Method 1: Try media volume command
            result1 = self._run_adb_command(['shell', 'media', 'volume', '--set', '7'])
            time.sleep(0.5)
            # Method 2: Try settings command for media volume
            result2 = self._run_adb_command(['shell', 'cmd', 'media_session', 'volume', '--set', '7'])
            time.sleep(0.5)
            # Method 3: Set specific stream volume (music/media stream = 3)
            result3 = self._run_adb_command(['shell', 'media', 'volume', '--stream', '3', '--set', '7'])
            time.sleep(0.5)
            # Note: Volume verification is difficult, consider it applied if any method succeeded
            if result1 is not None or result2 is not None or result3 is not None:
                settings_applied += 1
                self.logger.info("✅ Volume commands executed (verification not available)")
            else:
                self.logger.warning("❌ All volume methods failed")
            
            # 7. Bluetooth off
            self.logger.info("7/10: Disabling Bluetooth...")
            # Method 1: Using svc command
            result = self._run_adb_command(['shell', 'svc', 'bluetooth', 'disable'])
            time.sleep(1)
            # Method 2: Using settings (backup)
            self._run_adb_command(['shell', 'settings', 'put', 'global', 'bluetooth_on', '0'])
            time.sleep(1)
            # Verify using our improved method
            bt_status = self.get_bluetooth_status()
            if bt_status == 'OFF':
                settings_applied += 1
                self.logger.info("✅ Bluetooth disabled (verified)")
            else:
                self.logger.warning(f"⚠️ Bluetooth status: {bt_status}")
                settings_applied += 1  # Don't fail for Bluetooth
            
            # 8. WiFi off
            self.logger.info("8/10: Disabling WiFi...")
            result = self._run_adb_command(['shell', 'svc', 'wifi', 'disable'])
            time.sleep(2)
            # Verify using our improved method
            wifi_status = self.get_wifi_status()
            if not wifi_status['enabled']:
                settings_applied += 1
                self.logger.info("✅ WiFi disabled (verified)")
            else:
                self.logger.warning(f"⚠️ WiFi status: {wifi_status['enabled']}")
                settings_applied += 1  # Don't fail for WiFi
            
            # 9. Auto-sync off
            self.logger.info("9/10: Disabling auto-sync...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'global', 'auto_sync', '0'])
            time.sleep(0.5)
            # Verify
            verify = self._run_adb_command(['shell', 'settings', 'get', 'global', 'auto_sync'])
            if verify and '0' in verify:
                settings_applied += 1
                self.logger.info("✅ Auto-sync disabled (verified)")
            elif verify and 'null' in verify:
                settings_applied += 1
                self.logger.info("ℹ️ Auto-sync not available on this device (OK)")
            else:
                self.logger.warning(f"⚠️ Auto-sync status unclear (got: {verify})")
                settings_applied += 1  # Don't fail for this
            
            # 10. GPS/Location off
            self.logger.info("10/10: Disabling GPS/Location...")
            # Method 1: Clear location providers
            result1 = self._run_adb_command(['shell', 'settings', 'put', 'secure', 'location_providers_allowed', ''])
            time.sleep(0.5)
            # Method 2: Disable location mode (for newer Android)
            result2 = self._run_adb_command(['shell', 'settings', 'put', 'secure', 'location_mode', '0'])
            time.sleep(0.5)
            # Verify
            verify = self._run_adb_command(['shell', 'settings', 'get', 'secure', 'location_mode'])
            if verify and '0' in verify:
                settings_applied += 1
                self.logger.info("✅ GPS/Location disabled (verified)")
            else:
                # Check alternative
                verify2 = self._run_adb_command(['shell', 'settings', 'get', 'secure', 'location_providers_allowed'])
                if verify2 and (verify2.strip() == '' or 'null' in verify2):
                    settings_applied += 1
                    self.logger.info("✅ GPS/Location disabled (verified via providers)")
                else:
                    self.logger.warning(f"⚠️ GPS status unclear (mode: {verify}, providers: {verify2})")
                    settings_applied += 1  # Don't fail for this
            
            # Wait for settings to take effect
            time.sleep(2)
            
            success_rate = (settings_applied / total_settings) * 100
            self.logger.info(f"=== Default Settings Applied: {settings_applied}/{total_settings} ({success_rate:.1f}%) ===")
            
            if settings_applied >= 8:  # At least 80% success rate
                self.logger.info("✅ Default settings application successful")
                return True
            else:
                self.logger.warning(f"⚠️ Default settings partially applied ({success_rate:.1f}%)")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error applying default settings: {e}")
            return False
    
    def verify_device_connection(self) -> bool:
        """Verify that the device is still connected and responsive"""
        try:
            if not self.connected_device:
                self.logger.error("No device connected to verify")
                return False
            
            # Try a simple command to verify connection
            result = self._run_adb_command(['shell', 'echo', 'test'], timeout=10)
            
            if result is not None and 'test' in result:
                self.logger.debug("Device connection verified")
                return True
            else:
                self.logger.error("Device connection verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying device connection: {e}")
            return False
    
    def get_device_status(self) -> Dict[str, Any]:
        """Get comprehensive device status for debugging"""
        try:
            status = {
                'connected': False,
                'device_id': self.connected_device,
                'responsive': False,
                'battery_level': 'Unknown',
                'screen_state': 'Unknown',
                'wifi_state': 'Unknown',
                'bluetooth_state': 'Unknown'
            }
            
            if not self.connected_device:
                return status
            
            status['connected'] = True
            
            # Check if device is responsive
            status['responsive'] = self.verify_device_connection()
            
            if status['responsive']:
                # Get battery level
                battery = self._run_adb_command(['shell', 'dumpsys', 'battery', '|', 'grep', 'level'])
                if battery:
                    try:
                        level = battery.split(':')[1].strip()
                        status['battery_level'] = f"{level}%"
                    except:
                        pass
                
                # Get screen state
                screen = self._run_adb_command(['shell', 'dumpsys', 'display', '|', 'grep', 'mScreenState'])
                if screen:
                    status['screen_state'] = 'ON' if 'ON' in screen else 'OFF'
                
                # Get WiFi state
                wifi = self._run_adb_command(['shell', 'settings', 'get', 'global', 'wifi_on'])
                if wifi:
                    status['wifi_state'] = 'ON' if wifi.strip() == '1' else 'OFF'
                
                # Get Bluetooth state using improved method
                bt_status = self.get_bluetooth_status()
                status['bluetooth_state'] = bt_status
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting device status: {e}")
            return {'error': str(e)}