# 전압 측정값 디버그

**문제:** Shunt Resistor는 동일(0.01Ω)한데 전류값이 20,000배 차이
- 다른 툴: 50mA 이상
- 우리 툴: 0.0025mA

**원인 추정:** 측정되는 전압 값 자체가 다를 가능성

---

## 🔍 디버그 로깅 추가

### 변경 내용
```python
# 모든 채널에서 상세 로그 출력
print(f"🔍 {channel}: RAW_VOLTAGE={voltage:.9f}V ({voltage*1000:.6f}mV) → CURRENT={current:.9f}A ({current*1000:.6f}mA)")
print(f"   Calculation: {voltage:.9f}V / {shunt_r}Ω = {current:.9f}A")
```

### 예상 출력
```
🔍 ai0: RAW_VOLTAGE=0.000088000V (0.088000mV) → CURRENT=0.008800000A (8.800000mA)
   Calculation: 0.000088000V / 0.01Ω = 0.008800000A
```

---

## 📊 비교 분석

### 다른 툴 (NI Trace)
```
측정 전압: 0.088mV (8.8154E-05V)
Shunt: 0.01Ω
전류: 0.088mV / 0.01Ω = 8.8mA ✅
```

### 우리 툴 (예상)
```
만약 전류가 0.0025mA라면:
역계산: 0.0025mA × 0.01Ω = 0.000025mV = 0.025μV ❌
(이렇게 작은 값은 DAQ가 측정 불가능)
```

### 가능한 시나리오

#### 시나리오 1: 전압이 정상 측정되는 경우
```
측정: 0.5mV
계산: 0.5mV / 0.01Ω = 50mA ✅
→ 정상 작동
```

#### 시나리오 2: 전압이 매우 작게 측정되는 경우
```
측정: 0.000025mV (25nV)
계산: 0.000025mV / 0.01Ω = 0.0025mA ❌
→ 문제 있음 (gain, scale factor 등)
```

#### 시나리오 3: 단위가 잘못된 경우
```
측정: 0.00005 (단위?)
만약 μV 단위라면: 0.00005μV → 너무 작음
만약 mV 단위라면: 0.00005mV × 1000 = 0.05mV → 5mA
```

---

## 🧪 테스트 방법

### 1. Phone App Test 실행
```bash
cd /workspace
PYTHONPATH=/workspace python3 test_scenarios/scripts/run_phone_app_scenario.py
```

### 2. 로그 확인
콘솔에서 다음과 같은 로그를 확인:
```
🔍 ai0: RAW_VOLTAGE=0.XXXXXXXXX V (X.XXXXXX mV) → CURRENT=X.XXXXXXXXX A (X.XXXXXX mA)
```

### 3. 예상 범위 확인
- **정상:** 0.001V ~ 0.1V (1mV ~ 100mV)
- **비정상:** < 0.0001V (< 0.1mV) 또는 > 1V

---

## 🎯 다음 단계

### 전압이 정상 범위인 경우 (0.001V ~ 0.1V)
→ 계산 로직이나 단위 변환 문제

### 전압이 너무 작은 경우 (< 0.0001V)
→ DAQ 설정 문제 (gain, scale factor, terminal config)

### 전압이 너무 큰 경우 (> 1V)
→ Hardware 연결 문제 (Rail Voltage 측정 중)

---

## 📝 확인 사항

테스트 실행 후 다음 정보를 확인:
1. **RAW_VOLTAGE 값** (V 단위)
2. **계산된 전류값** (mA 단위)
3. **예상 범위와 비교**

이 정보로 정확한 문제를 진단할 수 있습니다!
