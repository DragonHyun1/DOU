# NI DAQ API 버전 차이 분석

## API 아키텍처 비교

### Traditional DAQ API (다른 툴)
```c
// Legacy NI-DAQ API (circa 2000s)
DAQCreateAIVoltageChan(
    taskHandle,
    "Dev1/ai0",
    DAQ_DEFAULT,        // -1 = 하드웨어 점퍼 따름
    -0.2, 0.2,
    DAQ_Volts,
    NULL                // Custom scaling 없음
);

DAQControl(taskHandle, DAQ_Start);
DAQReadNChanNSamp1DWfm(taskHandle, ...);
```

**특징:**
- 하드웨어 중심 (Hardware-centric)
- 점퍼/스위치 설정 우선
- 간단한 API
- Custom Scaling은 별도 처리

---

### DAQmx API (DoU - 현재 툴)
```python
# Modern NI-DAQmx API (2003+)
task.ai_channels.add_ai_voltage_chan(
    "Dev1/ai0",
    terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
    min_val=-0.2,        # 소프트웨어 Range 명시
    max_val=0.2,
    units=nidaqmx.constants.VoltageUnits.VOLTS
)

task.timing.cfg_samp_clk_timing(
    rate=30000,
    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
    samps_per_chan=300000
)

task.start()
data = task.read(number_of_samples_per_channel=300000)
```

**특징:**
- 소프트웨어 중심 (Software-centric)
- 명시적 설정 필요
- 복잡하지만 유연
- Custom Scaling은 Scale 객체로 처리

---

## 🔥 핵심 차이점

### 1. Range/Gain 설정

#### Traditional DAQ:
```
하드웨어가 자동 선택:
- 측정 범위에 맞는 최적 Gain 자동 선택
- PGA (Programmable Gain Amplifier) 하드웨어 제어
```

#### DAQmx:
```python
# 소프트웨어에서 명시적 설정
min_val=-0.2, max_val=0.2  # → 하드웨어 Gain 설정됨
```

**문제 가능성:**
```
DoU: min_val=-0.2, max_val=0.2 설정
→ DAQ 하드웨어: "0.2V 레인지로 Gain 설정"
→ 실제 신호: 0.013mV (0.2V보다 훨씬 작음)
→ ADC Resolution 낭비? 또는 다른 Scaling?
```

---

### 2. Custom Scaling

#### Traditional DAQ:
```c
// Custom Scale 생성 (선형 변환)
CreateLinearScale(
    "MyScale",
    1.0,              // Slope (Register?)
    0.0,              // Offset
    DAQ_Volts,        // PreScaled Units
    "Current"         // Scaled Units
);

// 채널에 적용
DAQCreateAIVoltageChan(
    ...,
    "MyScale"         // Custom Scale 적용
);
```

**→ "Register = 1" = Slope?**

#### DAQmx:
```python
# Scale 객체 생성
scale = nidaqmx.scale.Scale("MyScale")
scale.create_linear_scale(
    slope=1.0,
    offset=0.0,
    prescaled_units=nidaqmx.constants.UnitsPreScaled.VOLTS,
    scaled_units="Current"
)

# 채널에 적용
task.ai_channels.add_ai_voltage_chan(..., custom_scale_name="MyScale")
```

**DoU는 Custom Scale 사용하지 않음!**
**→ Python 코드에서 직접 계산: `I = V / R`**

---

### 3. Terminal Configuration

#### Traditional DAQ:
```c
DAQ_DEFAULT = -1  // 하드웨어 점퍼 설정 따름
DAQ_RSE = 0
DAQ_NRSE = 1
DAQ_DIFFERENTIAL = 2
```

#### DAQmx:
```python
TerminalConfiguration.DEFAULT  # 하드웨어 따름 (성공!)
TerminalConfiguration.RSE
TerminalConfiguration.NRSE
TerminalConfiguration.DIFF
```

**이건 이미 해결됨 (DEFAULT 사용 중)**

---

## 🚨 의심되는 시나리오

### 시나리오 1: Range/Gain 차이

**다른 툴 (Traditional DAQ):**
```
1. 0.013mV 신호 감지
2. 하드웨어가 최적 Gain 자동 선택 (예: 100x)
3. ADC에 1.3mV로 증폭되어 입력
4. 소프트웨어가 Gain 보정 (÷100)
5. Custom Scale 적용 (Register = 1)
```

**DoU (DAQmx):**
```
1. min_val=-0.2, max_val=0.2 설정
2. 하드웨어가 0.2V Range용 Gain 설정 (예: 10x)
3. 0.013mV 신호 → 0.00013V로 ADC 입력
4. 소프트웨어가 Range 보정
5. Python에서 Shunt 계산 (÷0.01)

→ Gain 차이로 인한 Scaling 오차?
```

---

### 시나리오 2: Custom Scale 누락

**다른 툴:**
```c
Voltage 측정: 0.013mV
Custom Scale (Register=1): 0.013mV * 1 = 0.013
단위 변환: ??? → 0.409mA

// Custom Scale이 단순 곱셈이 아니라
// 복잡한 보정 공식일 수 있음!
```

**DoU:**
```python
Voltage 측정: 0.013mV
Shunt 계산: 0.013mV / 0.01Ω = 1.3mA (10배 차이!)
```

---

### 시나리오 3: Shunt 저항 하드코딩

**다른 툴:**
```
Register = 1 = Gain/Scale Factor
실제 Shunt = 0.032Ω (하드웨어 고정?)

Voltage: 0.013mV
Current: 0.013mV / 0.032Ω = 0.406mA ✓
```

**DoU:**
```
Shunt = 0.01Ω (설정 파일)
Current: 0.013mV / 0.01Ω = 1.3mA (3배 차이)
```

---

## 🎯 확인 방법

### 1. DAQmx Range 최적화

**현재 코드:**
```python
min_val=-0.2, max_val=0.2  # 0.2V Range
```

**테스트:**
```python
# 더 작은 Range 시도
min_val=-0.01, max_val=0.01  # 10mV Range
# 또는
min_val=-0.001, max_val=0.001  # 1mV Range
```

**예상:**
- Range를 줄이면 ADC Resolution 향상
- 측정값이 달라질 수 있음

---

### 2. NI MAX에서 확인

**NI Measurement & Automation Explorer:**
```
1. Devices and Interfaces → Dev1
2. Test Panels → Analog Input
3. ai0 채널 선택
4. Settings:
   - Terminal Configuration: DEFAULT
   - Input Range: Auto vs Manual
   - Gain: 확인
5. 실제 Voltage 측정값 확인
```

**비교:**
```
NI MAX 측정값: ???mV
DoU 측정값:    0.013mV
다른 툴 계산:  0.409mA → 0.004mV? (0.01Ω 가정)
```

---

### 3. 다른 툴의 내부 설정 확인

**다른 툴이 사용하는 실제 값:**
```
1. Config 파일 확인
2. Log 파일 확인 (Voltage 측정값)
3. API Trace 확인
```

---

## 📚 다음 단계

1. **NI-DAQmx 문서 깊이 분석**
   - Range vs Gain
   - Custom Scaling
   - Best Practices for Low Voltage

2. **NI MAX 테스트**
   - ai0에서 실제 Voltage 확인
   - Range 변경 테스트

3. **다른 툴 역공학**
   - Voltage 측정값 찾기
   - Config/Log 파일 분석

4. **DoU Range 최적화**
   - 더 작은 Range 시도
   - Auto Range 테스트

---

**이 중 어떤 것부터 시작할까요?**
