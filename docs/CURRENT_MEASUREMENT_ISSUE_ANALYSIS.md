# 전류 측정 차이 분석: 메뉴얼 vs DoU 툴

**작성일:** 2025-11-10  
**이슈:** Phone App Scenario에서 메뉴얼 측정과 DoU 툴의 전류 측정값이 크게 차이남

---

## 🔍 문제 상황

### 하드웨어 구성
```
Power Rail 6개 (ai0 ~ ai5)
각 rail은 differential pair로 구성:
  [+ai0(rail1), -ai0(rail2)]
  [+ai1(rail3), -ai1(rail4)]
  [+ai2(rail5), -ai2(rail6)]

측정 방식:
  ---(A)---(shunt)---(B)---
  (A) → +ai0
  (B) → -ai0
```

### USB-6289 Differential 입력 구조
```
USB-6289은 16개 single-ended 또는 8개 differential 입력 지원

Differential 모드에서 채널 매핑:
  ai0 = ai0+ (pin) / ai8- (pin)
  ai1 = ai1+ (pin) / ai9- (pin)
  ai2 = ai2+ (pin) / ai10- (pin)
  ai3 = ai3+ (pin) / ai11- (pin)
  ai4 = ai4+ (pin) / ai12- (pin)
  ai5 = ai5+ (pin) / ai13- (pin)
```

### 측정값 차이
```
메뉴얼 측정: 정상 범위 (수 mA ~ 수십 mA)
DoU 툴 측정: 비정상 범위 (수백 A ~ 수천 A)
비율: 약 10,000배 ~ 100,000배 차이
```

---

## 🚨 핵심 문제들

### 1. **DIFFERENTIAL 모드 실패 → RSE Fallback**

**현재 코드 동작:**
```python
# Line 1310-1354 in ni_daq.py
try:
    # DEFAULT 모드 시도
    task.ai_channels.add_ai_voltage_chan(
        channel_name,
        terminal_config=TerminalConfiguration.DEFAULT,
        min_val=-0.2, max_val=0.2  # ±200mV
    )
except:
    try:
        # DIFFERENTIAL 모드 시도
        task.ai_channels.add_ai_voltage_chan(
            channel_name,
            terminal_config=TerminalConfiguration.DIFFERENTIAL,
            min_val=-0.2, max_val=0.2  # ±200mV
        )
    except:
        # RSE로 fallback (문제!)
        task.ai_channels.add_ai_voltage_chan(
            channel_name,
            terminal_config=TerminalConfiguration.RSE,
            min_val=-5.0, max_val=5.0  # ±5V (Rail voltage 범위)
        )
```

**문제점:**
1. DIFFERENTIAL/DEFAULT 실패 시 RSE로 fallback
2. RSE 모드에서는 **Rail Voltage**를 측정 (4.2V 같은 큰 값)
3. 잘못된 전류 계산: 4.2V ÷ 0.01Ω = 420A ❌

### 2. **범위 설정 문제 가능성**

**DIFFERENTIAL 모드가 실패하는 이유:**
```python
min_val=-0.2, max_val=0.2  # ±200mV 범위
```

**가능한 원인:**
1. 실제 shunt 전압이 200mV를 초과할 수 있음
2. 채널 초기화 시 전압 스파이크가 범위를 벗어남
3. 하드웨어가 실제로 differential로 연결되지 않음

### 3. **채널 명명 혼란**

**사용자 설명:**
```
[+ai0(rail1), -ai0(rail2)]
```

**두 가지 해석:**

**해석 A: Single-ended + 수동 차분 계산**
```
ai0 → rail 측 전압 (예: 4.2V)
ai1 → load 측 전압 (예: 4.199V)
차이: 4.2V - 4.199V = 1mV
전류: 1mV / 0.01Ω = 100mA
```

**해석 B: Differential 입력 (올바른 방식)**
```
ai0 = differential pair (ai0+, ai8-)
자동으로 차분 측정
측정값: 1mV (shunt drop)
전류: 1mV / 0.01Ω = 100mA
```

---

## 🔧 가능한 원인들

### 원인 1: 하드웨어가 Single-ended로 연결됨 ⭐⭐⭐

**상황:**
- ai0이 shunt 전 (rail 측)에만 연결
- Ground reference를 통해 측정
- 결과: Rail voltage 직접 측정 (4.2V)

**증거:**
- 문서에 "Channel ai0: Avg voltage: 4147.016mV" 로그 있음
- 이것은 VBAT rail voltage임

