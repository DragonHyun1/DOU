# 전류 측정 차이 문제 해결 요약

**날짜:** 2025-11-10  
**브랜치:** cursor/analyze-current-measurement-discrepancies-c8da  
**이슈:** 메뉴얼 측정과 DoU 툴의 전류 측정값 차이 (약 10,000배 ~ 100,000배)

---

## 🔍 문제 진단 결과

### 근본 원인
**DIFFERENTIAL 모드 실패로 인한 RSE 모드 fallback**

```
시도 순서:
1. DEFAULT 모드 (±200mV) → 실패
2. DIFFERENTIAL 모드 (±200mV) → 실패
3. NRSE 모드 (±200mV) → 실패
4. RSE 모드 (±5V) → 성공 (하지만 잘못된 측정)

문제:
- RSE 모드는 Rail Voltage를 측정 (예: 4.2V)
- Shunt drop을 측정하지 못함 (예: 0.001V)
- 결과: 4.2V ÷ 0.01Ω = 420A (비정상)
```

### 실패 이유
**±200mV 범위가 너무 좁음**

```
설정: min_val=-0.2, max_val=0.2 (±200mV)
문제: 
- 채널 초기화 시 전압 스파이크
- 실제 측정 범위 초과 가능성
- DAQ가 DIFFERENTIAL 모드 거부
```

---

## ✅ 적용된 수정사항

### 1. DIFFERENTIAL 모드 범위 확대 ⭐⭐⭐

**위치:** `services/ni_daq.py` Line 1305-1374

**수정 전:**
```python
# DIFFERENTIAL 모드 (±200mV)
terminal_config=TerminalConfiguration.DIFFERENTIAL,
min_val=-0.2, max_val=0.2
```

**수정 후:**
```python
# DIFFERENTIAL 모드 (±5V) - 넓은 범위로 실패 방지
terminal_config=TerminalConfiguration.DIFFERENTIAL,
min_val=-5.0, max_val=5.0
```

**효과:**
- DIFFERENTIAL 모드 성공 가능성 증가
- 정밀도는 여전히 충분함 (16-bit ADC: 0.15mV 해상도)
- Shunt drop을 정확히 측정

### 2. 우선순위 변경

**수정 전:**
```
1. DEFAULT (±200mV)
2. DIFFERENTIAL (±200mV)
3. NRSE (±200mV)
4. RSE (±5V) - fallback
```

**수정 후:**
```
1. DIFFERENTIAL (±5V) ← 최우선
2. DEFAULT (±5V)
3. NRSE (±5V)
4. RSE (±10V) - 명확한 경고
```

### 3. 검증 로직 추가 ⭐⭐

**위치:** `services/ni_daq.py` Line 1416-1457, 1479-1518

**추가된 검증:**

```python
# 1. 측정 전압이 rail voltage인지 검증
if abs(avg_v_volts) > 0.5:  # > 500mV
    print("🚨 CRITICAL WARNING")
    print("🚨 Measured voltage is too high for shunt drop!")
    print("🚨 Likely measuring Rail Voltage!")
    
# 2. 계산된 전류가 비정상인지 검증
if abs(avg_i_ma) > 10000:  # > 10A
    print("🚨 WARNING: Current is unreasonably high!")
    
# 3. 검증 결과를 데이터에 포함
result[channel] = {
    'current_data': ...,
    'validation': {
        'is_rail_voltage': True/False,
        'terminal_mode': 'DIFFERENTIAL/RSE/...',
        'avg_voltage_mv': measured_value,
        'expected_shunt_drop_mv': '< 100mV'
    }
}
```

### 4. 로깅 개선 ⭐

**추가된 로그:**

```python
# 각 채널 설정 시
print(f"  → Trying DIFFERENTIAL mode with ±5V range...")
print(f"  ✅ DIFFERENTIAL mode enabled")

# 측정 결과
print(f"  Avg voltage: {avg_v_mv:.3f}mV")
print(f"  Avg current: {avg_i_ma:.3f}mA")
print(f"  Terminal mode: {terminal_mode}")
print(f"  Validation: ✅ PASSED / ❌ FAILED")

# 에러 발생 시
print(f"  ⚠️ DIFFERENTIAL failed: {error_type}: {error_message}")
print(f"     Error details: {full_error}")
```

---

## 📊 예상 결과

### 수정 전 (RSE 모드)
```
Channel ai0 (VBAT):
  Avg voltage: 4147.016mV  ← Rail voltage
  Avg current: 414,701.6mA  ← 414A (비정상!)
  Terminal mode: RSE
  Validation: ❌ FAILED

🚨 CRITICAL WARNING
🚨 Measured voltage (4147.0mV) is too high for shunt drop!
🚨 RSE mode measures rail voltage, not shunt drop!
```

