# Current Mode vs Voltage Mode 비교 분석

## 문제 상황

- **Manual**: 전압 1.05V 측정 → 전류 1.018mA 출력
- **DoU**: 전압 0.033mV 측정 → 전류 6.533mA 계산
- **차이**: 6.42배

## 🔍 핵심 가설: Manual이 Current Mode를 사용한다

### Current Mode (DAQmxCreateAICurrentChan)

```c
DAQmxCreateAICurrentChan(
    taskHandle,
    physicalChannel,
    nameToAssignToChannel,
    terminalConfig,        // RSE, DIFFERENTIAL 등
    minVal,                // 최소 전류 (Amps)
    maxVal,                // 최대 전류 (Amps) 
    units,                 // DAQmx_Val_Amps
    shuntResistorLoc,      // DAQmx_Val_Internal (10200) 또는 DAQmx_Val_External (10167)
    extShuntResistVal,     // External shunt 값 (Ohms)
    customScaleName        // NULL
);
```

**동작 원리:**
1. **DAQ가 내부적으로 전압을 측정** (Rail voltage나 Shunt voltage)
2. **DAQ가 자동으로 전류로 변환** (내부 알고리즘 사용)
3. **사용자는 전류 값만 받음** (mA 또는 A)

**중요:**
- 사용자가 보는 "전압 1.05V"는 **디버그/참조용 Rail Voltage**
- 실제 전류 계산은 **DAQ 내부에서 수행**
- External shunt 설정에 따라 **자동으로 올바르게 계산됨**

### Voltage Mode (DAQmxCreateAIVoltageChan)

```c
DAQmxCreateAIVoltageChan(
    taskHandle,
    physicalChannel,
    nameToAssignToChannel,
    terminalConfig,        // RSE, DIFFERENTIAL 등
    minVal,                // 최소 전압 (Volts)
    maxVal,                // 최대 전압 (Volts)
    units,                 // DAQmx_Val_Volts
    customScaleName        // NULL
);
```

**동작 원리:**
1. **DAQ가 전압을 측정** (Raw voltage)
2. **사용자가 수동으로 전류 계산** (I = V / R)
3. **측정 위치에 따라 결과가 완전히 다름:**
   - RSE mode → Rail voltage 측정 (잘못됨!)
   - DIFFERENTIAL → Shunt drop 측정 (올바름)

## 🎯 왜 6.42배 차이가 나는가?

### 가설 1: Manual의 Internal Calibration

**Current Mode의 경우:**
- NI DAQ가 **내부 calibration data**를 사용
- Factory calibration + User calibration
- **정확한 전류 값 출력**

**Voltage Mode의 경우:**
- Raw voltage만 측정
- Calibration이 적용되지 않을 수 있음
- **측정 오차가 그대로 전류 계산에 반영됨**

### 가설 2: Shunt Drop 측정 오차

```
실제 Shunt Drop (Manual 내부 계산):
1.018mA × 0.005Ω = 0.00509mV (5.09 µV)

DoU가 측정한 Shunt Drop:
0.033mV (33 µV)

차이: 33 / 5.09 ≈ 6.48배
```

**DoU가 측정한 0.033mV는 왜 6.48배 더 큰가?**

#### 가능성 1: Common Mode Voltage 간섭
```
DIFFERENTIAL mode (이상적):
V_measured = V(+) - V(-)
         = (Rail - Shunt_drop) - Rail
         = -Shunt_drop
         = -0.00509mV ✅

DEFAULT mode가 RSE처럼 작동 (문제):
V_measured = V(+) - Ground
         = Rail voltage의 일부가 포함됨
         = 0.033mV (잘못된 값) ❌
```

#### 가능성 2: Gain/Amplification 차이
```
Manual (Current Mode):
- DAQ 내부 gain: 자동 조정
- Optimal gain for current measurement

DoU (Voltage Mode):
- Gain: Voltage range에 따라 고정
- Current 측정에 최적화되지 않음
- 6.48배의 systematic error
```

#### 가능성 3: Hardware Jumper 설정
```
DEFAULT mode는 Hardware Jumper를 따름:

Jumper가 RSE로 설정:
→ Single-ended measurement
→ Ground를 기준으로 측정
→ Common mode voltage 포함
→ 잘못된 결과!

Jumper가 DIFFERENTIAL로 설정:
→ Differential measurement
→ V(+) - V(-) 측정
→ 올바른 Shunt drop
→ 정확한 결과!
```

## 🧪 검증 방법

### 1. Manual 툴의 API 확인

**확인 항목:**
```
□ DAQmxCreateAICurrentChan 사용?
□ DAQmxCreateAIVoltageChan 사용?
□ shuntResistorLoc 설정?
□ Terminal Configuration?
```

### 2. Hardware Jumper 확인

**DAQ 하드웨어 확인:**
```
1. DAQ 장치의 물리적 jumper 위치 확인
2. NI Measurement & Automation Explorer (MAX) 실행
3. Devices and Interfaces → Dev1
4. Device Configuration → Terminal Configuration
5. Jumper 설정 확인: RSE? DIFFERENTIAL?
```

### 3. DoU를 Current Mode로 전환 테스트

**코드 수정:**
```python
# Voltage Mode (현재)
task.ai_channels.add_ai_voltage_chan(...)
voltage = task.read()
current = voltage / shunt_r

# Current Mode (테스트)
task.ai_channels.add_ai_current_chan(
    channel_name,
    min_val=-0.1,
    max_val=0.1,
    units=nidaqmx.constants.CurrentUnits.AMPS,
    shunt_resistor_loc=nidaqmx.constants.CurrentShuntResistorLocation.EXTERNAL,
    ext_shunt_resistor_val=0.005  # 5mΩ
)
current = task.read()  # 직접 전류 값!
```

## 📊 예상 결과

### If Manual uses Current Mode:
```
DoU를 Current Mode로 변경 시:
→ Manual과 동일한 결과 (1.018mA) ✅
→ 6.42배 차이 해소!
```

### If Hardware Jumper가 RSE:
```
Jumper를 DIFFERENTIAL로 변경:
→ Shunt drop만 측정
→ 정확한 전류 계산 ✅
```

## 🎯 결론

**가장 가능성 높은 원인:**

1. **Manual = Current Mode, DoU = Voltage Mode**
   - Manual: DAQ 내부에서 정확히 전류 계산
   - DoU: 수동 계산으로 오차 증폭

2. **Hardware Jumper가 RSE로 설정됨**
   - DEFAULT mode가 RSE처럼 작동
   - Common mode voltage 간섭
   - Shunt drop 측정 오차

**해결 방법:**

1. **DoU를 Current Mode로 전환** (가장 확실)
2. **Hardware Jumper를 DIFFERENTIAL로 변경**
3. **DIFFERENTIAL mode 강제 사용** (10106 constant)

---

## 🔍 다음 단계

1. Manual 툴이 Current Mode를 사용하는지 확인
2. NI MAX에서 Hardware Jumper 설정 확인
3. DoU를 Current Mode로 테스트 실행
4. 결과 비교 및 분석
