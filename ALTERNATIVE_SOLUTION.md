# nidaq32.dll 없이 해결하는 방법

## 🎯 핵심 질문

**다른 툴이 정말 Traditional DAQ API를 사용하나요?**

### 확인 방법:

#### 1. 다른 툴의 DLL 확인
```bash
# 다른 툴이 사용하는 DLL 확인
# Process Explorer 또는 Dependency Walker 사용

다른 툴 실행 중:
  - nidaqmx.dll 사용? → DAQmx API!
  - nidaq32.dll 사용? → Traditional DAQ API
```

#### 2. 다른 툴의 NI I/O Trace 재확인
```
이전에 본 Trace:
  DAQCreateAIVoltageChan(...)  ← 이게 Traditional?
  
아니면:
  DAQmxCreateAIVoltageChan(...) ← DAQmx?

함수 이름에 "mx" 있으면 → DAQmx!
```

---

## 💡 가능성 1: 다른 툴도 DAQmx 사용

**만약 다른 툴도 DAQmx를 사용한다면:**

문제는 API가 아니라 **설정 차이**!

### 확인할 것:

#### A. Calibration 적용 여부
```python
# 다른 툴은 Calibration 적용?
device = nidaqmx.system.Device("Dev1")
device.self_cal()  # Self-calibration
```

#### B. Scale 설정
```python
# 다른 툴이 Custom Scale 사용?
# Register = 1 = Scale factor?
```

#### C. Sampling/Averaging 차이
```python
# 다른 툴의 샘플링 방식:
- 샘플 수
- 평균 방법
- Filtering
```

---

## 💡 가능성 2: Shunt 저항 값 차이

**실제 하드웨어 Shunt 저항이 다를 수 있음!**

### 테스트 방법:

#### 1. 멀티미터로 실측
```
VBAT 채널 Shunt 저항:
  - DoU 설정: 0.01Ω
  - 실제 측정: ???Ω
  
만약 실제가 0.032Ω라면:
  0.013mV / 0.032Ω = 0.406mA ✓
```

#### 2. 역산으로 확인
```
DoU Voltage:    0.013mV (측정값)
Manual Current: 0.409mA (측정값)

역산:
  Shunt = V / I
  Shunt = 0.013mV / 0.409mA
  Shunt = 0.0318Ω ≈ 0.032Ω

→ 실제 Shunt가 0.032Ω일 가능성!
```

---

## 💡 가능성 3: Terminal Configuration

**DEFAULT가 실제로 어떻게 동작하는지 확인!**

### 테스트:

#### 명시적으로 모든 모드 테스트
```python
# Test 1: DEFAULT
terminal_config = TerminalConfiguration.DEFAULT

# Test 2: DIFFERENTIAL
terminal_config = TerminalConfiguration.DIFFERENTIAL

# Test 3: RSE
terminal_config = TerminalConfiguration.RSE

# Test 4: NRSE
terminal_config = TerminalConfiguration.NRSE

# 어느 것이 Manual과 일치하는가?
```

---

## 🔧 즉시 시도할 수 있는 해결책

### 해결책 1: Shunt 저항 값 수정

**DoU 설정을 역산된 값으로 변경:**

```python
# Before
'ai0': {'shunt_r': 0.01}  # VBAT

# After (역산 결과)
'ai0': {'shunt_r': 0.032}  # VBAT

# 계산:
0.013mV / 0.032Ω = 0.406mA ≈ 0.409mA ✓
```

**파일:** `test_scenarios/configs/wifi_config.py`

---

### 해결책 2: Calibration 적용

**측정 전 Calibration:**

```python
# ni_daq.py에 추가
def connect_device(self, device_name, channel):
    # ... 기존 코드 ...
    
    # Self-calibration 수행
    try:
        device_obj.self_cal()
        print("✓ Device calibration completed")
    except:
        print("⚠️ Calibration failed")
    
    # ... 나머지 코드 ...
```

---

### 해결책 3: 다른 툴 설정 파일 확인

**다른 툴의 설정 파일에서:**
```
[VBAT]
Channel=ai0
Shunt=???  ← 이 값!
Range=???
TerminalConfig=???
```

---

## 🎯 추천하는 즉시 조치

### 1단계: Shunt 저항 값 수정 (가장 가능성 높음!)

```python
# test_scenarios/configs/wifi_config.py 수정

# 역산된 값으로 변경:
'ai0': 0.032Ω  # VBAT (was 0.01)
'ai1': ???Ω    # VDD_1P8_AP
...
```

**계산식:**
```
실제 Shunt = (DoU Voltage) / (Manual Current)

VBAT:
  0.013mV / 0.409mA = 0.0318Ω ≈ 0.032Ω

VDD_1P8_AP:
  (DoU Voltage) / 0.365mA = ???Ω
```

---

### 2단계: 테스트

```bash
python test_scenarios/scripts/run_phone_app_scenario.py
```

**예상 결과:**
```
VBAT:
  DoU:    0.409mA  ✓ (Shunt 0.032Ω 사용)
  Manual: 0.409mA
  → 일치!
```

---

## 🔍 다른 툴 분석 재요청

**확인해주세요:**

### A. 다른 툴이 사용하는 DLL
```
Process Explorer로 확인:
  - nidaqmx.dll? → DAQmx
  - nidaq32.dll? → Traditional DAQ
```

### B. 다른 툴의 Shunt 설정
```
설정 파일 또는 UI에서:
  VBAT Shunt = ???Ω
```

### C. 다른 툴의 Voltage 측정값
```
다른 툴이 측정한 Voltage:
  VBAT = ???mV
  (DoU: 0.013mV)
  
같은가? 다른가?
```

---

## 📊 비교 표

| 채널 | DoU Voltage | Manual Current | 계산된 Shunt | DoU 설정 Shunt |
|------|-------------|----------------|--------------|----------------|
| VBAT | 0.013mV | 0.409mA | **0.032Ω** | 0.01Ω |
| VDD_1P8_AP | ?mV | 0.365mA | ?Ω | 0.1Ω |
| VDD_MLDO_2P0 | ?mV | -0.173mA | ?Ω | 0.1Ω |
| VDD_WIFI_1P0 | ?mV | 1.709mA | ?Ω | 0.005Ω |
| VDD_1P2_AP_WIFI | ?mV | 0.149mA | ?Ω | 0.05Ω |
| VDD_1P35_WIFIPMU | ?mV | 0.759mA | ?Ω | 0.05Ω |

**→ DoU의 실제 Voltage 측정값을 알려주시면 모든 채널의 정확한 Shunt 계산 가능!**

---

## ✅ 결론

**nidaq32.dll 없어도 해결 가능!**

**가장 가능성 높은 해결책:**
1. **Shunt 저항 값이 실제와 다름**
2. Shunt 값을 역산된 값(0.032Ω)으로 수정
3. 테스트 → Manual과 일치!

**필요한 정보:**
- 다른 툴의 Shunt 설정값
- 또는 DoU의 실제 Voltage 측정값 (모든 채널)
