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
        """Run ADB command and return output"""
        if not self.connected_device:
            self.logger.error("No device connected")
            return None
        
        try:
            full_command = ['adb', '-s', self.connected_device] + command
            result = subprocess.run(full_command, 
                                  capture_output=True, text=True, timeout=timeout)
            
            if result.returncode != 0:
                self.logger.error(f"ADB command failed: {' '.join(full_command)}")
                self.logger.error(f"Error: {result.stderr}")
                return None
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"ADB command timeout: {' '.join(command)}")
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
        """Clear recent apps"""
        try:
            # Open recent apps
            result = self._run_adb_command(['shell', 'input', 'keyevent', 'KEYCODE_APP_SWITCH'])
            if result is not None:
                time.sleep(1)  # Wait for recent apps to open
                
                # Clear all recent apps (swipe up gesture)
                # This might need adjustment based on device resolution
                self._run_adb_command(['shell', 'input', 'swipe', '500', '1000', '500', '100'])
                time.sleep(0.5)
                
                self.logger.info("Recent apps cleared")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error clearing recent apps: {e}")
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
    
    def disconnect(self):
        """Disconnect from device"""
        self.connected_device = None
        self.device_info = {}
        self.logger.info("Disconnected from ADB device")