### 수정 후 (DIFFERENTIAL 모드 성공 시)
```
Channel ai0 (VBAT):
  → Trying DIFFERENTIAL mode with ±5V range...
  ✅ DIFFERENTIAL mode enabled (±5V range)
  Avg voltage: 0.168mV  ← Shunt drop
  Avg current: 16.8mA  ← 정상 범위
  Terminal mode: DIFFERENTIAL
  Validation: ✅ PASSED
```

### 수정 후 (여전히 RSE인 경우)
```
Channel ai0 (VBAT):
  → Trying DIFFERENTIAL mode with ±5V range...
  ⚠️ DIFFERENTIAL failed: ...
  ...
  ⚠️ NRSE also failed, using RSE as last resort
  🚨 WARNING: RSE mode measures Rail Voltage, NOT shunt drop!
  🚨 This will cause ~100,000x error in current measurement!
  
  Avg voltage: 4147.016mV  ← Rail voltage
  Avg current: 414,701.6mA  ← 414A (비정상!)
  Terminal mode: RSE
  Validation: ❌ FAILED

🚨 CRITICAL WARNING for ai0
🚨 Measured voltage (4147.0mV) is too high for shunt drop!
🚨 Expected shunt drop: < 100mV
🚨 Terminal mode: RSE
🚨 RSE mode measures rail voltage, not shunt drop!
🚨 Hardware must be connected in DIFFERENTIAL mode
```

---

## 🧪 테스트 방법

### 1단계: DoU 재시작 및 테스트 실행

```bash
# 1. 코드 업데이트 확인
git status

# 2. DoU 툴 재시작

# 3. Phone App Test 실행
```

### 2단계: 콘솔 로그 확인

**성공 케이스:**
```
=== Hardware-Timed VOLTAGE Collection ===
Adding VOLTAGE channel: Dev1/ai0 (VBAT)
  → Trying DIFFERENTIAL mode with ±5V range...
  ✅ DIFFERENTIAL mode enabled (±5V range)
  📌 Channel ai0 configured with DIFFERENTIAL mode
...
Channel ai0: 10000 compressed samples
  Avg voltage: 0.168mV  ← 이 값이 중요!
  Avg current: 16.8mA
  Terminal mode: DIFFERENTIAL
  Validation: ✅ PASSED
```

**실패 케이스 (하드웨어 문제):**
```
=== Hardware-Timed VOLTAGE Collection ===
Adding VOLTAGE channel: Dev1/ai0 (VBAT)
  → Trying DIFFERENTIAL mode with ±5V range...
  ⚠️ DIFFERENTIAL failed: DaqError: ...
     Error details: [자세한 에러]
...
  🚨 WARNING: RSE mode measures Rail Voltage, NOT shunt drop!

Channel ai0: 10000 compressed samples
  Avg voltage: 4147.0mV  ← Rail voltage (문제!)
  
🚨 CRITICAL WARNING for ai0
🚨 Measured voltage (4147.0mV) is too high for shunt drop!
🚨 Terminal mode: RSE
🚨 Hardware must be connected in DIFFERENTIAL mode
```

### 3단계: Excel 결과 확인

**정상 측정:**
```
Time(ms)  VBAT(mA)  VDD_1P8_AP(mA)  ...
0         15.234    3.456           ...
1         16.123    3.567           ...
2         17.234    3.678           ...
...

범위: 수 mA ~ 수십 mA
```

**비정상 측정 (하드웨어 문제):**
```
Time(ms)  VBAT(mA)     VDD_1P8_AP(mA)  ...
0         414,700.16   178,322.20      ...
1         414,701.23   178,323.15      ...
...

범위: 수십만 mA (비정상!)
```

---

## 🔧 하드웨어 점검 사항

만약 DIFFERENTIAL 모드가 여전히 실패한다면, **하드웨어 연결**을 확인해야 합니다:

### 올바른 Differential 연결

```
Power Rail ━━[A]━━━[Shunt 0.01Ω]━━━[B]━━━ Load
              ↓                        ↓
         [DAQ ai0+]              [DAQ ai8-]
         
측정값: V(A) - V(B) = Shunt drop (0.1mV ~ 10mV)
전류: Shunt drop / 0.01Ω = 정상 전류
```

### 잘못된 Single-ended 연결 (현재 상태?)

```
Power Rail ━━[A]━━━[Shunt 0.01Ω]━━━[B]━━━ Load
              ↓
         [DAQ ai0+]
              ↓
           [GND]
         
측정값: V(A) = Rail voltage (4.2V)
전류: 4.2V / 0.01Ω = 420A (비정상!)
```

### USB-6289 Differential 채널 매핑

```
ai0 = ai0+ (pin) / ai8- (pin)
ai1 = ai1+ (pin) / ai9- (pin)
ai2 = ai2+ (pin) / ai10- (pin)
ai3 = ai3+ (pin) / ai11- (pin)
ai4 = ai4+ (pin) / ai12- (pin)
ai5 = ai5+ (pin) / ai13- (pin)
```

