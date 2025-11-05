# DoU vs 다른 툴 데이터 차이 분석

## 📊 측정값 비교

### 평균 전류값 비교:
```
Channel          DoU (mA)      다른툴 (mA)     비율
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VBAT             415,916.96    3.74            111,229배
VDD_1P8_AP       17,793.77     0.02            889,689배
VDD_MLDO_2P0     394,868.58    0.00            (무한대)
VDD_WIFI_1P0     201,917.18    0.74            272,861배
VDD_1P2_AP_WIFI  11,782.39     0.17            69,308배
VDD_1P35_WIFIPMU 133,963.72    0.18            744,243배
```

**DoU 값이 약 100,000배 ~ 1,000,000배 큽니다!** ⚠️

---

## 🔍 가능한 원인들

### 1. **Shunt 저항 값 문제** (가능성 높음!)

**현재 DoU 코드:**
```python
shunt_r = config.get('shunt_r', 0.01)  # Default 0.01Ω
current_ma = (voltage / shunt_r) * 1000
```

**만약 실제 shunt가 다르다면:**
```
DoU가 0.01Ω로 계산했는데, 실제는 1Ω이면:
  → 100배 차이
  
DoU가 0.01Ω로 계산했는데, 실제는 10Ω이면:
  → 1,000배 차이
  
DoU가 0.01Ω로 계산했는데, 실제는 100Ω이면:
  → 10,000배 차이
```

---

### 2. **단위 변환 중복 문제**

**의심 코드:**
```python
# 압축 시 이미 변환?
compressed_ma = [(v / shunt_r) * 1000 for v in compressed_volts]

# 또 다시 변환?
result * 1000?
```

---

### 3. **평균 vs 합계**

**압축 로직:**
```python
# _compress_data는 평균을 낸다
def _compress_data(self, data, compress_ratio):
    for i in range(0, len(data), compress_ratio):
        group = data[i:i+compress_ratio]
        avg_value = sum(group) / len(group)  # 평균
        compressed.append(avg_value)
```

**그런데 출력 시 합계를 내고 있을 수도?**

---

## 🎯 확인 필요 사항

### 1. 채널 설정 확인
```
실제 설정된 shunt 저항 값은?
- UI에서 설정한 값
- channel_configs의 실제 값
```

### 2. 콘솔 로그 확인
```
Phone App Test 실행 후 콘솔 출력:

  Avg voltage: ???mV
  Avg current: ???mA
  (shunt=???Ω)
```

### 3. Raw Voltage 값 확인
```
다른 툴: 0.000168257 V = 0.168 mV

DoU는 몇 V 측정?
  - 비슷한 값이면 shunt 문제
  - 완전히 다른 값이면 측정 문제
```

---

## 💡 다른 툴 Trace 분석

### Continuous vs Finite 모드:
```
다른 툴:
  - Continuous Mode
  - 60 samples씩 계속 읽기
  - Sample Rate: 30kHz
  - dt: 33.3 μs (= 1/30000)

DoU:
  - Finite Mode  
  - 300,000 samples 한 번에
  - 30:1 압축 → 10,000 samples
  - Sample Rate: 30kHz
```

### 추가로 확인할 점:
```
7.  setTimingI32EnumAP ("_unnamedTask<3>", "", SampTimingType, Sample Clock, "")
8.  setTimingI32EnumAP ("_unnamedTask<3>", "", SampQuant.SampMode, Continuous Samples, "")
9.  setTimingF64U64AP ("_unnamedTask<3>", "", SampQuant.SampPerChan, 1000.000000 (1.000000E+03), "")
10. setTimingI32EnumAP ("_unnamedTask<3>", "", SampClk.ActiveEdge, Rising, "")
11. setTimingF64AP ("_unnamedTask<3>", "", SampClk.Rate, 30000.000000 (3.000000E+04), "")
12. setTimingTerminalAP ("_unnamedTask<3>", "", SampClk.Src, "OnboardClock", "")
```

특별한 차이는 없어 보입니다.

---

## 🚨 즉시 확인해야 할 것

### 1. 실제 Shunt 저항 값
```python
# Phone App Test 실행 전에
# UI에서 각 채널의 Shunt 값 확인:

ai0 (VBAT):           ???Ω
ai1 (VDD_1P8_AP):     ???Ω
ai2 (VDD_MLDO_2P0):   ???Ω
ai3 (VDD_WIFI_1P0):   ???Ω
ai4 (VDD_1P2_AP_WIFI): ???Ω
ai5 (VDD_1P35_WIFIPMU): ???Ω
```

