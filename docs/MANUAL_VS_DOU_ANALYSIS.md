# DoU vs Manual 데이터 비교 분석

## 📊 측정값 차이

### 평균 전류 비교 (mA):
```
Channel          DoU       Manual    비율      차이
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VBAT             1.256     0.409     3.07배    +0.847
VDD_1P8_AP       0.916     0.365     2.51배    +0.551
VDD_MLDO_2P0     0.517    -0.173     음수!     +0.690
VDD_WIFI_1P0     9.723     1.709     5.69배    +8.014
VDD_1P2_AP_WIFI  0.449     0.149     3.01배    +0.300
VDD_1P35_WIFIPMU 4.605     0.759     6.07배    +3.846
```

**DoU가 약 2.5~6배 더 큽니다!**

---

## 🔍 가능한 원인

### 1. Shunt 저항 값 차이 ⭐ (가능성 높음!)

**현재 DoU UI 설정:**
```
ai0 (VBAT):           0.01Ω
ai1 (VDD_1P8_AP):     0.1Ω
ai2 (VDD_MLDO_2P0):   0.005Ω
ai3 (VDD_WIFI_1P0):   0.005Ω
ai4 (VDD_1P2_AP_WIFI): 0.1Ω
ai5 (VDD_1P35_WIFIPMU): 0.01Ω
```

**다른 툴의 Shunt 값은?**
```
확인 필요:
- 다른 툴 설정 화면에서 각 채널의 Shunt 값
- DoU와 같은가? 다른가?
```

**예시:**
```
만약 DoU가 0.01Ω, 다른 툴이 0.03Ω 사용:
  DoU:    V / 0.01 = 3배 큰 전류
  Manual: V / 0.03 = 1배 전류
  비율:   3배 차이 ✓
```

---

### 2. 샘플링 구간 차이

**DoU:**
```
전체 10초 데이터 평균
Time: 0ms ~ 10,000ms
Samples: 10,000개 모두 평균
```

**다른 툴(Manual):**
```
특정 구간만 평균?
Time: 1,000ms ~ 10,000ms? (초반 제외?)
Samples: 일부만 평균?
```

**확인 필요:**
- 다른 툴이 전체 평균인가?
- 특정 구간 평균인가?

---

### 3. 압축 방식 차이

**DoU:**
```python
# 30:1 압축 (30개 평균)
compressed = sum(group) / 30
```

**다른 툴:**
```
# 다른 압축 방식?
# RMS? Median? Peak?
```

---

### 4. Voltage Range 차이

**현재 DoU (DEFAULT 실패 후 RSE):**
```python
min_val=-5.0
max_val=5.0
→ ±5V range
```

**다른 툴:**
```
±5V range (동일)
```

하지만 DEFAULT 모드가 실패했다는 것이 문제!

---

## 🚨 핵심 문제: DEFAULT 모드 실패

**이전 로그:**
```
⚠️ DIFFERENTIAL failed: DIFFERENTIAL, falling back to RSE
```

**이것은 DEFAULT도 실패했다는 의미!**

---

## 🔧 확인 필요 사항

### 1. 최신 코드로 테스트했나요?
```bash
git pull origin DEV
# DoU 재시작
# Phone App Test 실행
```

### 2. 최신 로그 확인
```
Adding VOLTAGE channel: Dev1/ai0 (VBAT)
  → DEFAULT mode (following hardware jumper settings)  ← 이 메시지?
  
또는

  ⚠️ DEFAULT failed: ... ← 에러 메시지?
```

### 3. 다른 툴의 Shunt 값
```
다른 툴 설정 화면에서:
ai0: ???Ω
ai1: ???Ω
ai2: ???Ω
ai3: ???Ω
ai4: ???Ω
ai5: ???Ω
```

### 4. 다른 툴의 평균 계산 방식
```
- 전체 평균? (0~10초)
- 구간 평균? (예: 2~10초)
- 다른 통계? (median, RMS, etc.)
```

---

## 💡 빠른 테스트: Shunt 값 변경

**임시로 DoU의 Shunt 값을 3배로 해보면:**
```
ai0: 0.01Ω → 0.03Ω
ai1: 0.1Ω → 0.3Ω
...

그러면 전류가 1/3로 줄어듦
→ 다른 툴과 비슷해질까?
```

---

**이 정보들을 확인해주시면 정확한 원인을 찾을 수 있습니다!** 🎯