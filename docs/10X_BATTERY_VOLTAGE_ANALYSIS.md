# 10배 차이와 배터리 전압 4V 연관성 분석

## 🔋 사용자 힌트

1. **Shunt resistor 값은 정확함** (10배 문제 아님)
2. **배터리 전압 4V**와 연관이 있을 수 있음
3. VBAT rail은 그렇다 치고, **다른 rail들에 수식이 필요한가?**

## 📊 현재 Rail 구성

| Channel | Rail Name | Target V | Shunt R | 설명 |
|---------|-----------|----------|---------|------|
| ai0 | VBAT | 4.0V | 0.01Ω | 배터리 직접 |
| ai1 | VDD_1P8_AP | 1.8V | 0.1Ω | VBAT → 1.8V 변환 |
| ai2 | VDD_MLDO_2P0 | 2.0V | 0.005Ω | VBAT → 2.0V 변환 |
| ai3 | VDD_WIFI_1P0 | 1.0V | 0.005Ω | VBAT → 1.0V 변환 |
| ai4 | VDD_1P2_AP_WIFI | 1.2V | 0.1Ω | VBAT → 1.2V 변환 |
| ai5 | VDD_1P35_WIFIPMU | 1.35V | 0.1Ω | VBAT → 1.35V 변환 |

## 🤔 가능한 원인

### 원인 1: DIFF 모드에서 Gain 문제

**DIFF 모드:**
- 두 입력의 **차이**를 측정
- 내부 gain이 적용될 수 있음
- Voltage range에 따라 gain이 달라질 수 있음

**±0.1V range vs ±5V range:**
- 작은 range → 높은 gain (정밀 측정)
- 큰 range → 낮은 gain (넓은 측정)
- **Gain 차이가 10배일 수도?**

### 원인 2: Voltage를 10배 크게 읽고 있음

**가능성:**
```python
# 혹시 내부적으로:
measured_voltage = raw_adc_value * scale_factor

# scale_factor가 10배 크게 설정되어 있으면?
# 예: 실제 0.001V인데 0.01V로 읽힘
# → 전류가 10배 계산됨
```

### 원인 3: CONTINUOUS vs FINITE 모드 차이

**CONTINUOUS 모드:**
- 순환 버퍼에서 읽음
- 타이밍이 조금 다를 수 있음

**FINITE 모드:**
- 정확히 지정된 샘플만 수집
- 타이밍이 더 정확함

**Manual tool이 CONTINUOUS를 사용하지만, 내부 처리가 다를 수도?**

### 원인 4: 30kHz 샘플링의 Aliasing

**30kHz 샘플링:**
- 30개/ms → 30:1 압축 → 1개/ms
- 혹시 압축 과정에서 10배 증폭?

**압축 계산:**
```python
# 현재 방식
compressed = [sum(group)/len(group) for group in groups]

# 혹시 sum만 하고 len으로 안 나눴으면?
compressed = [sum(group) for group in groups]  # 10배 차이 가능?
```

### 원인 5: Voltage Range ADC Resolution

**±0.1V range:**
- ADC resolution 높음 (정밀)
- 하지만 scale factor가 다를 수 있음

**±5V range:**
- ADC resolution 낮음 (넓은 범위)
- Scale factor 다름

**혹시 ±0.1V range로 읽을 때 자동으로 10x gain이 적용되는데, 이걸 보정 안 하고 있는 건 아닐까?**

## 🔍 확인 방법

### 1. Raw Voltage 직접 출력

```python
# ni_daq.py에서 raw voltage 출력
print(f"Raw voltage samples (first 10): {data[:10]}")
print(f"Average raw voltage: {sum(data)/len(data):.9f}V")
```

**Manual tool과 비교:**
- Manual의 raw voltage는 얼마인가?
- 우리 툴의 raw voltage가 10배 큰가?

### 2. 다른 Voltage Range로 테스트

```bash
python test_10x_voltage_check.py
```

**비교:**
- ±0.1V range: X mV
- ±5V range: Y mV
- X vs Y 비율은?

### 3. Compression 로직 확인

```python
# _compress_data 함수 확인
def _compress_data(self, data, ratio):
    compressed = []
    for i in range(0, len(data), ratio):
        group = data[i:i+ratio]
        if group:
            avg_value = sum(group) / len(group)  # ← 여기 확인!
            compressed.append(avg_value)
    return compressed
```

### 4. Manual Tool 설정 비교

**확인 필요:**
1. Manual의 Voltage Range?
2. Manual의 Shunt Resistor 값?
3. Manual의 Raw Voltage 값?
4. Manual의 압축 방식?

## 💡 임시 해결책

**10으로 나누기 (테스트용):**

```python
# ni_daq.py Line 1059, 1133
# 기존:
compressed_ma = [(v / shunt_r) * 1000 for v in compressed_volts]

# 임시 수정:
compressed_ma = [(v / shunt_r) * 1000 / 10 for v in compressed_volts]
# 또는
compressed_ma = [(v / shunt_r) * 100 for v in compressed_volts]
```

**주의:** 이것은 근본 원인을 찾기 전의 임시방편입니다!

## 🎯 다음 단계

1. **`test_10x_voltage_check.py` 실행**
   - Raw voltage 값 확인
   - ±0.1V vs ±5V 비교

2. **Manual tool 확인**
   - Raw voltage 값
   - Voltage range 설정
   - 전류 계산 방식

3. **Compression 로직 재확인**
   - `_compress_data` 함수 검증
   - 30:1 압축이 정확한지

4. **근본 원인 발견 후 수정**
   - Voltage reading 문제
   - 또는 계산식 문제
   - 또는 압축 문제
