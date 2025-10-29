#!/usr/bin/env python3
"""
Test script for the new Phone App scenario
사용자 요청 Phone App 시나리오 테스트
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

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'phone_app_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )

def main():
    """Main test function"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("Phone App 시나리오 테스트 시작")
    print("=" * 80)
    
    # Initialize services
    logger.info("Initializing services...")
    
    # HVPM Service
    hvpm_service = HVPMService()
    logger.info("HVPM service initialized")
    
    # DAQ Service
    daq_service = create_ni_service()
    logger.info("DAQ service initialized")
    
    # Test Scenario Engine
    def log_callback(message: str, level: str = "info"):
        """Custom log callback for detailed progress"""
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
    
    engine = TestScenarioEngine(
        hvpm_service=hvpm_service,
        daq_service=daq_service,
        log_callback=log_callback
    )
    
    # Connect to Qt signals for progress updates
    def on_progress_updated(progress: int, status: str):
        print(f"📊 Progress: {progress}% - {status}")
    
    def on_test_completed(success: bool, message: str):
        if success:
            print(f"🎉 Test completed successfully: {message}")
        else:
            print(f"💥 Test failed: {message}")
    
    if hasattr(engine, 'progress_updated'):
        engine.progress_updated.connect(on_progress_updated)
    if hasattr(engine, 'test_completed'):
        engine.test_completed.connect(on_test_completed)
    
    try:
        # List available scenarios
        print("\n📋 Available scenarios:")
        scenarios = engine.get_available_scenarios()
        for key, config in scenarios.items():
            print(f"  - {key}: {config.name}")
            print(f"    {config.description}")
        
        # Check if phone_app_test scenario exists
        if "phone_app_test" not in scenarios:
            print("❌ Phone App Test scenario not found!")
            return False
        
        print(f"\n🎯 Selected scenario: phone_app_test")
        scenario_config = scenarios["phone_app_test"]
        
        print(f"\n📝 Scenario details:")
        print(f"  Name: {scenario_config.name}")
        print(f"  Description: {scenario_config.description}")
        print(f"  HVPM Voltage: {scenario_config.hvpm_voltage}V")
        print(f"  Stabilization Time: {scenario_config.stabilization_time}s")
        print(f"  Test Duration: {scenario_config.test_duration}s")
        print(f"  Steps: {len(scenario_config.steps)}")
        
        print(f"\n📋 Test steps:")
        for i, step in enumerate(scenario_config.steps, 1):
            print(f"  {i:2d}. {step.name} ({step.duration}s) - {step.action}")
        
        # Ask for confirmation
        print(f"\n⚠️  이 테스트는 다음을 수행합니다:")
        print(f"  1. HVPM 4V 설정")
        print(f"  2. 비행기 모드 활성화")
        print(f"  3. WiFi 2G 연결")
        print(f"  4. 블루투스 활성화")
        print(f"  5. 화면 타임아웃 10분 설정")
        print(f"  6. LCD 켜기 + 잠금해제 + 홈 + 앱 정리")
        print(f"  7. 전류 안정화 대기 (10초)")
        print(f"  8. DAQ 모니터링 시작")
        print(f"  9. Phone 앱 시나리오 실행 (10초)")
        print(f"  10. DAQ 모니터링 중지")
        print(f"  11. Excel 파일 저장")
        
        response = input(f"\n계속 진행하시겠습니까? (y/N): ").strip().lower()
        if response != 'y':
            print("테스트가 취소되었습니다.")
            return False
        
        # Start the test
        print(f"\n🚀 Starting Phone App Test...")
        start_time = time.time()
        
        success = engine.run_scenario("phone_app_test")
        
        end_time = time.time()
        duration = end_time - start_time
        
        if success:
            print(f"\n🎉 Phone App Test completed successfully!")
            print(f"⏱️  Total duration: {duration:.1f} seconds")
            
            # Check if data was collected
            if hasattr(engine, 'daq_data') and engine.daq_data:
                print(f"📊 DAQ data collected: {len(engine.daq_data)} data points")
            else:
                print("⚠️  No DAQ data collected")
            
        else:
            print(f"\n💥 Phone App Test failed!")
            print(f"⏱️  Duration before failure: {duration:.1f} seconds")
        
        return success
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Test interrupted by user")
        engine.stop_test()
        return False
        
    except Exception as e:
        logger.error(f"Test execution error: {e}")
        print(f"💥 Test execution error: {e}")
        return False
    
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up...")
        try:
            if hasattr(engine, 'stop_test'):
                engine.stop_test()
        except:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)