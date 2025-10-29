#!/usr/bin/env python3
"""
Phone App Scenario Runner
Uses the new organized test scenario structure
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Add test_scenarios to path
test_scenarios_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, test_scenarios_path)

from services.hvpm import HVPMService
from services.ni_daq import create_ni_service
from services.adb_service import ADBService
from scenarios.phone_app import PhoneAppScenario
from configs.test_config import TestConfig

def setup_logging():
    """Set up logging configuration"""
    TestConfig.ensure_directories()
    
    log_config = TestConfig.get_logging_config()
    log_filename = f"{log_config['file_prefix']}_phone_app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(TestConfig.get_paths()['logs_dir'], log_filename)
    
    logging.basicConfig(
        level=getattr(logging, log_config['level']),
        format=log_config['format'],
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path)
        ]
    )
    
    return log_path

def main():
    """Main test function"""
    log_path = setup_logging()
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("📱 PHONE APP SCENARIO TEST (Organized Structure)")
    print("=" * 80)
    print(f"📝 Log file: {log_path}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize services
    logger.info("Initializing services...")
    
    hvpm_service = HVPMService()
    daq_service = create_ni_service()
    adb_service = ADBService()
    
    def log_callback(message: str, level: str = "info"):
        """Enhanced log callback"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        
        if level == "error":
            logger.error(formatted_msg)
            print(f"❌ {formatted_msg}")
        elif level == "warn":
            logger.warning(formatted_msg)
            print(f"⚠️  {formatted_msg}")
        else:
            logger.info(formatted_msg)
            print(f"✅ {formatted_msg}")
    
    # Create Phone App scenario
    scenario = PhoneAppScenario(
        hvpm_service=hvpm_service,
        daq_service=daq_service,
        adb_service=adb_service,
        log_callback=log_callback
    )
    
    # Get scenario configuration
    config = scenario.get_config()
    print(f"\n📝 Scenario: {config.name}")
    print(f"📄 Description: {config.description}")
    print(f"⚡ HVPM Voltage: {config.hvpm_voltage}V")
    print(f"⏱️ Test Duration: {config.test_duration}s")
    print(f"📊 Steps: {len(config.steps)}")
    
    print(f"\n📋 Test steps:")
    for i, step in enumerate(config.steps, 1):
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
        success = scenario.run()
        
        end_time = time.time()
        duration = end_time - start_time
        
        if success:
            print(f"\n🎉 Phone App Test completed successfully!")
            print(f"⏱️ Total duration: {duration:.1f} seconds")
            
            # Get progress information
            progress = scenario.get_progress()
            print(f"📊 Final progress: {progress}")
            
            return True
        else:
            print(f"\n💥 Phone App Test failed!")
            print(f"⏱️ Duration before failure: {duration:.1f} seconds")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        logger.exception("Test execution error")
        print(f"\n💥 Test execution error: {e}")
        return False
    
    finally:
        print(f"\n📝 Detailed logs saved to: {log_path}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)