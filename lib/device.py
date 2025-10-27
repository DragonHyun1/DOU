"""
Device wrapper for ADB operations
Provides a unified interface for device control operations
"""
import time
import re
from typing import Dict, Any, Optional


class Device:
    """Device control wrapper for ADB operations"""
    
    def __init__(self, adb_service=None):
        self.adb_service = adb_service
        self._screen_size = None
        
    def shell(self, command: str) -> str:
        """Execute shell command on device"""
        if self.adb_service:
            return self.adb_service.shell(command)
        else:
            # Fallback for testing
            print(f"[MOCK] shell: {command}")
            return ""
    
    def sleep(self, milliseconds: int):
        """Sleep for specified milliseconds"""
        time.sleep(milliseconds / 1000.0)
    
    def press(self, key: str):
        """Press hardware key"""
        key_map = {
            "home": "KEYCODE_HOME",
            "back": "KEYCODE_BACK", 
            "menu": "KEYCODE_MENU",
            "search": "KEYCODE_SEARCH",
            "enter": "KEYCODE_ENTER",
            "app_switch": "KEYCODE_APP_SWITCH",
            "statusbar": "service call statusbar 1"  # Special case
        }
        
        if key == "statusbar":
            self.shell(key_map[key])
        else:
            keycode = key_map.get(key, f"KEYCODE_{key.upper()}")
            self.shell(f"input keyevent {keycode}")
    
    def tap(self, x: int, y: int):
        """Tap at coordinates"""
        self.shell(f"input tap {x} {y}")
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 500):
        """Swipe from (x1,y1) to (x2,y2)"""
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
    
    def type_text(self, text: str):
        """Type text input"""
        # Escape special characters
        escaped_text = text.replace('"', '\\"').replace(' ', '%s')
        self.shell(f'input text "{escaped_text}"')
    
    def rotation(self, mode: str):
        """Set screen rotation"""
        if mode == "0":
            self.shell("settings put system user_rotation 0")
        elif mode == "1": 
            self.shell("settings put system user_rotation 1")
        elif mode == "on":
            self.shell("settings put system accelerometer_rotation 1")
        elif mode == "off":
            self.shell("settings put system accelerometer_rotation 0")
    
    def get_screen_size(self) -> tuple:
        """Get screen dimensions"""
        if self._screen_size:
            return self._screen_size
            
        size_output = self.shell("wm size")
        # Parse "Physical size: 1080x2340" or "Override size: 1080x2340"
        match = re.search(r'(\d+)x(\d+)', size_output)
        if match:
            width, height = int(match.group(1)), int(match.group(2))
            self._screen_size = (width, height)
            return self._screen_size
        return (1080, 2340)  # Default fallback
    
    def click(self, selector: Dict[str, Any]) -> bool:
        """Click UI element by selector (mock implementation)"""
        # This would need uiautomator2 integration for real implementation
        if "textMatches" in selector:
            pattern = selector["textMatches"]
            print(f"[MOCK] Clicking element with textMatches: {pattern}")
            return True
        elif "resourceId" in selector:
            res_id = selector["resourceId"]
            print(f"[MOCK] Clicking element with resourceId: {res_id}")
            return True
        elif "text" in selector:
            text = selector["text"]
            print(f"[MOCK] Clicking element with text: {text}")
            return True
        return False
    
    def log(self, message: str):
        """Log message"""
        print(f"[DEVICE LOG] {message}")
    
    # Mock u2 property for compatibility
    class MockU2:
        def __init__(self, device):
            self.device = device
            
        def __call__(self, **kwargs):
            return MockElement(kwargs)
    
    @property
    def u2(self):
        return self.MockU2(self)


class MockElement:
    """Mock UI element for testing"""
    def __init__(self, selector):
        self.selector = selector
        
    @property
    def exists(self) -> bool:
        # Mock existence check
        return True
        
    def click(self):
        print(f"[MOCK] Element clicked: {self.selector}")