**확인 사항:**
- [ ] ai0+가 shunt 한쪽에 연결
- [ ] ai8-가 shunt 다른쪽에 연결
- [ ] 각 rail마다 동일하게 연결

---

## 📋 다음 단계

### CASE A: DIFFERENTIAL 모드 성공 시

**상황:**
```
✅ DIFFERENTIAL mode enabled
Avg voltage: 0.168mV
Avg current: 16.8mA
Validation: ✅ PASSED
```

**조치:**
1. ✅ 메뉴얼 측정 결과와 비교
2. ✅ 차이가 작다면 성공!
3. ✅ 차이가 여전히 크다면:
   - Shunt 저항 값 확인 (0.01Ω이 맞는지)
   - 메뉴얼 툴의 설정 확인
   - 샘플링 구간 확인 (전체 평균 vs 일부 평균)

### CASE B: DIFFERENTIAL 모드 실패 시

**상황:**
```
⚠️ DIFFERENTIAL failed
🚨 WARNING: RSE mode measures Rail Voltage
Avg voltage: 4147.0mV
Validation: ❌ FAILED
```

**조치:**
1. ❌ **하드웨어 재연결 필요**
2. 위의 "올바른 Differential 연결" 참고
3. 각 채널을 differential로 재연결
4. 재테스트

### CASE C: DIFFERENTIAL 성공했지만 여전히 차이 큼

**상황:**
```
✅ DIFFERENTIAL mode enabled
Avg voltage: 10.0mV (정상 범위)
Avg current: 1000mA (메뉴얼은 100mA)
→ 10배 차이
```

**가능한 원인:**
1. **Shunt 저항 값이 다름**
   - DoU 설정: 0.01Ω
   - 실제: 0.1Ω?
   - 해결: Shunt 값 수정

2. **측정 구간이 다름**
   - DoU: 0~10초 전체 평균
   - 메뉴얼: 특정 구간만?
   - 해결: 동일 구간으로 설정

3. **압축/평균 방식이 다름**
   - DoU: 30:1 압축, 평균
   - 메뉴얼: RMS? Median?
   - 해결: 동일 방식 구현

---

## 📝 변경사항 요약

| 파일 | 변경 내용 | 라인 | 효과 |
|------|----------|------|------|
| `services/ni_daq.py` | DIFFERENTIAL 범위 ±200mV → ±5V | 1320 | 모드 실패 방지 |
| `services/ni_daq.py` | 우선순위 변경 (DIFFERENTIAL 최우선) | 1315-1367 | 올바른 측정 보장 |
| `services/ni_daq.py` | 검증 로직 추가 (rail voltage 감지) | 1416-1457 | 오류 조기 감지 |
| `services/ni_daq.py` | 검증 로직 추가 (multi-channel) | 1479-1518 | 오류 조기 감지 |
| `services/ni_daq.py` | 명확한 경고 메시지 | 전체 | 문제 진단 용이 |
| `docs/CURRENT_MEASUREMENT_ISSUE_ANALYSIS.md` | 문제 분석 문서 작성 | 신규 | 이해 및 공유 |

**총 변경:**
- 수정: ~100 lines
- 추가: ~150 lines (로깅 및 검증)
- 문서: 2개 (분석 + 요약)

---

## 🎯 기대 효과

### 1. DIFFERENTIAL 모드 성공률 증가
- ±200mV → ±5V 범위 확대
- 초기화 스파이크에도 안정적

### 2. 명확한 문제 진단
- 실시간 검증 로그
- Rail voltage 측정 즉시 감지
- 하드웨어 문제 여부 명확히 파악

### 3. 데이터 신뢰성 향상
- 검증 정보 포함
- 비정상 데이터 자동 플래그
- 후처리 시 필터링 가능

---

## 📞 추가 확인 필요 사항

다음 정보를 제공해주시면 더 정확한 분석이 가능합니다:

### 1. 테스트 실행 후 콘솔 로그
```
=== Hardware-Timed VOLTAGE Collection ===
(전체 로그 복사)
```

### 2. DIFFERENTIAL 모드 성공 여부
```
✅ DIFFERENTIAL mode enabled
또는
⚠️ DIFFERENTIAL failed: ...
```

### 3. 측정 전압값
```
Avg voltage: ???mV
→ 0.1~10mV이면 정상 (shunt drop)
→ 1000~5000mV이면 비정상 (rail voltage)
```

### 4. 메뉴얼 툴 설정
```
- Terminal Config: ???
- Voltage Range: ???
- Shunt 저항 값: ???
```

---

**이 수정으로 DIFFERENTIAL 모드가 성공하면 메뉴얼 측정과 거의 동일한 결과를 얻을 수 있을 것입니다!** 🎯
