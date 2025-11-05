#!/usr/bin/env python3
"""Verify Traditional DAQ API availability and configuration"""

import sys
import os

print("\n" + "="*70)
print("Traditional DAQ API 확인")
print("="*70)

# Step 1: Check if traditional_daq module can be imported
print("\n[1] traditional_daq 모듈 import 확인...")
try:
    sys.path.append('/workspace')
    from services.traditional_daq import get_traditional_daq_service, DAQ_DEFAULT
    print("✓ traditional_daq 모듈 import 성공!")
except ImportError as e:
    print(f"✗ Import 실패: {e}")
    sys.exit(1)

# Step 2: Check if Traditional DAQ API is available
print("\n[2] Traditional DAQ API DLL 확인...")
trad_daq = get_traditional_daq_service()

if trad_daq.is_available():
    print("✓ Traditional DAQ API 사용 가능!")
    print("  → nidaq32.dll 발견")
    print("  → DoU는 Traditional DAQ API 사용 (다른 툴과 동일!)")
else:
    print("✗ Traditional DAQ API 사용 불가")
    print("  → nidaq32.dll 없음")
    print("  → DoU는 DAQmx API fallback 사용 (측정값 차이 있을 수 있음)")
    print("\n해결 방법:")
    print("  1. NI-DAQ (Legacy) 설치")
    print("  2. 또는 DAQmx fallback으로 계속 진행")

# Step 3: Check ni_daq.py integration
print("\n[3] ni_daq.py 통합 확인...")
try:
    from services.ni_daq import NIDAQService
    print("✓ NIDAQService import 성공")
    
    # Check if read_current_channels_hardware_timed exists
    if hasattr(NIDAQService, 'read_current_channels_hardware_timed'):
        print("✓ read_current_channels_hardware_timed 메서드 존재")
    else:
        print("✗ read_current_channels_hardware_timed 메서드 없음")
        
    if hasattr(NIDAQService, '_read_using_daqmx'):
        print("✓ _read_using_daqmx fallback 메서드 존재")
    else:
        print("✗ _read_using_daqmx fallback 메서드 없음")
        
except ImportError as e:
    print(f"✗ NIDAQService import 실패: {e}")

# Step 4: Check numpy (required by Traditional DAQ)
print("\n[4] numpy 패키지 확인...")
try:
    import numpy as np
    print(f"✓ numpy 설치됨 (version: {np.__version__})")
except ImportError:
    print("✗ numpy 없음")
    print("  설치: pip install numpy>=1.21.0")

# Step 5: Summary
print("\n" + "="*70)
print("요약")
print("="*70)

if trad_daq.is_available():
    print("\n✅ Traditional DAQ API 사용 가능!")
    print("\n예상 동작:")
    print("  1. Phone App Test 실행")
    print("  2. Traditional DAQ API 사용 (다른 툴과 동일!)")
    print("  3. 측정값이 Manual 툴과 일치할 것으로 예상")
    print("\n다음 단계:")
    print("  python test_scenarios/scripts/run_phone_app_scenario.py")
else:
    print("\n⚠️ Traditional DAQ API 사용 불가")
    print("\n예상 동작:")
    print("  1. Phone App Test 실행")
    print("  2. DAQmx API fallback 사용")
    print("  3. 측정값이 Manual 툴과 차이 있을 수 있음")
    print("\n옵션:")
    print("  A. NI-DAQ (Legacy) 설치 후 재시도")
    print("  B. DAQmx fallback으로 계속 진행 (측정값 차이 감수)")

print("\n" + "="*70)
