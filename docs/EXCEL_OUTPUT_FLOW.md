# 엑셀 출력 데이터 흐름 완전 분석

## 📊 전체 프로세스 요약

```
1. DAQ 하드웨어 측정 (30kHz, 10초)
   ↓
2. 압축 (30:1) → 10,000개 샘플
   ↓
3. 전류 계산 (V/R*1000 /10)
   ↓
4. daq_data 리스트 생성
   ↓
5. 엑셀 출력
```

## 🔬 1단계: DAQ 하드웨어 측정

### 📍 위치: `services/ni_daq.py` - `read_current_channels_hardware_timed()`

```python
# Line 823
def read_current_channels_hardware_timed(
    self, 
    channels: List[str],
    sample_rate: float = 30000.0,      # 30kHz
    compress_ratio: int = 30,           # 30:1 압축
    duration_seconds: float = 10.0,    # 10초
    voltage_range: float = 0.1          # ±0.1V
) -> Optional[dict]:
```

### ⚙️ DAQ 설정 (nidaqmx API):

```python
# Line 976-980
task.timing.cfg_samp_clk_timing(
    rate=30000.0,                                    # 샘플링 속도: 30kHz
    sample_mode=AcquisitionType.CONTINUOUS,          # 연속 모드 (Manual tool과 동일)
    samps_per_chan=300000                            # 버퍼 크기: 300,000 샘플
)
```

**nidaqmx 공식 문서 기준:**
- `rate`: Clock rate (Hz) - 30,000 Hz = 30kHz
- `sample_mode`: CONTINUOUS = 순환 버퍼에서 연속 수집
- `samps_per_chan`: 채널당 샘플 수 (10초 × 30kHz = 300,000)

### 📡 데이터 읽기:

```python
# Line 989
data = task.read(
    number_of_samples_per_channel=300000,  # 채널당 300,000개 샘플 읽기
    timeout=15.0                           # 타임아웃 15초
)
```

**결과:** 
- Raw voltage 데이터: **300,000개 샘플** (채널당)
- 단위: **Volts** (V)
- 예: `[0.000001, 0.0000012, 0.0000009, ...]`

## 🗜️ 2단계: 데이터 압축 (30:1)

### 📍 위치: `services/ni_daq.py` - `_compress_data()`

```python
# Line 810-821
def _compress_data(self, data: List[float], compress_ratio: int) -> List[float]:
    """Compress data by averaging groups of samples"""
    compressed = []
    
    for i in range(0, len(data), compress_ratio):  # 30개씩 그룹
        group = data[i:i+compress_ratio]            # 30개 샘플 선택
        
        if len(group) > 0:
            avg_value = sum(group) / len(group)     # 평균 계산
            compressed.append(avg_value)
    
    return compressed
```

**계산:**
```
Raw: 300,000개 샘플
압축: 300,000 / 30 = 10,000개 샘플
간격: 1ms마다 1개 (30kHz / 30 = 1kHz = 1ms)
```

**예시:**
```python
# 원본 30개 샘플
[0.000001, 0.0000012, 0.0000009, ..., 0.0000011]  # 30개

# 평균 계산
avg = sum(30개) / 30 = 0.00000105 V

# 압축 결과
[0.00000105]  # 1개로 압축
```

## ⚡ 3단계: 전류 계산

### 📍 위치: `services/ni_daq.py` - Line 1061, 1135

```python
# 현재 적용된 계산식 (10으로 나누기 포함)
compressed_ma = [(v / shunt_r) * 1000 / 10.0 for v in compressed_volts]
```

**단계별 계산:**

```python
# 예: ai3 (VDD_WIFI_1P0)
compressed_volts = [0.00000105, 0.00000098, ...]  # 10,000개 (압축된 전압, V)
shunt_r = 0.005  # 5mΩ = 0.005Ω

# 각 샘플에 대해:
v = 0.00000105  # V (1.05 μV)

# Step 1: 전류 계산 (Ohm's law: I = V / R)
current_A = v / shunt_r
         = 0.00000105 / 0.005
         = 0.00021 A

# Step 2: mA로 변환
current_mA = current_A * 1000
          = 0.00021 * 1000
          = 0.21 mA

# Step 3: 10으로 나누기 (임시 수정)
current_mA_final = current_mA / 10.0
                 = 0.21 / 10.0
                 = 0.021 mA

# 결과
compressed_ma = [0.021, 0.019, ...]  # 10,000개 (mA)
```

**반환 데이터 구조:**

```python
result = {
    'ai0': {
        'current_data': [0.015, 0.016, 0.014, ...],  # 10,000개 (mA)
        'sample_count': 10000,
        'name': 'VBAT'
    },
    'ai1': {
        'current_data': [0.752, 0.748, 0.755, ...],  # 10,000개 (mA)
        'sample_count': 10000,
        'name': 'VDD_1P8_AP'
    },
    # ... ai2, ai3, ai4, ai5
}
```

## 📦 4단계: daq_data 리스트 생성

### 📍 위치: `services/test_scenario_engine.py` - Line 1773-1803

```python
# Line 1774-1803
self.daq_data = []  # 초기화

# Get sample count (10,000)
sample_count = daq_result['ai0']['sample_count']  # 10000

# Create data points for each sample (10,000번 반복)
for i in range(sample_count):  # i = 0, 1, 2, ..., 9999
    data_point = {
        'timestamp': datetime.now(),
        'time_elapsed': i,          # Time in ms: 0, 1, 2, ..., 9999
        'screen_test_time': i
    }
    
    # Add current data for each channel
    for channel in enabled_channels:  # ['ai0', 'ai1', ..., 'ai5']
        if channel in daq_result:
            current_mA = daq_result[channel]['current_data'][i]  # i번째 샘플
            data_point[f'{channel}_current'] = current_mA        # 'ai0_current': 0.015
    
    self.daq_data.append(data_point)
```