**해결:**
- 하드웨어를 differential로 재연결
- 또는 두 채널을 사용하여 소프트웨어로 차분 계산

### 원인 2: DIFFERENTIAL 범위가 너무 작음 ⭐⭐

**상황:**
- ±200mV 범위로 설정
- 실제 측정값이 범위 초과
- DAQ가 DIFFERENTIAL 모드 거부

**해결:**
- 범위를 ±2V 또는 ±5V로 확대
- 실제 shunt 전압 먼저 확인

### 원인 3: 메뉴얼 측정 방식이 다름 ⭐⭐

**상황:**
- 메뉴얼 툴이 다른 측정 방식 사용
- 예: 두 채널을 읽어서 소프트웨어로 차분 계산
- 또는 다른 shunt 저항 값 사용

**해결:**
- 메뉴얼 툴의 설정 확인
- 동일한 방식으로 구현

---

## ✅ 해결 방안

### 방안 1: DIFFERENTIAL 범위 확대 및 재시도

**목적:** DIFFERENTIAL 모드가 실패하지 않도록 범위 확대

```python
# 수정 전
min_val=-0.2, max_val=0.2  # ±200mV

# 수정 후
min_val=-2.0, max_val=2.0  # ±2V (shunt drop + 마진)
```

**장점:**
- 간단한 수정
- Differential 모드 성공 가능성 증가

**단점:**
- 정밀도 약간 감소 (하지만 여전히 충분함)

### 방안 2: 두 채널 사용하여 차분 계산

**목적:** 하드웨어가 differential이 아닐 경우 대비

```python
# ai0과 ai1을 각각 읽어서 차분 계산
with nidaqmx.Task() as task:
    # Rail 측 (shunt 전)
    task.ai_channels.add_ai_voltage_chan(
        f"{device}/ai0",
        terminal_config=TerminalConfiguration.RSE,
        min_val=-5.0, max_val=5.0
    )
    # Load 측 (shunt 후)  
    task.ai_channels.add_ai_voltage_chan(
        f"{device}/ai1",
        terminal_config=TerminalConfiguration.RSE,
        min_val=-5.0, max_val=5.0
    )
    
    data = task.read()
    v_rail = data[0]  # 예: 4.200V
    v_load = data[1]  # 예: 4.199V
    shunt_drop = v_rail - v_load  # 1mV
    current = shunt_drop / shunt_r  # 100mA
```

**장점:**
- 하드웨어 연결에 유연
- 명확한 차분 계산

**단점:**
- 채널 2배 사용 (6개 rail → 12개 채널 필요)
- 동기화 문제 가능성

### 방안 3: 채널 매핑 재구성

**목적:** 사용자가 설명한 구조에 정확히 맞춤

**만약 실제 연결이 이렇다면:**
```
ai0+ → VBAT shunt 전
ai8- → VBAT shunt 후 (ground referenced)
ai1+ → VDD_1P8_AP shunt 전
ai9- → VDD_1P8_AP shunt 후
...
```

**코드:**
```python
# ai0을 differential로 읽으면 자동으로 ai0+와 ai8-의 차이 측정
task.ai_channels.add_ai_voltage_chan(
    f"{device}/ai0",
    terminal_config=TerminalConfiguration.DIFFERENTIAL,
    min_val=-2.0, max_val=2.0
)
```

---

## 🧪 진단 방법

### 단계 1: RSE 모드로 각 채널의 절대 전압 확인

```python
# ai0, ai1, ai2... 각각 RSE로 읽기
for ch in ['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5']:
    voltage = read_channel_RSE(ch, range=10.0)
    print(f"{ch}: {voltage}V")

# 예상 결과 A (Single-ended 연결):
# ai0: 4.200V (VBAT rail)
# ai1: 1.800V (VDD_1P8_AP rail)
# ai2: 2.000V (VDD_MLDO_2P0 rail)
# ...

# 예상 결과 B (Differential의 한쪽만):
# ai0: 0.001V (shunt 한쪽만 측정, 의미 없음)
# ...
```

### 단계 2: DIFFERENTIAL 모드 시도 및 실패 원인 확인

```python
# 넓은 범위로 DIFFERENTIAL 시도
try:
    task.ai_channels.add_ai_voltage_chan(
        f"{device}/ai0",
        terminal_config=TerminalConfiguration.DIFFERENTIAL,
        min_val=-10.0, max_val=10.0  # 매우 넓은 범위
    )
    voltage = task.read()
    print(f"DIFFERENTIAL 성공: {voltage}V")
except Exception as e:
    print(f"DIFFERENTIAL 실패: {e}")
```

