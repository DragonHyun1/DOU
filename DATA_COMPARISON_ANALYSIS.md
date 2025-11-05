# DoU vs 다른 툴 데이터 비교 분석

## 📊 측정 데이터 비교

### 다른 툴 (정상)
```
Time(ms)  VBAT       VDD_1P8_AP  VDD_MLDO_2P0  VDD_WIFI_1P0  VDD_1P2_AP_WIFI  VDD_1P35_WIFIPMU
1         -6.76 mA   0.15 mA     1.11 mA       11.57 mA      0.09 mA          17.23 mA
2          1.11 mA   0.24 mA     1.25 mA       13.51 mA      0.06 mA          12.54 mA
3          3.12 mA   0.27 mA     2.85 mA       15.18 mA      0.06 mA          13.89 mA
...

특징:
- 범위: -10 ~ +60 mA
- VBAT: 음수~양수 (충전/방전)
- 다른 레일: 주로 양수 (소비 전류)
```

### DoU (비정상)
```
Time(ms)  VBAT         VDD_1P8_AP   VDD_MLDO_2P0  ...
0         -0.000135    0.001034     -0.000039
1          0.000036    0.003274      0.000208
2          0.000069    0.000186      0.000015
...

특징:
- 범위: -0.0001 ~ +0.003 mA
- 약 1000배 ~ 10000배 작음
- 비율은 유사할 수도 있음
```

---

## 🔍 분석 체크리스트

### 1. RAW_VOLTAGE 측정값 확인 ⬅️ **지금 이것부터!**

**테스트:**
```
DoU 프로그램에서 Refresh 버튼 클릭
→ 콘솔 출력 확인
```

**예상 출력:**
```
🔍 ai0: RAW_VOLTAGE=0.000xxxV (?.???mV) → CURRENT=?.???A (?.???mA)
   Calculation: 0.000xxxV / 0.01Ω = ?.???A

🔍 ai1: RAW_VOLTAGE=0.000xxxV (?.???mV) → CURRENT=?.???A (?.???mA)
   Calculation: 0.000xxxV / 0.01Ω = ?.???A
...
```

**분석 질문:**
- [ ] RAW_VOLTAGE가 몇 V인가?
- [ ] 0.001V ~ 0.1V 범위인가? (정상)
- [ ] 0.0001V 미만인가? (너무 작음)
- [ ] 1V 이상인가? (너무 큼, Rail 전압)

---

### 2. 하드웨어 연결 확인

**확인 사항:**
```
DAQ 채널 → Shunt 저항 양단 연결?
             OR
DAQ 채널 → Power Rail 직접 연결?

올바른 연결:
  Power Rail ━[Shunt 0.01Ω]━ Load
                    ↓
              [DAQ ai0+/ai0-]
              (Shunt 양단 전압 측정)

잘못된 연결:
  Power Rail ━━━━━━━━━━━━━ Load
       ↓
  [DAQ ai0+]
  (Rail 전압 직접 측정 = 4.2V)
```

**질문:**
- [ ] 다른 툴과 DoU가 같은 하드웨어 설정인가?
- [ ] 채널 매핑이 정확한가?

---

### 3. DAQ 설정 비교

**현재 DoU 설정:**
```python
add_ai_voltage_chan(
    terminal_config=RSE,
    min_val=-5.0,
    max_val=5.0,
    units=VOLTS
)

Current = Voltage / 0.01Ω
```

**다른 툴 (NI Trace 분석):**
```
NI I/O Trace:
  Range: ±5V
  Terminal: RSE
  Reading: 0.00008V (0.08mV)
  
Similar to DoU!
```

**차이점:**
- [ ] Gain 설정?
- [ ] Sampling rate?
- [ ] Averaging?

---

### 4. 단위 변환 확인

**DoU 계산:**
```python
# ni_daq.py
voltage = task.read()  # Volts
shunt_r = 0.01  # Ohms
current = voltage / shunt_r  # Amps

# test_scenario_engine.py
channel_data_mA[key] = value * 1000  # A to mA
```

**검증:**
```
예시:
  RAW_VOLTAGE = 0.001V (1mV)
  Shunt = 0.01Ω
  Current = 0.001V / 0.01Ω = 0.1A = 100mA ✓

만약 DoU 출력 = 0.0001mA 라면?
  역산: 0.0001mA = 0.0000001A
  Voltage = 0.0000001A * 0.01Ω = 0.000001V (1μV)
  → 측정 전압이 매우 작음!
```

---

## 🎯 다음 단계

### Phase 1: 실제 측정값 확인 ⬅️ **지금!**
```
1. DoU Refresh 버튼 클릭
2. 콘솔 출력 복사
3. RAW_VOLTAGE 값 분석
```

### Phase 2: 하드웨어 연결 확인
```
- 다른 툴과 DoU 하드웨어 설정 비교
- 채널 매핑 확인
- Shunt 연결 확인
```

### Phase 3: DAQ 설정 최적화
```
- Range 조정?
- Gain 설정?
- Averaging 추가?
```

---

## 📝 테스트 결과 기록

### 테스트 1: Refresh 버튼 (날짜: _____)

**콘솔 출력:**
```
(여기에 콘솔 출력 복사)
```

**분석:**
- RAW_VOLTAGE:
- 예상 범위 대비:
- 문제점:

---

## 💡 가설

### 가설 1: DAQ Range 문제
```
현재: ±5V Range
문제: Shunt 전압(0.001V)이 너무 작아서 Resolution 부족?
해결: ±0.1V Range로 변경?
```

### 가설 2: 하드웨어 연결 문제
```
문제: Rail 전압과 Shunt 전압 혼동?
해결: 연결 재확인
```

### 가설 3: Gain 설정 필요
```
다른 툴: Gain 적용?
DoU: Gain 없음?
해결: Gain 추가?
```

---

**지금 Refresh 버튼 눌러서 콘솔 출력 보여주세요!** 🔍
