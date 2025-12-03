# Calibration 검증 계획

**목적:** 현재 calibration이 다른 시나리오에서도 유효한지 확인

---

## 🧪 검증 시나리오

### 시나리오 1: Phone App (현재)
```
측정 범위: 0.08 ~ 6.5mA
Calibration 적용: ✓
Manual 비교: ✓ 일치함
```

### 시나리오 2: WiFi Heavy Load (필수)
```
예상 범위: 50 ~ 200mA
목적: 고전류 범위에서 calibration 검증

테스트:
1. Manual 툴로 측정
2. DoU로 측정 (calibration 적용)
3. 비교

예상 결과 A (선형적):
  DoU = Manual ✓
  → Calibration 유효!
  
예상 결과 B (비선형적):
  DoU ≠ Manual ✗
  → Calibration 무효!
  → 근본 원인 파악 필요
```

### 시나리오 3: Sleep/Idle (필수)
```
예상 범위: 0.01 ~ 1mA
목적: 저전류 범위에서 calibration 검증

테스트:
1. Manual 툴로 측정
2. DoU로 측정 (calibration 적용)
3. 비교

예상 결과 A (선형적):
  DoU = Manual ✓
  
예상 결과 B (비선형적 또는 offset):
  DoU ≠ Manual ✗
```

---

## 📊 분석 방법

### 데이터 수집

**각 시나리오마다:**
```
채널  Manual(mA)  DoU_Raw(mA)  DoU_Cal(mA)  오차(%)
ai0   ???         ???          ???          ???
ai1   ???         ???          ???          ???
ai2   ???         ???          ???          ???
ai3   ???         ???          ???          ???
ai4   ???         ???          ???          ???
ai5   ???         ???          ???          ???
```

### 분석 기준

**✅ Calibration 유효 (선형적):**
```
모든 시나리오에서:
  오차 < 5%
  
→ Shunt 저항 값 문제일 가능성
→ Calibration 유지 가능
→ 하지만 근본 원인(Shunt) 수정 권장
```

**❌ Calibration 무효 (비선형적):**
```
시나리오별로 오차 다름:
  Phone App: 오차 < 5% ✓
  WiFi Heavy: 오차 > 20% ✗
  Sleep: 오차 > 50% ✗
  
→ 비선형성 또는 offset 문제
→ Calibration 제거 필요
→ 근본 원인 파악 필수
```

---

## 🔍 근본 원인 파악

### 원인 1: Shunt 저항 값 차이 (선형적)

**증상:**
```
모든 시나리오에서 동일한 비율로 차이
0.1mA도 6.5배, 100mA도 6.5배
```

**확인:**
```
멀티미터로 실제 shunt 측정
ai3: 0.032Ω? (설정: 0.005Ω)
```

**해결:**
```python
# Calibration 제거
# Shunt 값만 수정
config['ai3']['shunt_r'] = 0.032  # 실제 값
```

### 원인 2: Offset 오류

**증상:**
```
저전류에서 오차 큼, 고전류에서 오차 작음

예:
  Phone App (1mA): 오차 50%
  WiFi Heavy (100mA): 오차 5%
```

**원인:**
```
측정 회로에 고정된 offset
예: +5mV의 offset 있다면
  1mA: 실제 0.005mV + 5mV offset = 엄청난 오차
  100mA: 실제 5mV + 5mV offset = 작은 오차
```

**해결:**
```python
# Offset 보정 추가
current_corrected = (measured - OFFSET) * SCALE
```

### 원인 3: 비선형성

**증상:**
```
전류 범위마다 다른 보정 필요

Low: factor 0.1
Mid: factor 0.156
High: factor 0.3
```

**원인:**
```
- ADC saturation
- 증폭기 비선형성
- 측정 범위 자동 전환
```

**해결:**
```python
# 전류별 보정 테이블
def get_calibration(channel, current_raw):
    if current_raw < 10:
        return CALIB_LOW[channel]
    elif current_raw < 50:
        return CALIB_MID[channel]
    else:
        return CALIB_HIGH[channel]
```

---

## 🎯 즉시 실행 계획

### 1단계: 간단한 검증 (5분)

**다른 전류 범위 테스트:**

```python
# 인위적으로 다른 상황 만들기
# 예: Screen brightness 변경, WiFi on/off 등

테스트 A: Screen Off (저전류)
  Manual ai3: ???mA
  DoU ai3: ???mA
  
테스트 B: Screen Max + WiFi (고전류)
  Manual ai3: ???mA
  DoU ai3: ???mA
  
비교:
  둘 다 일치? → 선형적 ✓
  한쪽만 일치? → 비선형적 ✗
```

### 2단계: 체계적 검증 (30분)

**3가지 시나리오 테스트:**
```
1. Idle (lowest current)
2. Phone App (medium current) - 이미 완료
3. WiFi Heavy (highest current)

각각 Manual과 DoU 비교
```

### 3단계: 분석 및 결정

**시나리오 A: 모두 일치 (선형적)**
```
→ Shunt 값 문제 확정
→ Calibration 유지 가능
→ 하지만 Shunt 수정 권장
```

**시나리오 B: 불일치 (비선형적)**
```
→ Calibration 제거!
→ 근본 원인 파악
→ 올바른 해결책 적용
```
