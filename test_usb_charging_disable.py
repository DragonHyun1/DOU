#!/usr/bin/env python3
"""
USB 충전 비활성화 테스트 스크립트
실제로 ADB 명령이 작동하는지 확인
"""

import subprocess
import time

def run_adb(command):
    """ADB 명령 실행"""
    try:
        result = subprocess.run(
            ['adb', 'shell'] + command.split(),
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return None, str(e), -1

def main():
    print("=" * 60)
    print("USB 충전 비활성화 테스트")
    print("=" * 60)
    
    # 1. 현재 배터리 상태 확인
    print("\n[1] 현재 배터리 상태:")
    stdout, stderr, code = run_adb("dumpsys battery")
    if code == 0:
        for line in stdout.split('\n'):
            if any(key in line.lower() for key in ['voltage', 'usb', 'ac', 'powered', 'status']):
                print(f"  {line.strip()}")
    else:
        print(f"  ERROR: {stderr}")
        return
    
    # 2. USB 충전 비활성화 (방법 1)
    print("\n[2] USB 충전 비활성화 시도 (set usb 0):")
    stdout, stderr, code = run_adb("dumpsys battery set usb 0")
    print(f"  Return code: {code}")
    if stderr:
        print(f"  Stderr: {stderr}")
    
    time.sleep(1)
    
    # 3. 확인
    print("\n[3] USB 충전 비활성화 후 상태:")
    stdout, stderr, code = run_adb("dumpsys battery")
    if code == 0:
        for line in stdout.split('\n'):
            if any(key in line.lower() for key in ['voltage', 'usb', 'ac', 'powered', 'status']):
                print(f"  {line.strip()}")
    
    # 4. AC 충전도 비활성화
    print("\n[4] AC 충전도 비활성화 시도 (set ac 0):")
    stdout, stderr, code = run_adb("dumpsys battery set ac 0")
    print(f"  Return code: {code}")
    
    time.sleep(1)
    
    # 5. 다시 확인
    print("\n[5] AC 충전 비활성화 후 상태:")
    stdout, stderr, code = run_adb("dumpsys battery")
    if code == 0:
        for line in stdout.split('\n'):
            if any(key in line.lower() for key in ['voltage', 'usb', 'ac', 'powered', 'status']):
                print(f"  {line.strip()}")
    
    # 6. unplug 명령 시도
    print("\n[6] unplug 명령 시도:")
    stdout, stderr, code = run_adb("dumpsys battery unplug")
    print(f"  Return code: {code}")
    
    time.sleep(1)
    
    # 7. 최종 상태
    print("\n[7] 최종 배터리 상태:")
    stdout, stderr, code = run_adb("dumpsys battery")
    if code == 0:
        for line in stdout.split('\n'):
            if any(key in line.lower() for key in ['voltage', 'usb', 'ac', 'powered', 'status', 'health']):
                print(f"  {line.strip()}")
    
    # 8. 복원 방법 안내
    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("\n복원 방법:")
    print("  adb shell dumpsys battery reset")
    print("=" * 60)

if __name__ == "__main__":
    main()
