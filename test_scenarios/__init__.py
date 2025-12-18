"""
Test Scenarios Package
Organized test scenarios for different testing purposes
"""

from .scenarios.phone_app.phone_app_scenario import PhoneAppScenario
from .scenarios.screen_on_off.screen_on_off_scenario import ScreenOnOffScenario
from .scenarios.wifi.wifi_2g_scenario import WiFi2GScenario
from .scenarios.wifi.wifi_5g_scenario import WiFi5GScenario

__all__ = [
    'PhoneAppScenario',
    'ScreenOnOffScenario',
    'WiFi2GScenario',
    'WiFi5GScenario',
]