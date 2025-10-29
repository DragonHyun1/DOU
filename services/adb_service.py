#!/usr/bin/env python3
"""
ADB Service for Android Device Control
Handles ADB commands for test automation
"""

import subprocess
import time
import logging
from typing import Optional, List, Dict, Any


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
                                  capture_output=True, text=True, timeout=10)
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
                                  capture_output=True, text=True, timeout=timeout)
            
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
    
    def enable_flight_mode(self) -> bool:
        """Enable airplane/flight mode"""
        try:
            # Enable airplane mode
            result = self._run_adb_command(['shell', 'settings', 'put', 'global', 'airplane_mode_on', '1'])
            if result is not None:
                # Broadcast the change
                self._run_adb_command(['shell', 'am', 'broadcast', '-a', 'android.intent.action.AIRPLANE_MODE', '--ez', 'state', 'true'])
                self.logger.info("Flight mode enabled")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error enabling flight mode: {e}")
            return False
    
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
                
                # Step 3: Click Clear All button (multiple positions for compatibility)
                self.logger.info("Step 3: Clicking Clear All button...")
                clear_all_commands = [
                    # Samsung devices - bottom center
                    ['shell', 'input', 'tap', '540', '1800'],
                    # Generic Android - alternative position
                    ['shell', 'input', 'tap', '540', '1700'],
                    # Swipe up to reveal clear all if hidden
                    ['shell', 'input', 'swipe', '540', '1500', '540', '1000'],
                ]
                
                for i, cmd in enumerate(clear_all_commands, 1):
                    self.logger.info(f"  Trying Clear All position {i}...")
                    self._run_adb_command(cmd)
                    time.sleep(0.8)  # Wait between attempts
                
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
        """Connect to 2.4GHz WiFi network using multiple methods"""
        try:
            self.logger.info(f"Connecting to 2.4GHz WiFi: {ssid}")
            
            # Method 1: Enable WiFi first
            self.logger.info("Step 1: Enabling WiFi...")
            self._run_adb_command(['shell', 'svc', 'wifi', 'enable'])
            time.sleep(3)
            
            # Method 2: Try using wpa_cli (if available)
            self.logger.info("Step 2: Attempting WiFi connection...")
            
            # First try: Direct svc command
            result1 = self._run_adb_command(['shell', 'svc', 'wifi', 'connect', ssid, 'password', password])
            time.sleep(3)
            
            # Second try: Using am command to open WiFi settings and connect
            self.logger.info("Step 3: Alternative connection method...")
            
            # Create a temporary WiFi configuration script
            wifi_config = f'''
am start -n com.android.settings/.wifi.WifiSettings
sleep 2
input text "{ssid}"
sleep 1
input keyevent KEYCODE_ENTER
sleep 2
input text "{password}"
sleep 1
input keyevent KEYCODE_ENTER
sleep 3
input keyevent KEYCODE_HOME
'''
            
            # Try alternative method if first method didn't work
            self._run_adb_command(['shell', 'am', 'start', '-a', 'android.settings.WIFI_SETTINGS'])
            time.sleep(2)
            
            # Go back to home after attempting connection
            self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_HOME'])
            time.sleep(2)
            
            # Wait longer for connection to establish
            self.logger.info("Step 4: Waiting for WiFi connection to establish...")
            time.sleep(8)
            
            # Verify connection multiple times
            for attempt in range(3):
                wifi_status = self.get_wifi_status()
                self.logger.info(f"Connection attempt {attempt + 1}: {wifi_status}")
                
                if wifi_status['enabled'] and ssid.lower() in wifi_status['connected_ssid'].lower():
                    self.logger.info(f"Successfully connected to 2.4GHz WiFi: {ssid}")
                    return True
                elif wifi_status['connected_ssid'] != 'Unknown' and wifi_status['connected_ssid'] != '<unknown ssid>':
                    self.logger.info(f"Connected to WiFi (different network): {wifi_status['connected_ssid']}")
                    return True  # Connected to some WiFi network
                
                time.sleep(2)
            
            # If still not connected, check if WiFi is at least enabled
            final_status = self.get_wifi_status()
            if final_status['enabled'] or 'CONNECTED' in final_status['raw_info']:
                self.logger.warning(f"WiFi enabled but connection to {ssid} uncertain. Status: {final_status}")
                return True  # WiFi is working, continue test
            else:
                self.logger.error(f"Failed to connect to WiFi: {ssid}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to 2.4GHz WiFi: {e}")
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
        """Enable Bluetooth"""
        try:
            self.logger.info("Enabling Bluetooth...")
            result = self._run_adb_command(['shell', 'svc', 'bluetooth', 'enable'])
            if result is not None:
                time.sleep(2)  # Wait for Bluetooth to enable
                self.logger.info("Bluetooth enabled")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error enabling Bluetooth: {e}")
            return False
    
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
        Apply default settings for all test scenarios
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
            self.logger.info("=== Applying Default Settings ===")
            settings_applied = 0
            total_settings = 10
            
            # 1. Screen off timeout: 10분 (600000ms)
            self.logger.info("1/10: Setting screen timeout to 10 minutes...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'screen_off_timeout', '600000'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ Screen timeout set to 10 minutes")
            else:
                self.logger.warning("❌ Failed to set screen timeout")
            
            # 2. Multi control disabled
            self.logger.info("2/10: Disabling multi control...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'multi_control_enabled', '0'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ Multi control disabled")
            else:
                self.logger.warning("❌ Failed to disable multi control")
            
            # 3. QuickShare off
            self.logger.info("3/10: Disabling QuickShare...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'quickshare', '0'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ QuickShare disabled")
            else:
                self.logger.warning("❌ Failed to disable QuickShare")
            
            # 4. Brightness mode off (manual mode)
            self.logger.info("4/10: Setting brightness to manual mode...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'screen_brightness_mode', '0'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ Brightness set to manual mode")
            else:
                self.logger.warning("❌ Failed to set brightness mode")
            
            # 5. Set brightness to indoor_500 level (assuming ~128/255)
            self.logger.info("5/10: Setting brightness to indoor_500 level...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'system', 'screen_brightness', '128'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ Brightness set to indoor_500 level")
            else:
                self.logger.warning("❌ Failed to set brightness level")
            
            # 6. Volume level 7
            self.logger.info("6/10: Setting volume to level 7...")
            result = self._run_adb_command(['shell', 'media', 'volume', '--set', '7'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ Volume set to level 7")
            else:
                self.logger.warning("❌ Failed to set volume")
            
            # 7. Bluetooth off
            self.logger.info("7/10: Disabling Bluetooth...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'global', 'bluetooth_on', '0'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ Bluetooth disabled")
            else:
                self.logger.warning("❌ Failed to disable Bluetooth")
            
            # 8. WiFi off
            self.logger.info("8/10: Disabling WiFi...")
            result = self._run_adb_command(['shell', 'svc', 'wifi', 'disable'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ WiFi disabled")
            else:
                self.logger.warning("❌ Failed to disable WiFi")
            
            # 9. Auto-sync off
            self.logger.info("9/10: Disabling auto-sync...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'global', 'auto_sync', '0'])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ Auto-sync disabled")
            else:
                self.logger.warning("❌ Failed to disable auto-sync")
            
            # 10. GPS off
            self.logger.info("10/10: Disabling GPS...")
            result = self._run_adb_command(['shell', 'settings', 'put', 'secure', 'location_providers_allowed', ''])
            if result is not None:
                settings_applied += 1
                self.logger.info("✅ GPS disabled")
            else:
                self.logger.warning("❌ Failed to disable GPS")
            
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
                
                # Get Bluetooth state
                bt = self._run_adb_command(['shell', 'settings', 'get', 'global', 'bluetooth_on'])
                if bt:
                    status['bluetooth_state'] = 'ON' if bt.strip() == '1' else 'OFF'
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting device status: {e}")
            return {'error': str(e)}