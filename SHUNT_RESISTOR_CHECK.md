# Shunt Resistor 값 확인 필요

**문제:** 다른 툴과 우리 툴의 전류 측정값이 2000배 차이
- 다른 툴: 50mA 이상
- 우리 툴: 0.0025mA

---

## 🔍 가능한 원인

### 1. Shunt Resistor 값 설정 오류

현재 코드의 기본값:
```python
'VBAT':     shunt_r = 0.010Ω (10mΩ)  ← 이 값이 맞나요?
'VDD_1P8':  shunt_r = 0.020Ω (20mΩ)  ← 이 값이 맞나요?
```

실제 Hardware의 Shunt 값이 다를 경우:
```
만약 실제 = 0.001Ω (1mΩ)인데
코드 설정 = 0.010Ω (10mΩ)이면
→ 전류가 1/10로 계산됨!
```

### 2. 계산 예시

측정 전압 = 0.05mV (50μV)라고 가정

| 설정값 | 계산 | 결과 |
|--------|------|------|
| 0.001Ω | 0.05mV / 0.001Ω | 50mA ✅ |
| 0.010Ω | 0.05mV / 0.010Ω | 5mA ❌ |
| 0.100Ω | 0.05mV / 0.100Ω | 0.5mA ❌ |

---

## 📋 확인해야 할 것

### 1. Hardware Shunt Resistor 값
```
각 Power Rail의 실제 Shunt Resistor 저항값은?
□ VBAT: _____ Ω
□ VDD_1P8_AP: _____ Ω
□ VDD_MLDO_2P0: _____ Ω
□ VDD_WIFI_1P0: _____ Ω
□ VDD_1P2_AP_WIFI: _____ Ω
□ VDD_1P35_WIFIPMU: _____ Ω
```

일반적인 값:
- 1mΩ (0.001Ω) - 고전류 측정용
- 10mΩ (0.010Ω) - 중전류 측정용
- 100mΩ (0.100Ω) - 저전류 측정용

### 2. Multi-Channel Monitor 설정
```
UI에서 설정한 Shunt Resistor 값은?
(Excel로 import했거나 수동으로 입력한 값)
```

### 3. 다른 툴의 설정
```
다른 툴에서 사용하는 Shunt Resistor 값은?
```

---

## 🔧 수정 방법

올바른 Shunt Resistor 값을 확인한 후:

### Option 1: 코드에서 기본값 변경
```python
# services/ni_daq.py
default_rails = [
    {'name': 'VBAT', 'shunt_r': 0.001},  # 1mΩ로 변경
    # ...
]
```

### Option 2: Multi-Channel Monitor에서 설정
```
1. Multi-Channel Monitor 열기
2. 각 채널의 Shunt 값 입력
3. Save Config
```

---

## 📊 예상 결과

올바른 Shunt 값 설정 시:
```
Before: 0.0025mA (잘못된 설정)
After:  50mA (올바른 설정) ✅
```

---

## ⚠️ 긴급 확인 필요!

**Hardware Shunt Resistor의 실제 값을 확인해주세요!**

PCB 설계 문서나 실제 부품 확인이 필요합니다.
