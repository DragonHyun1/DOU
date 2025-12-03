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

## ✅ 문제 해결됨!

### 🔍 근본 원인 발견 (NI I/O Trace 분석)

**DoU (Auto Test - 잘못됨):**
```
DAQmxCreateAICurrentChan(
    "Dev1/ai0",
    min_val=-0.040,  // ±40mA
    max_val=0.040,
    units=Amps,
    shunt_resistor_loc=-1,  // Internal (249Ω)
    shunt_resistor_val=249.0
)

결과: 7.92639E-08 A = 0.00008 mA ❌
```

**다른 툴 (정상):**
```
DAQCreateAIVoltageChan(
    "Dev1/ai0",
    min_val=-5.0,  // ±5V
    max_val=5.0,
    units=Volts
)

결과: 0.000168257 V = 0.168 mV
→ Current = 0.168mV / 0.01Ω = 16.8 mA ✓
```

### 🎯 문제점

1. **DoU는 Current Mode 사용**
   - DAQ 내부 Shunt (249Ω) 사용
   - 외부 Shunt (0.01Ω) 무시
   - 측정값이 1000배 작음!

2. **다른 툴은 Voltage Mode 사용**
   - 외부 Shunt 전압 drop 측정
   - I = V / R 로 정확한 전류 계산
   - 정상적인 mA 범위 값

### ✅ 해결 완료

**수정사항 (Commit a559110):**
```python
# Before (잘못됨)
task.ai_channels.add_ai_current_chan(
    channel_name,
    min_val=-0.040,
    max_val=0.040,
    units=CurrentUnits.AMPS  # 내부 249Ω shunt
)

# After (수정됨)
task.ai_channels.add_ai_voltage_chan(
    channel_name,
    terminal_config=TerminalConfiguration.RSE,
    min_val=-5.0,
    max_val=5.0,
    units=VoltageUnits.VOLTS  # 외부 0.01Ω shunt
)

# 데이터 처리
voltage_volts = task.read()
shunt_r = 0.01  # Ω
current_ma = (voltage_volts / shunt_r) * 1000  # mA
```

### 📊 예상 결과

**수정 전:**
```
Time(ms)  VBAT         VDD_1P8_AP
0         -0.000135    0.001034    ❌ 1000배 작음
1          0.000036    0.003274
```

**수정 후 (예상):**
```
Time(ms)  VBAT       VDD_1P8_AP
0         -6.76      0.15        ✅ 정상 범위!
1          1.11      0.24
```

---

**이제 Phone App Test를 실행해서 결과를 확인하세요!** 🚀
