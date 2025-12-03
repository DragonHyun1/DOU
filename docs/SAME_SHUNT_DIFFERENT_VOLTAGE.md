# 동일 Shunt, 다른 전압 측정 분석

**날짜:** 2025-11-10  
**확인:** Manual과 DoU 모두 동일한 Shunt 저항 사용  
**문제:** 하지만 측정 전류가 2~68배 차이

---

## 📊 핵심 데이터

### 측정값 비교
| 채널 | DoU 전압 | DoU 전류 | Manual 전류 | Shunt | 비율 |
|------|----------|----------|-------------|-------|------|
| ai0 | -0.003mV | -0.337mA | 0.08mA | 0.01Ω | 4.2배 |
| ai1 | 0.079mV | 0.789mA | 0.4mA | 0.1Ω | 2.0배 |
| ai2 | -0.009mV | -1.786mA | -0.77mA | 0.005Ω | 2.3배 |
| ai3 | 0.033mV | 6.533mA | 1.018mA | 0.005Ω | 6.4배 |
| ai4 | 0.034mV | 0.337mA | 0.14mA | 0.1Ω | 2.4배 |
| ai5 | 0.030mV | 2.984mA | 0.044mA | 0.01Ω | 67.8배 |

### Manual의 "실제" 측정 전압 역산

**I = V / R 공식으로 역산:**
```
Manual ai3 전압 = 1.018mA × 0.005Ω = 0.00509mV

DoU ai3 전압 = 0.033mV

비율 = 0.033 / 0.00509 = 6.48배!
```

---

## 🚨 핵심 발견

### DoU의 전압 측정이 Manual보다 크다!

**같은 Shunt, 같은 하드웨어인데 DoU가 더 큰 전압을 측정:**

| 채널 | DoU 측정 전압 | Manual 역산 전압 | 전압 비율 |
|------|---------------|------------------|-----------|
| ai0 | 0.003mV | 0.0008mV | 3.75배 |
| ai1 | 0.079mV | 0.040mV | 1.98배 |
| ai2 | 0.009mV | 0.00385mV | 2.34배 |
| ai3 | 0.033mV | 0.00509mV | 6.48배 |
| ai4 | 0.034mV | 0.014mV | 2.43배 |
| ai5 | 0.030mV | 0.00044mV | 68.2배 |

**패턴:** 채널마다 전압 증폭 비율이 다름!

---

## 🔍 가능한 원인들

### 원인 1: Terminal Configuration 차이 ⭐⭐⭐

**DoU:**
```
DEFAULT mode (하드웨어 jumper 따름)
결과적으로 differential 측정
```

**Manual:**
```
명시적인 DIFFERENTIAL 설정?
또는 다른 측정 방식?
```

**차이점:**
- DEFAULT는 하드웨어 jumper에 의존
- 실제 differential이 아닐 수도?
- 또는 reference point가 다를 수도?

### 원인 2: 측정 범위(Range) 차이 ⭐⭐⭐

**DoU:**
```python
min_val=-5.0, max_val=5.0  # ±5V
```

**Manual:**
```
±5V? 또는 다른 범위?
```

**중요:** 
- 범위가 다르면 ADC scaling이 달라짐
- 하지만 채널별로 비율이 다른 것을 설명 못함

### 원인 3: 하드웨어 연결 차이 ⭐⭐⭐

**가능성 A: 다른 측정 포인트**
```
DoU:    Shunt의 특정 포인트 (A-B)
Manual: Shunt의 다른 포인트 (C-D)

예:
Rail ━━(A)━━[Shunt]━━(B)━━ Load
           ↓        ↓
       [측정1]   [측정2]
```

**가능성 B: Ground reference 차이**
```
DoU:    Ground-referenced measurement
Manual: True differential measurement
```

### 원인 4: 채널 페어링 차이 ⭐⭐⭐

**USB-6289 Differential 채널 매핑:**
```
ai0 = ai0+ / ai8-
ai1 = ai1+ / ai9-
ai2 = ai2+ / ai10-
ai3 = ai3+ / ai11-
ai4 = ai4+ / ai12-
ai5 = ai5+ / ai13-
```

**DoU:**
```
DEFAULT mode → 하드웨어 jumper 따름
혹시 잘못된 페어링?
예: ai0가 ai0+ / ai1- 로 측정?
```

**Manual:**
```
명시적 페어링 설정?
```

### 원인 5: 증폭/감쇠 회로 ⭐

**DoU 경로:**
```
Shunt → [증폭기?] → DAQ
```

**Manual 경로:**
```
Shunt → DAQ
```

**또는:**
```
둘 다 같은 경로인데 설정이 다름
```

---

## 🧪 진단 방법

### 테스트 1: Manual의 원시(raw) 전압 확인

**가장 중요! Manual 툴에서 raw 전압을 확인할 수 있나요?**

