"""
Test Scenarios Package
Organized test scenarios for different testing purposes
"""

from .scenarios.phone_app.phone_app_scenario import PhoneAppScenario
from .scenarios.idle_wait.idle_wait_scenario import IdleWaitScenario
from .scenarios.screen_on_off.screen_on_off_scenario import ScreenOnOffScenario

__all__ = [
    'PhoneAppScenario',
    'IdleWaitScenario',
    'ScreenOnOffScenario',
]