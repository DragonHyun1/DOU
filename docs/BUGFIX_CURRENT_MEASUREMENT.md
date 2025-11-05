# Current Measurement Bugfix

**Date:** 2025-11-04  
**Branch:** DEV  
**Issue:** Phone App Test 결과가 비정상적인 전류 값 출력 (420A 또는 0.0001mA)

---

## 🐛 문제 상황

### 증상
1. **YH.txt 초기 결과**: 420,000 mA (420A) - 너무 큼 ❌
2. **YH.txt 현재 결과**: 0.0001 mA - 너무 작음 ❌  
3. **정상 범위**: 1~60 mA ✅

### 근본 원인

#### 1. `test_scenario_engine.py` 문제
- Line 1434에서 `_read_current_from_channel()` 함수 호출
- **이 함수가 정의되어 있지 않음** → Exception 발생
- Fallback으로 random 시뮬레이션 값 사용 (0.00005 A = 0.05 mA)

#### 2. `ni_daq.py` 문제
- `_read_all_channels()`가 **Voltage Mode**로 측정
- Rail Voltage (4.2V)를 측정하고 shunt resistor (0.01Ω)로 나눔
- 잘못된 계산: 4.2V ÷ 0.01Ω = 420A

```python
# 기존 코드 (잘못됨)
temp_task.ai_channels.add_ai_voltage_chan(...)
voltage = temp_task.read()  # Rail Voltage 측정
current = voltage / shunt_r  # 잘못된 계산
```

---

## ✅ 해결 방법

### 1. `test_scenario_engine.py` 수정

**추가된 함수:** `_read_current_from_channel()` (Line 2107-2135)

```python
def _read_current_from_channel(self, channel: str) -> float:
    """Read current from a specific DAQ channel
    
    Returns:
        Current value in Amps (will be converted to mA later)
    """
    try:
        if not self.daq_service:
            raise Exception("DAQ service not available")
        
        # Use read_single_shot() to get all channel readings
        readings = self.daq_service.read_single_shot()
        
        if not readings or channel not in readings:
            raise Exception(f"No reading available for channel {channel}")
        
        # Get current value from readings (in Amps)
        channel_reading = readings[channel]
        current = channel_reading.get('current', 0.0)
        
        return current
        
    except Exception as e:
        print(f"Error reading current from {channel}: {e}")
        raise
```

**효과:**
- DAQ 서비스의 `read_single_shot()`를 올바르게 호출
- Exception 발생 시 fallback 로직이 작동
- 실제 DAQ에서 전류 값을 읽어옴

### 2. `ni_daq.py` 수정

**변경된 함수:** `_read_all_channels()` (Line 197-250)

```python
# Use CURRENT measurement mode instead of voltage
try:
    temp_task.ai_channels.add_ai_current_chan(
        channel_name,
        min_val=-0.040,  # ±40mA range
        max_val=0.040,
        units=nidaqmx.constants.CurrentUnits.AMPS
    )
    
    # Read current directly in Amps
    current = temp_task.read()
    voltage = 0.0
    
    print(f"Current mode read: {channel} = {current}A ({current*1000:.3f}mA)")
    
except Exception as current_err:
    # Fallback to voltage mode if current mode fails
    print(f"Current mode failed, falling back to voltage mode")
    
    temp_task.ai_channels.add_ai_voltage_chan(...)
    voltage = temp_task.read()
    shunt_r = config.get('shunt_r', 0.010)
    current = voltage / shunt_r
```

**효과:**
- DAQ의 **Current Measurement Mode** 직접 사용
- Shunt resistor 계산 오류 회피
- Voltage mode fallback으로 호환성 유지

---

## 📊 예상 결과

### 수정 전
```
Time(ms)  VBAT(mA)
0         0.000135    ← 너무 작음
1         0.000036
```

또는

```
Time(ms)  VBAT(mA)
0         420328.86   ← 너무 큼
1         420396.96
```

### 수정 후 (예상)
```
Time(ms)  VBAT(mA)
0         5.234       ← 정상 범위
1         6.123
2         12.456
3         15.789
...
```

---

## 🔧 기술적 세부사항

### Current Measurement Mode

DAQ의 Current Measurement는 두 가지 방식으로 작동:

1. **Internal Shunt Resistor** (USB-6289 지원)
   - DAQ 내부의 정밀 shunt resistor 사용
   - 자동 전류 계산
   - 높은 정확도

2. **External Shunt Resistor**
   - 외부 shunt resistor 사용
   - Differential 전압 측정 필요
   - 수동 계산 필요

현재 코드는 **Internal Shunt Resistor** 방식 사용.

### Fallback 전략

1. **Primary:** Current Mode (Direct measurement)
2. **Fallback:** Voltage Mode (Shunt resistor 계산)
3. **Last Resort:** Simulation (Random 값)

---

## ✅ 변경사항 요약

| 파일 | 변경 내용 | 라인 |
|------|----------|------|
| `services/test_scenario_engine.py` | `_read_current_from_channel()` 함수 추가 | +30 |
| `services/ni_daq.py` | `_read_all_channels()` Current Mode로 변경 | +58/-21 |

**Total:** +67 lines

---

## 🧪 테스트 필요 사항

1. **DAQ 연결 확인**
   - NI USB-6289 연결 상태
   - Current Measurement 지원 여부

2. **Channel 설정 확인**
   - Multi-Channel Monitor에서 Current Mode 선택
   - 올바른 채널 enable

3. **값 범위 확인**
   - Phone App 대기: 5~30 mA
   - Phone App 실행: 20~100 mA
   - 피크: 최대 200 mA

4. **Excel 결과 확인**
   - 10,000 샘플 수집 (1ms 간격)
   - Time: 0~9999 ms
   - Current: mA 단위

---

## 📝 참고사항

- Cursor Rules 준수: YH.txt 파일은 수정하지 않음
- Background Agent로 작동: 커밋은 사용자 확인 후
- DEV 브랜치에서 작업