```
Manual ai3 측정 전압: _____mV

만약 0.00509mV라면:
  → Manual이 더 작은 전압 측정
  → DoU가 증폭되어 있음

만약 0.033mV라면:
  → 전압은 동일
  → 계산 방식이 다름
  → Shunt 값을 다르게 적용?
```

### 테스트 2: DoU Terminal Mode 명시적 설정

**현재 DEFAULT mode를 DIFFERENTIAL로 명시:**

```python
# DEFAULT 대신 명시적 DIFFERENTIAL 시도
# (이미 코드에 있지만 AttributeError로 실패)

# 또는 NRSE, RSE 등 다른 mode 시도
```

### 테스트 3: 하드웨어 연결 확인

**각 채널이 어떻게 연결되어 있는지:**

```
ai3 예시:
  ai3+ (pin?) → Shunt 앞단?
  ai11- (pin?) → Shunt 뒷단?
  
Manual도 동일하게 연결?
```

### 테스트 4: 동시 측정 비교

**Manual과 DoU를 동시에 실행:**
```
같은 순간에 측정하면 같은 값이어야 함
만약 다르다면 측정 방식 차이
```

---

## 💡 가장 가능성 높은 시나리오

### 시나리오 A: DEFAULT mode가 True Differential이 아님

**DoU DEFAULT mode:**
```
하드웨어 jumper 따름
하지만 실제로는 pseudo-differential?
또는 ground-referenced?
```

**Manual:**
```
True differential measurement
정확한 (V+ - V-) 측정
```

**결과:**
```
DoU가 더 큰 전압 측정
→ 더 큰 전류 계산
```

### 시나리오 B: 채널별 하드웨어 이슈

**ai5가 68배 차이나는 이유:**
```
ai5의 연결이 잘못됨
또는 ai5의 증폭기/스케일링 설정이 다름
```

**ai3가 6.4배 차이나는 이유:**
```
ai3의 특별한 설정?
또는 ai3의 측정 경로 문제?
```

---

## 🔧 해결 시도

### 시도 1: 다양한 Terminal Configuration 테스트

코드를 수정하여 각 모드를 순차적으로 테스트:

```python
# 1. DIFFERENTIAL (이미 실패함)
# 2. DEFAULT (현재 사용 중)
# 3. NRSE 
# 4. RSE
# 5. 직접 상수 10106

각각 테스트하여 Manual과 가장 가까운 모드 찾기
```

### 시도 2: Voltage Range 조정

```python
# 현재: ±5V
# 테스트: ±2V, ±1V, ±0.2V 등

더 작은 range = 더 높은 해상도
하지만 scaling 영향도 있음
```

### 시도 3: Manual 설정 그대로 복사

**Manual 툴의 정확한 설정 확인:**
```
1. Terminal Configuration
2. Voltage Range
3. Sampling Rate
4. 기타 DAQ 설정
```

**DoU를 Manual과 100% 동일하게 설정**

---

## 📋 즉시 확인 필요 사항

### 우선순위 1: Manual의 원시 전압 ⭐⭐⭐

**Manual 툴에서 ai3의 측정 전압 확인:**
```
ai3 측정 전압: _____mV

DoU는 0.033mV 측정했음
Manual이 얼마를 측정했는지가 핵심!
```

### 우선순위 2: Manual Terminal Configuration ⭐⭐⭐

**Manual 툴 설정:**
```
Terminal Config: 
□ DIFFERENTIAL
□ RSE
□ NRSE
□ DEFAULT
□ 기타: _____
```

### 우선순위 3: Manual 전체 설정 ⭐⭐

**Manual 툴의 DAQ 설정:**
```
1. Voltage Range: ±_____V
2. Sampling Rate: _____Hz
3. Sample Mode: Finite / Continuous
4. Samples per Channel: _____
```

### 우선순위 4: 하드웨어 연결 확인 ⭐

**물리적 연결:**
```
ai3+ (DAQ pin #) → Shunt의 어느 포인트?
ai11- (DAQ pin #) → Shunt의 어느 포인트?

Manual도 동일한 pin에 연결?
```

---

## 🎯 예상 해결 방향

### 만약 Manual 전압이 0.00509mV라면:

**DoU가 6.48배 증폭되어 측정 중**
```
원인: Terminal configuration 또는 측정 경로 차이
해결: Manual과 동일한 설정 적용
```

### 만약 Manual 전압도 0.033mV라면:

**전압은 동일, 계산이 다름**
```
원인: Shunt 값을 다르게 적용?
       또는 단위 변환 차이?
해결: 계산 로직 확인
```

---

## 📝 요약

**확인된 사실:**
- Shunt 저항은 동일 ✓
- 하지만 DoU가 더 큰 전압 측정
- 채널별로 증폭 비율이 다름

**핵심 질문:**
1. Manual이 측정한 ai3 전압은? (DoU: 0.033mV)
2. Manual의 Terminal Configuration은?
3. Manual의 전체 DAQ 설정은?

**이 정보로 정확한 원인을 찾아 해결하겠습니다!** 🔍

특히 **Manual이 측정한 원시 전압 값**이 가장 중요합니다!