### 단계 3: 두 채널 차분 측정 시도

```python
# ai0과 ai1을 RSE로 읽어서 차분 계산
with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan(f"{device}/ai0", ...)
    task.ai_channels.add_ai_voltage_chan(f"{device}/ai1", ...)
    data = task.read()
    diff = data[0] - data[1]
    print(f"ai0={data[0]}V, ai1={data[1]}V, diff={diff}V")
    
# 예상 결과:
# ai0=4.200V, ai1=4.199V, diff=0.001V  → 이게 shunt drop
```

---

## 📊 메뉴얼 툴 설정 확인 필요

다음 정보를 확인해주세요:

### 1. 메뉴얼 툴의 DAQ 설정
```
- [ ] Terminal Configuration: DIFFERENTIAL? RSE? NRSE?
- [ ] Voltage Range: ±200mV? ±2V? ±5V?
- [ ] 채널 사용: ai0~ai5만? 아니면 ai0~ai11?
```

### 2. 메뉴얼 툴의 Shunt 저항 설정
```
- [ ] ai0 (VBAT): ???Ω
- [ ] ai1 (VDD_1P8_AP): ???Ω
- [ ] ai2 (VDD_MLDO_2P0): ???Ω
- [ ] ai3 (VDD_WIFI_1P0): ???Ω
- [ ] ai4 (VDD_1P2_AP_WIFI): ???Ω
- [ ] ai5 (VDD_1P35_WIFIPMU): ???Ω
```

### 3. 메뉴얼 툴의 측정 결과 (raw voltage)
```
- [ ] ai0 raw voltage: ???mV
- [ ] ai1 raw voltage: ???mV
...
```

---

## 💡 즉시 확인 가능한 테스트

### 테스트 1: 현재 측정값 확인
```python
# DoU 실행 후 콘솔 로그 확인
# "Avg voltage: ???mV" 부분

예상 A (잘못된 경우): 4200mV (rail voltage)
예상 B (올바른 경우): 0.1mV ~ 10mV (shunt drop)
```

### 테스트 2: 범위 확대 후 재테스트
```python
# ni_daq.py Line 1313 수정
min_val=-0.2, max_val=0.2
→
min_val=-5.0, max_val=5.0

# 재실행 후 DIFFERENTIAL 모드 성공 여부 확인
```

### 테스트 3: 메뉴얼 툴과 DoU 동시 실행
```
1. 메뉴얼 툴로 측정 시작
2. DoU로 측정 시작  
3. 두 결과를 실시간으로 비교
4. 어느 시점부터 차이가 나는지 확인
```

---

## 🎯 권장 조치 순서

### 1단계: DIFFERENTIAL 범위 확대 (5분)
```python
# ni_daq.py Line 1313, 1327, 1339 수정
min_val=-0.2, max_val=0.2
→
min_val=-2.0, max_val=2.0
```

### 2단계: 테스트 실행 및 로그 확인 (10분)
```bash
# Phone App Test 실행
# 콘솔에서 다음 메시지 확인:
# "→ DIFFERENTIAL mode enabled"  ← 성공!
# "Avg voltage: ???mV"            ← shunt drop 확인
```

### 3단계: 메뉴얼 툴 설정 비교 (15분)
```
- 메뉴얼 툴의 설정 화면 캡처
- DoU 설정과 비교
- 차이점 확인
```

### 4단계: 필요시 채널 매핑 재구성 (30분)
```
- 하드웨어 연결 확인
- 두 채널 차분 계산 구현
- 또는 differential 채널 올바르게 매핑
```

---

## 📝 결론

**가장 가능성 높은 원인:**
1. ⭐⭐⭐ **DIFFERENTIAL 모드 실패 → RSE fallback → Rail voltage 측정**
2. ⭐⭐ **범위 설정(±200mV)이 너무 작아서 DIFFERENTIAL 실패**
3. ⭐ **하드웨어가 실제로 differential이 아닌 single-ended 연결**

**즉시 시도 가능한 해결책:**
1. DIFFERENTIAL 범위를 ±2V로 확대
2. 실패 시 두 채널 차분 계산 방식으로 변경
3. 메뉴얼 툴 설정과 비교하여 동일하게 구현

**추가 정보 필요:**
- 메뉴얼 툴의 DAQ 설정 (Terminal Config, Range)
- 메뉴얼 툴의 raw voltage 값
- DoU 실행 시 정확한 에러 메시지