**daq_data 구조:**

```python
self.daq_data = [
    {  # 0ms
        'timestamp': datetime(...),
        'time_elapsed': 0,
        'screen_test_time': 0,
        'ai0_current': 0.015,   # mA
        'ai1_current': 0.752,   # mA
        'ai2_current': -0.123,  # mA
        'ai3_current': 0.021,   # mA
        'ai4_current': 0.334,   # mA
        'ai5_current': 0.089    # mA
    },
    {  # 1ms
        'timestamp': datetime(...),
        'time_elapsed': 1,
        'screen_test_time': 1,
        'ai0_current': 0.016,
        'ai1_current': 0.748,
        # ...
    },
    # ... 총 10,000개 딕셔너리
]
```

## 📄 5단계: 엑셀 출력

### 📍 위치: `services/test_scenario_engine.py` - `_export_to_excel_basic()`

```python
# Line 2652-2750
def _export_to_excel_basic(self, filename: str) -> bool:
    # pandas DataFrame으로 변환
    df = pd.DataFrame(self.daq_data)
    
    # 컬럼 재정렬
    time_cols = ['timestamp', 'time_elapsed', 'screen_test_time']
    current_cols = [col for col in df.columns if '_current' in col]
    df = df[time_cols + sorted(current_cols)]
    
    # 엑셀 저장
    df.to_excel(filename, index=False)
```

**엑셀 파일 구조:**

| timestamp | time_elapsed | screen_test_time | ai0_current | ai1_current | ai2_current | ai3_current | ai4_current | ai5_current |
|-----------|--------------|------------------|-------------|-------------|-------------|-------------|-------------|-------------|
| 2025-11-10 12:00:00 | 0 | 0 | 0.015 | 0.752 | -0.123 | 0.021 | 0.334 | 0.089 |
| 2025-11-10 12:00:00 | 1 | 1 | 0.016 | 0.748 | -0.125 | 0.019 | 0.338 | 0.091 |
| 2025-11-10 12:00:00 | 2 | 2 | 0.014 | 0.755 | -0.120 | 0.022 | 0.330 | 0.087 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |
| ... (10,000 rows) ... |

**컬럼 설명:**
- `timestamp`: 측정 시작 시각
- `time_elapsed`: 경과 시간 (ms) - 0부터 9999까지
- `screen_test_time`: 화면 테스트 시간 (ms)
- `ai0_current` ~ `ai5_current`: 각 채널의 전류 (mA)

## 📊 데이터 흐름 요약

```
Raw ADC 읽기:
  300,000 samples × 6 channels
  @ 30kHz, 10 seconds
  단위: Volts (V)
  예: 0.00000105 V

          ↓ [30:1 압축]

압축 후:
  10,000 samples × 6 channels
  @ 1kHz (1ms 간격)
  단위: Volts (V)
  예: 0.00000105 V (평균)

          ↓ [전류 계산: I = V/R*1000/10]

전류 데이터:
  10,000 samples × 6 channels
  단위: mA
  예: 0.021 mA

          ↓ [daq_data 리스트 생성]

daq_data:
  10,000 dictionaries
  각 dict: 시간 정보 + 6개 채널 전류
  
          ↓ [pandas → Excel]

엑셀 파일:
  10,000 rows × 9 columns
  (timestamp, time_elapsed, screen_test_time, ai0~ai5_current)
```

## 🔢 실제 예시 (ai3 기준)

```
Step 1: Raw ADC (30kHz × 10s = 300,000 samples)
  [0.000001050, 0.000001052, ..., 0.000001048]  # 300k 샘플

Step 2: 30:1 압축 (10,000 samples)
  [0.000001050, 0.000001045, ..., 0.000001052]  # 10k 샘플 (30개씩 평균)

Step 3: 전류 계산 (shunt_r = 0.005Ω)
  I = V / R * 1000 / 10
  I = 0.000001050 / 0.005 * 1000 / 10
  I = 0.021 mA
  
  → [0.021, 0.020, 0.022, ...]  # 10k 샘플 (mA)

Step 4: daq_data
  {
    'time_elapsed': 0,
    'ai3_current': 0.021
  }

Step 5: 엑셀
  Row 1: time_elapsed=0, ai3_current=0.021
  Row 2: time_elapsed=1, ai3_current=0.020
  ...
```

## ⚠️ 현재 /10.0 적용

**Line 1061, 1135:**
```python
compressed_ma = [(v / shunt_r) * 1000 / 10.0 for v in compressed_volts]
```

**이유:** 
- 엑셀 값을 10으로 나누면 Manual tool과 일치
- 근본 원인은 아직 미확인 (voltage reading 또는 gain 문제 가능성)

**결과:**
- 전류 값이 1/10로 출력됨
- Manual tool과 일치하는 값

## 📝 정리

**엑셀 최종 출력 값:**
- **단위:** mA (milliampere)
- **샘플 수:** 10,000개 (채널당)
- **시간 간격:** 1ms
- **계산식:** `I (mA) = V (Volts) / R (Ω) × 1000 / 10`
- **Raw 데이터:** 300,000개 → 30:1 압축 → 10,000개
