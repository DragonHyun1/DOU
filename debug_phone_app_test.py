#!/usr/bin/env python3
"""
Debug script for Phone App scenario
Enhanced with Default Settings and comprehensive error handling
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.test_scenario_engine import TestScenarioEngine
from services.hvpm import HVPMService
from services.ni_daq import create_ni_service
from services.adb_service import ADBService

def setup_debug_logging():
    """Set up comprehensive logging for debugging"""
    log_filename = f'debug_phone_app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.DEBUG,  # Enable DEBUG level for detailed logs
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_filename)
        ]
    )
    
    return log_filename

def test_adb_connection():
    """Test ADB connection and device status"""
    print("\n" + "="*60)
    print("🔍 TESTING ADB CONNECTION")
    print("="*60)
    
    adb_service = ADBService()
    
    # Get connected devices
    devices = adb_service.get_connected_devices()
    print(f"📱 Connected devices: {devices}")
    
    if not devices:
        print("❌ No ADB devices found!")
        print("Please check:")
        print("  1. Device is connected via USB")
        print("  2. USB debugging is enabled")
        print("  3. ADB is installed and in PATH")
        return False
    
    # Connect to first device
    device_id = devices[0]
    print(f"🔌 Connecting to device: {device_id}")
    
    if adb_service.connect_device(device_id):
        print("✅ ADB connection successful")
        
        # Get device status
        status = adb_service.get_device_status()
        print(f"📊 Device status: {status}")
        
        return True
    else:
        print("❌ ADB connection failed")
        return False

def test_default_settings():
    """Test default settings application"""
    print("\n" + "="*60)
    print("⚙️ TESTING DEFAULT SETTINGS")
    print("="*60)
    
    adb_service = ADBService()
    
    # Connect to device
    devices = adb_service.get_connected_devices()
    if not devices:
        print("❌ No devices available for default settings test")
        return False
    
    if not adb_service.connect_device(devices[0]):
        print("❌ Failed to connect to device")
        return False
    
    # Get initial status
    print("📊 Getting initial device status...")
    initial_status = adb_service.get_device_status()
    print(f"Initial: {initial_status}")
    
    # Apply default settings
    print("⚙️ Applying default settings...")
    success = adb_service.apply_default_settings()
    
    # Get final status
    print("📊 Getting final device status...")
    final_status = adb_service.get_device_status()
    print(f"Final: {final_status}")
    
    if success:
        print("✅ Default settings applied successfully")
        return True
    else:
        print("⚠️ Default settings partially applied")
        return False

def test_phone_app_scenario():
    """Test complete Phone App scenario with debugging"""
    print("\n" + "="*60)
    print("📱 TESTING PHONE APP SCENARIO")
    print("="*60)
    
    # Initialize services
    print("🔧 Initializing services...")
    hvpm_service = HVPMService()
    daq_service = create_ni_service()
    
    def debug_log_callback(message: str, level: str = "info"):
        """Enhanced log callback with timestamps and emojis"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        emoji_map = {
            "error": "❌",
            "warn": "⚠️",
            "info": "ℹ️",
            "debug": "🔍"
        }
        
        emoji = emoji_map.get(level, "📝")
        formatted_msg = f"[{timestamp}] {emoji} {message}"
        
        print(formatted_msg)
        
        # Also log to standard logging
        logger = logging.getLogger("debug_test")
        if level == "error":
            logger.error(message)
        elif level == "warn":
            logger.warning(message)
        elif level == "debug":
            logger.debug(message)
        else:
            logger.info(message)
    
    engine = TestScenarioEngine(
        hvpm_service=hvpm_service,
        daq_service=daq_service,
        log_callback=debug_log_callback
    )
    
    # Get available scenarios
    scenarios = engine.get_available_scenarios()
    print(f"📋 Available scenarios: {list(scenarios.keys())}")
    
    if "phone_app_test" not in scenarios:
        print("❌ Phone App Test scenario not found!")
        return False
    
    # Show scenario details
    scenario = scenarios["phone_app_test"]
    print(f"\n📝 Scenario: {scenario.name}")
    print(f"📄 Description: {scenario.description}")
    print(f"⚡ HVPM Voltage: {scenario.hvpm_voltage}V")
    print(f"⏱️ Test Duration: {scenario.test_duration}s")
    print(f"📊 Steps: {len(scenario.steps)}")
    
    print(f"\n📋 Test steps:")
    for i, step in enumerate(scenario.steps, 1):
        print(f"  {i:2d}. {step.name} ({step.duration}s) - {step.action}")
    
    # Ask for confirmation
    response = input(f"\n❓ Run Phone App Test scenario? (y/N): ").strip().lower()
    if response != 'y':
        print("Test cancelled.")
        return False
    
    # Run the test
    print(f"\n🚀 Starting Phone App Test...")
    start_time = time.time()
    
    try:
        success = engine.run_scenario("phone_app_test")
        
        end_time = time.time()
        duration = end_time - start_time
        
        if success:
            print(f"\n🎉 Phone App Test completed successfully!")
            print(f"⏱️ Total duration: {duration:.1f} seconds")
            
            # Check DAQ data
            if hasattr(engine, 'daq_data') and engine.daq_data:
                print(f"📊 DAQ data collected: {len(engine.daq_data)} data points")
            else:
                print("⚠️ No DAQ data collected")
            
            return True
        else:
            print(f"\n💥 Phone App Test failed!")
            print(f"⏱️ Duration before failure: {duration:.1f} seconds")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user")
        engine.stop_test()
        return False
    except Exception as e:
        print(f"\n💥 Test execution error: {e}")
        return False

def main():
    """Main debug function"""
    log_filename = setup_debug_logging()
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("🔍 PHONE APP SCENARIO DEBUG SESSION")
    print("=" * 80)
    print(f"📝 Debug log file: {log_filename}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test sequence
    tests = [
        ("ADB Connection", test_adb_connection),
        ("Default Settings", test_default_settings),
        ("Phone App Scenario", test_phone_app_scenario)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"💥 {test_name} crashed: {e}")
            results[test_name] = False
            logger.exception(f"{test_name} test failed")
    
    # Summary
    print("\n" + "="*80)
    print("📊 DEBUG SESSION SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} : {status}")
    
    overall_success = all(results.values())
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    print(f"📝 Detailed logs saved to: {log_filename}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)