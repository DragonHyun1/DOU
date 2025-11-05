# USB 충전 간섭 문제 해결

**날짜:** 2025-11-04  
**커밋:** 0e5ccb6  
**문제:** USB 연결 시 Battery Rail이 4.2V로 올라가는 문제

---

## 🔌 문제 상황

### 증상
```
USB 미연결: HVPM 4V → Battery Rail 4V ✅
USB 연결:   HVPM 4V + USB 5V → Battery Rail 4.2V ❌
```

### 원인
- USB VBUS (5V)가 충전 회로를 통해 Battery Rail 공급
- 충전 회로가 Battery를 4.2V로 충전 (리튬이온 배터리 표준)
- HVPM의 4V보다 USB 충전 전압이 우선됨
- **ADB 사용을 위해서는 USB 연결 필수**

### 영향
- 테스트 시 Battery 전압이 4.2V로 고정됨
- HVPM 4V 설정이 무의미해짐
- 전류 측정 및 Power 분석이 부정확해짐

---

## ✅ 해결 방법

### ADB 명령으로 USB 충전 비활성화

Android의 `dumpsys battery` 명령을 사용하여 **소프트웨어적으로** USB 충전을 끌 수 있습니다!

```bash
# 충전 비활성화
adb shell dumpsys battery set usb 0

# 충전 활성화 (복원)
adb shell dumpsys battery reset

# 배터리 전압 확인
adb shell dumpsys battery | grep voltage
```

---

## 🔧 구현 내역

### 1. ADBService에 메서드 추가

**파일:** `services/adb_service.py`

#### disable_usb_charging()
```python
def disable_usb_charging(self) -> bool:
    """Disable USB charging to prevent voltage interference
    
    USB VBUS (5V) charges battery rail to 4.2V,
    interfering with HVPM's 4V supply.
    """
    result = self._run_adb_command(['shell', 'dumpsys', 'battery', 'set', 'usb', '0'])
    return result is not None
```

#### enable_usb_charging()
```python
def enable_usb_charging(self) -> bool:
    """Re-enable USB charging (restore normal behavior)"""
    result = self._run_adb_command(['shell', 'dumpsys', 'battery', 'reset'])
    return result is not None
```

#### get_battery_voltage()
```python
def get_battery_voltage(self) -> Optional[float]:
    """Get current battery voltage in volts"""
    result = self._run_adb_command(['shell', 'dumpsys', 'battery'])
    # Parse "voltage: 4000" (mV) → 4.0V
    return voltage_v
```

### 2. Phone App 시나리오에 통합

**파일:** `test_scenarios/scenarios/phone_app/phone_app_scenario.py`

**새로운 스텝 추가 (2번째):**
```python
TestStep("disable_usb_charging", 2.0, "disable_usb_charging")
```

**실행 순서:**
```
1. Default Settings (5s)
2. Disable USB Charging (2s)  ← 새로 추가! (HVPM 설정 전)
3. LCD ON + Unlock (3s)
4. Set HVPM 4V (2s)
5. Airplane Mode (2s)
6. ... (나머지 스텝)
```

**중요:** USB 충전을 **HVPM 설정 전에** 비활성화해야 합니다!

---

## 📊 동작 과정

### Phone App Test 실행 시

```
Step 1: Default Settings
  ✅ WiFi, Bluetooth 등 기본 설정

Step 2: Disable USB Charging  ← 핵심!
  🔌 ADB: dumpsys battery set usb 0
  ⏱️  대기: 1초
  📊 확인: Battery voltage = 4.0V (정상)
  ✅ USB charging disabled

Step 3: LCD ON + Unlock
  📱 화면 켜기

Step 4: Set HVPM 4V
  ⚡ HVPM → 4V 출력
  📊 Battery Rail = 4V (USB 간섭 없음!) ✅
```

### 전압 모니터링

```python
# 배터리 전압 확인
voltage = adb_service.get_battery_voltage()
print(f"Battery voltage: {voltage:.3f}V")

# 4.1V 이상이면 경고
if voltage > 4.1:
    print("⚠️ WARNING: Battery voltage still high")
    time.sleep(2.0)  # 안정화 대기
```

---

## 🧪 테스트 방법

### 수동 테스트

```bash
# 1. USB 연결 (ADB 활성화)
adb devices

# 2. 충전 비활성화
adb shell dumpsys battery set usb 0

# 3. 배터리 상태 확인
adb shell dumpsys battery
# 출력 예시:
#   USB powered: false  ← 중요!
#   voltage: 4000       ← 4V

# 4. 충전 복원
adb shell dumpsys battery reset

# 5. 다시 확인
adb shell dumpsys battery
# 출력 예시:
#   USB powered: true
#   voltage: 4200       ← 4.2V
```

### 자동 테스트

```bash
# Phone App Test 실행
cd /workspace
PYTHONPATH=/workspace python3 test_scenarios/scripts/run_phone_app_scenario.py

# 로그 확인
=== Disabling USB Charging ===
✅ USB charging disabled
📊 Battery voltage: 4.000V
```

---

## ⚠️ 주의사항

### 1. Root 권한 불필요
- `dumpsys battery` 명령은 **일반 권한**으로 실행 가능
- Root나 system 권한 불필요

### 2. 재부팅 시 복원
- 디바이스 재부팅하면 자동으로 충전 활성화됨
- 테스트 종료 후 수동 복원 필요 없음

### 3. 배터리 안전
- USB 전원은 유지되므로 디바이스는 정상 작동
- 배터리가 방전되지 않음 (HVPM이 전원 공급)

### 4. 테스트 종료 후
- 선택적으로 `enable_usb_charging()` 호출 가능
- 필수는 아님 (재부팅 시 자동 복원)

---

## 📝 예상 결과

### Before (USB 충전 활성화 상태)
```
HVPM 설정: 4.0V
실제 Battery: 4.2V ❌
전류 측정: 부정확
```

### After (USB 충전 비활성화 적용)
```
HVPM 설정: 4.0V
실제 Battery: 4.0V ✅
전류 측정: 정확
```

---

## 🎯 결론

**ADB 명령으로 USB 충전을 소프트웨어적으로 비활성화!**

- ✅ USB 연결 유지 (ADB 사용 가능)
- ✅ USB 충전 비활성화 (HVPM 전압 유지)
- ✅ 자동 통합 (Phone App 시나리오)
- ✅ Root 권한 불필요
- ✅ 안전하고 간단함

이제 USB를 연결한 상태로 정확한 4V 테스트가 가능합니다! 🚀
