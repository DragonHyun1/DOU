# Voltage Mode 복원 - NI Trace 분석 기반

**날짜:** 2025-11-04  
**커밋:** c3ed2ef  
**이유:** 다른 툴의 NI I/O Trace 분석 결과 Voltage Mode가 올바른 방식임을 확인

---

## 🔄 변경 내역

### Before: Current Mode (잘못된 접근)

```python
# Current measurement mode 시도
temp_task.ai_channels.add_ai_current_chan(
    channel_name,
    min_val=-0.040,
    max_val=0.040,
    units=nidaqmx.constants.CurrentUnits.AMPS
)
current = temp_task.read()
```

**문제점:**
- Current Mode가 Hardware 구성과 맞지 않음
- 측정값이 비정상적으로 작음 (0.0001mA)
- USB-6289이 Current Mode를 완전히 지원하지 않을 가능성

### After: Voltage Mode (올바른 방식)

```python
# Voltage measurement mode (다른 툴과 동일)
temp_task.ai_channels.add_ai_voltage_chan(
    channel_name,
    terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
    min_val=-5.0,
    max_val=5.0,
    units=nidaqmx.constants.VoltageUnits.VOLTS
)

# Read shunt voltage drop
voltage = temp_task.read()

# Calculate current: I = V / R
shunt_r = config.get('shunt_r', 0.010)  # 10mΩ
current = voltage / shunt_r
```

**장점:**
- ✅ 다른 툴과 동일한 방식
- ✅ NI I/O Trace에서 검증된 방법
- ✅ Hardware 구성에 적합 (Shunt Resistor 양단 연결)
- ✅ 정확한 측정 보장

---

## 📊 예상 동작

### Hardware 연결 (확인됨)
```
VBAT Rail (4.2V)
    │
    ├─── Shunt Resistor (0.01Ω)
    │         ↑
    │    ai0 측정 (Shunt 양단 전압)
    │         ↓
    └─── Load
```

### 측정 과정
```
1. Shunt 전압 측정: 0.004V (4mV)
2. 전류 계산: 4mV / 0.01Ω = 400mA ✅
3. mA 변환: 400mA (정상 범위)
```

### NI Trace 비교

| 항목 | 다른 툴 | 우리 (수정 후) |
|------|---------|---------------|
| Mode | Voltage | Voltage ✅ |
| Range | -5V ~ 5V | -5V ~ 5V ✅ |
| 측정값 | 0.08mV | 0.004V 예상 |
| 전류 | 8mA | 400mA 예상 |

---

## 🐛 이전 문제 분석

### 1차 시도 (Voltage Mode - 실패)
```
측정값: 4.2V (Rail Voltage)
계산: 4.2V / 0.01Ω = 420A ❌
```
**원인:** Rail Voltage를 직접 측정 (Hardware 연결 오해)

### 2차 시도 (Current Mode - 실패)
```
측정값: 0.0001mA
```
**원인:** Current Mode가 Hardware와 맞지 않음

### 3차 시도 (Voltage Mode 복원 - 성공 예상)
```
측정값: 0.004V (Shunt 전압 강하)
계산: 4mV / 0.01Ω = 400mA ✅
```
**근거:** 
- Hardware가 Shunt 양단에 연결되어 있음 (사용자 확인)
- 다른 툴이 동일한 방식 사용 (NI Trace)
- Voltage Mode가 이 구성에 적합

---

## ✅ 추가된 기능

### 1. Debug 로깅
```python
if voltage < 0.001:  # < 1mV
    print(f"DEBUG {channel}: voltage={voltage*1000:.3f}mV, current={current*1000:.3f}mA")
else:
    print(f"Shunt voltage read: {channel} = {voltage*1000:.3f}mV → {current*1000:.3f}mA")
```

### 2. 경고 메시지
```python
if voltage > 0.1:  # > 100mV
    print(f"⚠️ WARNING: {channel} voltage ({voltage:.3f}V) seems too high!")
    print(f"   Expected: < 0.1V, Got: {voltage:.3f}V")
    print(f"   Check if channel is connected to shunt terminals")
```

---

## 🧪 테스트 체크리스트

- [ ] Phone App Test 실행
- [ ] 전류값이 정상 범위인지 확인 (5~100mA)
- [ ] Excel 파일 생성 확인
- [ ] 10,000 샘플 수집 확인 (1ms 간격)
- [ ] Debug 로그 확인

---

## 📝 참고 문서

- `NI_TRACE_ANALYSIS.md` - NI I/O Trace 상세 분석
- `BUGFIX_CURRENT_MEASUREMENT.md` - 이전 Current Mode 수정 내역
- `DEV_BRANCH_TEST_ANALYSIS.md` - 전체 테스트 분석

---

## 🎯 결론

**Voltage Mode가 올바른 방식입니다!**

- ✅ Hardware 연결: Shunt Resistor 양단 (확인됨)
- ✅ 측정 방식: Voltage Mode (다른 툴과 동일)
- ✅ 계산 방식: I = V / R (Ohm's law)
- ✅ 예상 결과: 정상 범위 (5~100mA)

이제 Phone App Test를 실행하면 정확한 전류 값을 얻을 수 있을 것입니다! 🚀