### 2. Phone App Test 콘솔 출력
```
실행 후 아래 로그 복사:

=== Hardware-Timed VOLTAGE Collection ===
Channels: [...]
...
Channel ai0: ... compressed samples
  Avg voltage: ???mV
  Avg current: ???mA
  (shunt=???Ω)
```

---

## 💡 의심 시나리오

### 시나리오 A: Shunt가 0.01Ω이 아님
```
DoU가 0.01Ω로 계산
실제는 0.0001Ω (0.1mΩ)
→ 100배 차이

또는 실제는 0.00001Ω (0.01mΩ)
→ 1,000배 차이
```

### 시나리오 B: UI 설정이 0.0Ω
```
기본값이 0.0Ω이면:
  config.get('shunt_r', 0.01)  # 0.0이면 default 0.01 사용

하지만 사용자가 설정 안 했으면?
  channel_configs에 shunt_r: 0.0 저장됨
  get()으로 가져오면 0.0 반환
  config.get('shunt_r', 0.01)  # 0.0 반환! (default 사용 안 됨!)
```

**이것이 문제일 가능성!**

```python
# 잘못된 코드
config.get('shunt_r', 0.01)  # key가 있고 값이 0.0이면 0.0 반환!

# 올바른 코드
shunt_r = config.get('shunt_r', 0.01)
if shunt_r == 0:
    shunt_r = 0.01  # Force default if zero
```

---

## ✅ 문제 확인 완료!

### **실제 측정값 (로그에서):**
```
Channel ai0: Avg voltage: 4147.016mV = 4.147V (VBAT Rail!)
Channel ai1: Avg voltage: 1783.222mV = 1.783V (1.8V Rail!)
Channel ai2: Avg voltage: 1976.871mV = 1.977V (2.0V Rail!)
Channel ai3: Avg voltage: 1016.039mV = 1.016V (1.0V Rail!)
```

**DoU는 Power Rail 전압을 측정하고 있습니다!**

---

## ❌ 근본 원인: 하드웨어 연결 문제

### **현재 연결 (잘못됨):**
```
Power Rail ━━━[Shunt 0.01Ω]━━━ Load
     ↓
[DAQ ai0+] (RSE to GND)
     ↓
   [GND]

측정 결과: 4.147V (Rail 전압)
계산: 4147mV / 0.01Ω = 414,700 mA ❌
```

### **올바른 연결:**
```
Power Rail ━━━[Shunt 0.01Ω]━━━ Load
              ↓         ↓
         [DAQ ai0+] [DAQ ai0-]
         (DIFFERENTIAL)

측정 결과: 0.168 mV (Shunt drop)
계산: 0.168mV / 0.01Ω = 16.8 mA ✓
```

---

## 🔧 해결 방법

### **1. 하드웨어 재연결 (필수!)**

**각 채널을 Shunt 양단에 연결:**
```
ai0+: VBAT Shunt 한쪽 (Rail 쪽)
ai0-: VBAT Shunt 다른쪽 (Load 쪽)

ai1+: VDD_1P8_AP Shunt 한쪽
ai1-: VDD_1P8_AP Shunt 다른쪽

... (모든 채널)
```

### **2. DIFFERENTIAL 모드 사용**

코드 수정 완료:
- Terminal Config: RSE → DIFFERENTIAL
- Range: ±5V → ±200mV (shunt drop 범위)

---

## 📋 다음 단계

**1. 하드웨어 재연결 후:**
```
- DAQ ai0+를 Shunt 한쪽에
- DAQ ai0-를 Shunt 다른쪽에
- (모든 채널 동일)
```

**2. 다시 Phone App Test 실행**

**3. 예상 로그:**
```
Channel ai0: Avg voltage: 0.168mV, Avg current: 16.8mA (shunt=0.01Ω) ✓
```

---

## ⚠️ 중요 질문

**다른 툴은 어떻게 연결되어 있나요?**
- 다른 툴도 같은 DAQ 사용?
- 다른 툴도 ai0~ai5 채널 사용?
- 다른 툴은 정상 측정되는데, DoU만 Rail 전압 측정?

→ **하드웨어 연결이 다를 가능성 높음!**
