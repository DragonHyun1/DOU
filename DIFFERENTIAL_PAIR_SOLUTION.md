# Differential Pair 측정 솔루션

## 가설: 다른 툴은 두 채널의 차이를 계산

### 현재 상황
```
ai0 (RSE) → 4.100000V (Rail 전압)
ai8 (RSE) → 4.099832V (Rail - Shunt drop)
차이:       0.000168V = 0.168mV ← Shunt drop!
```

### 다른 툴의 가능한 구현
```c
// 다른 툴 (추정)
float ch0 = read_ai0();  // 4.100000V
float ch8 = read_ai8();  // 4.099832V
float shunt_drop = ch0 - ch8;  // 0.000168V
float current = shunt_drop / 0.01 * 1000;  // 16.8mA
```

## 🔧 DoU 구현 방법

### Option 1: Differential 채널 쌍 읽기

**채널 매핑:**
```
VBAT:           ai0 (High) - ai8 (Low)
VDD_1P8_AP:     ai1 (High) - ai9 (Low)
VDD_MLDO_2P0:   ai2 (High) - ai10 (Low)
VDD_WIFI_1P0:   ai3 (High) - ai11 (Low)
VDD_1P2_AP_WIFI: ai4 (High) - ai12 (Low)
VDD_1P35_WIFIPMU: ai5 (High) - ai13 (Low)
```

**코드 수정:**
```python
# 두 채널 읽고 차이 계산
high_channels = ['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5']
low_channels = ['ai8', 'ai9', 'ai10', 'ai11', 'ai12', 'ai13']

for high, low in zip(high_channels, low_channels):
    voltage_high = read_channel(high)
    voltage_low = read_channel(low)
    shunt_drop = voltage_high - voltage_low
    current = shunt_drop / shunt_r * 1000
```

### Option 2: USB-6289 Differential 모드

**USB-6289 Differential 채널:**
```
ai0 = Channel 0 Differential (ai0+ and ai0-)
ai1 = Channel 1 Differential (ai1+ and ai1-)
...
ai7 = Channel 7 Differential (ai7+ and ai7-)

물리적 핀:
ai0+ : Pin 68
ai0- : Pin 33
```

**하드웨어 재연결:**
```
Shunt High → Pin 68 (ai0+)
Shunt Low  → Pin 33 (ai0-)
```

## 🎯 다음 단계

### 1. 다른 툴 채널 확인
```
다른 툴의 설정 화면에서:
- VBAT가 ai0만 사용하는지
- 아니면 ai0+ai8 두 개 사용하는지 확인
```

### 2. USB-6289 핀 연결 확인
```
현재 하드웨어가 어떻게 연결되어 있는지:
- ai0 (Pin 68): 어디에 연결?
- ai8 (Pin 33): 어디에 연결?
```

### 3. 선택
```
A. 두 채널 읽어서 차이 계산 (소프트웨어)
B. Differential 모드 사용 (하드웨어)
```

---

**이 정보를 확인해주시면 정확한 해결책을 제시할 수 있습니다!**
