#!/usr/bin/env python3
"""
Test Enhanced Test Engine
Based on AI recommendations for proper thread architecture
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from services.enhanced_test_engine import EnhancedTestEngine
from services.hvpm import HVPMService
from services.ni_daq import create_ni_service

def setup_logging():
    """Set up logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'enhanced_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )

def main():
    """Test the enhanced engine"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("🚀 ENHANCED TEST ENGINE (Based on AI Recommendations)")
    print("=" * 80)
    
    # Initialize services
    hvpm_service = HVPMService()
    daq_service = create_ni_service()
    
    def log_callback(message: str, level: str = "info"):
        """Enhanced log callback"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        emoji_map = {
            "error": "❌",
            "warn": "⚠️",
            "info": "ℹ️"
        }
        
        emoji = emoji_map.get(level, "📝")
        formatted_msg = f"[{timestamp}] {emoji} {message}"
        print(formatted_msg)
        
        if level == "error":
            logger.error(message)
        elif level == "warn":
            logger.warning(message)
        else:
            logger.info(message)
    
    # Create enhanced engine
    engine = EnhancedTestEngine(
        hvpm_service=hvpm_service,
        daq_service=daq_service,
        log_callback=log_callback
    )
    
    # Connect to Qt signals if available
    def on_progress_updated(progress: int, status: str):
        print(f"📊 Progress: {progress}% - {status}")
    
    def on_test_completed(success: bool, message: str):
        if success:
            print(f"🎉 Test completed: {message}")
        else:
            print(f"💥 Test failed: {message}")
    
    def on_step_completed(step_name: str, success: bool):
        status = "✅" if success else "❌"
        print(f"{status} Step: {step_name}")
    
    try:
        if hasattr(engine, 'progress_updated'):
            engine.progress_updated.connect(on_progress_updated)
        if hasattr(engine, 'test_completed'):
            engine.test_completed.connect(on_test_completed)
        if hasattr(engine, 'step_completed'):
            engine.step_completed.connect(on_step_completed)
    except:
        print("Qt signals not available - using callback only")
    
    print(f"\n🎯 Testing Phone App scenario with enhanced engine")
    print(f"📋 Key improvements:")
    print(f"  - Proper worker thread (AI recommendation)")
    print(f"  - Separate DAQ collection thread (user suggestion)")
    print(f"  - Thread-safe signal emission")
    print(f"  - Immediate stop response")
    print(f"  - No 120s timeout issues")
    
    # Ask for confirmation
    response = input(f"\n❓ Run enhanced Phone App test? (y/N): ").strip().lower()
    if response != 'y':
        print("Test cancelled.")
        return False
    
    # Start test
    print(f"\n🚀 Starting enhanced Phone App test...")
    start_time = time.time()
    
    try:
        success = engine.start_test("phone_app_test")
        
        if success:
            print("✅ Test started successfully in worker thread")
            
            # Monitor progress (non-blocking)
            while engine.status.value in ["initializing", "running"]:
                status = engine.get_status()
                print(f"📊 Status: {status}")
                time.sleep(2)  # Check every 2 seconds
            
            end_time = time.time()
            duration = end_time - start_time
            
            final_status = engine.get_status()
            print(f"\n📊 Final status: {final_status}")
            print(f"⏱️ Total duration: {duration:.1f} seconds")
            
            return final_status['status'] == 'completed'
        else:
            print("❌ Failed to start test")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted - stopping...")
        engine.stop_test()
        return False
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)