#!/usr/bin/env python3
"""
Test script to verify scenario loading
"""

import sys
from services.test_scenario_engine import TestScenarioEngine

def test_scenario_loading():
    """Test if scenarios are loaded correctly"""
    
    def log_callback(msg, level="info"):
        print(f"[{level.upper()}] {msg}")
    
    print("=== Testing Test Scenario Engine ===")
    
    # Create test scenario engine
    engine = TestScenarioEngine(log_callback=log_callback)
    
    # Get available scenarios
    scenarios = engine.get_available_scenarios()
    
    print(f"\nFound {len(scenarios)} scenarios:")
    for key, config in scenarios.items():
        print(f"  Key: '{key}' -> Name: '{config.name}'")
        print(f"    Description: {config.description}")
        print(f"    Steps: {len(config.steps) if config.steps else 0}")
    
    print("\n=== Test Complete ===")
    
    return len(scenarios) > 0

if __name__ == "__main__":
    success = test_scenario_loading()
    sys.exit(0 if success else 1)