"""
Default Settings Module
Common default settings applied to all test scenarios
"""

from typing import Dict, Any


class DefaultSettings:
    """Default settings configuration for all test scenarios"""
    
    # Default settings configuration
    SETTINGS = {
        'screen_off_timeout': 600000,  # 10 minutes in milliseconds
        'multi_control_enabled': 0,
        'quickshare': 0,
        'screen_brightness_mode': 0,  # Manual mode
        'screen_brightness': 128,     # Indoor_500 level
        'volume': 7,
        'bluetooth_on': 0,            # Off
        'wifi_on': 0,                 # Off
        'auto_sync': 0,               # Off
        'location_providers_allowed': '',  # GPS off
        'aod_mode': 0,                # AOD off
        'aod_show_state': 0           # AOD off
    }
    
    @classmethod
    def get_settings(cls) -> Dict[str, Any]:
        """Get default settings dictionary"""
        return cls.SETTINGS.copy()
    
    @classmethod
    def get_setting_commands(cls) -> Dict[str, list]:
        """Get ADB commands for applying default settings"""
        return {
            'screen_off_timeout': ['shell', 'settings', 'put', 'system', 'screen_off_timeout', str(cls.SETTINGS['screen_off_timeout'])],
            'multi_control_enabled': ['shell', 'settings', 'put', 'system', 'multi_control_enabled', str(cls.SETTINGS['multi_control_enabled'])],
            'quickshare': ['shell', 'settings', 'put', 'system', 'quickshare', str(cls.SETTINGS['quickshare'])],
            'screen_brightness_mode': ['shell', 'settings', 'put', 'system', 'screen_brightness_mode', str(cls.SETTINGS['screen_brightness_mode'])],
            'screen_brightness': ['shell', 'settings', 'put', 'system', 'screen_brightness', str(cls.SETTINGS['screen_brightness'])],
            'volume': ['shell', 'media', 'volume', '--set', str(cls.SETTINGS['volume'])],
            'bluetooth_on': ['shell', 'settings', 'put', 'global', 'bluetooth_on', str(cls.SETTINGS['bluetooth_on'])],
            'wifi_disable': ['shell', 'svc', 'wifi', 'disable'],
            'auto_sync': ['shell', 'settings', 'put', 'global', 'auto_sync', str(cls.SETTINGS['auto_sync'])],
            'location_providers_allowed': ['shell', 'settings', 'put', 'secure', 'location_providers_allowed', cls.SETTINGS['location_providers_allowed']],
            'aod_mode': ['shell', 'settings', 'put', 'secure', 'aod_mode', str(cls.SETTINGS['aod_mode'])],
            'aod_show_state': ['shell', 'settings', 'put', 'secure', 'aod_show_state', str(cls.SETTINGS['aod_show_state'])]
        }
    
    @classmethod
    def get_description(cls) -> str:
        """Get description of default settings"""
        return """
Default Settings Applied to All Test Scenarios:
- Screen off timeout: 10 minutes
- Multi control: Disabled
- QuickShare: Disabled
- Brightness mode: Manual
- Brightness level: Indoor_500 (128/255)
- Volume: Level 7
- Bluetooth: Disabled
- WiFi: Disabled
- Auto-sync: Disabled
- GPS: Disabled
- AOD (Always On Display): Disabled
        """.strip()