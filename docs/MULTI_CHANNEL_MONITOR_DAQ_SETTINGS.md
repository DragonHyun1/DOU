# Multi-Channel Monitor DAQ Settings 추가 완료

## 📊 추가된 기능

### Multi-Channel Monitor에 DAQ Configuration UI 추가

**파일:** `/workspace/ui/multi_channel_monitor.py`

## 🎯 새로운 UI 요소

### DAQ Configuration 섹션

Rail Configuration 그룹박스 아래에 추가됨:

#### 1. **Voltage Range**
- **Widget:** ComboBox
- **Options:** ±5V, ±10V
- **Default:** ±5V
- **Variable:** `self.voltage_range_cb`

#### 2. **Sample Rate**
- **Widget:** SpinBox
- **Range:** 1,000 ~ 500,000 Hz
- **Default:** 30,000 Hz
- **Step:** 1,000 Hz
- **Variable:** `self.sample_rate_sb`

#### 3. **Compression Ratio**
- **Widget:** SpinBox
- **Range:** 1 ~ 100
- **Default:** 30:1
- **Variable:** `self.compression_ratio_sb`

#### 4. **Measurement Duration**
- **Widget:** DoubleSpinBox
- **Range:** 0.1 ~ 60.0 seconds
- **Default:** 10.0 seconds
- **Variable:** `self.measurement_duration_sb`

## 🔧 코드 변경 사항

### 1. DAQ Settings Dictionary 추가

```python
self.daq_settings = {
    'voltage_range': 5.0,  # ±5V
    'sample_rate': 30000,  # Hz
    'compression_ratio': 30,  # 30:1
    'measurement_duration': 10.0  # seconds
}
```

### 2. update_daq_settings() 함수 추가

```python
def update_daq_settings(self):
    """Update DAQ settings from UI"""
    voltage_range_text = self.voltage_range_cb.currentText()
    self.daq_settings['voltage_range'] = 5.0 if '±5V' in voltage_range_text else 10.0
    self.daq_settings['sample_rate'] = self.sample_rate_sb.value()
    self.daq_settings['compression_ratio'] = self.compression_ratio_sb.value()
    self.daq_settings['measurement_duration'] = self.measurement_duration_sb.value()
```

### 3. Monitoring & Single Read 업데이트

**Before:**
```python
results = ni_service.read_current_channels_direct(
    enabled_channels, 
    samples_per_channel=1000
)
```

**After:**
```python
results = ni_service.read_current_channels_hardware_timed(
    channels=enabled_channels,
    sample_rate=self.daq_settings['sample_rate'],
    compress_ratio=self.daq_settings['compression_ratio'],
    duration_seconds=self.daq_settings['measurement_duration'],
    voltage_range=self.daq_settings['voltage_range']
)
```

### 4. 자동 설정 업데이트

- **Start Monitoring 버튼 클릭 시:** `update_daq_settings()` 자동 호출
- **Single Read 버튼 클릭 시:** `update_daq_settings()` 자동 호출

## 📐 UI 레이아웃

```
Multi-Channel Power Rail Monitor
├─ Title & Controls (Self-Calibration, Single Read, Start Monitoring)
├─ Measurement Mode (Voltage Mode / Current Mode)
├─ Rail Configuration
│  ├─ Excel Data Import
│  └─ Save/Load Config
├─ DAQ Configuration  ← 새로 추가!
│  ├─ Voltage Range: [±5V ▼]
│  ├─ Sample Rate: [30000 Hz]
│  ├─ Compression Ratio: [30:1]
│  └─ Measurement Duration: [10.0 s]
└─ Channels (ai0 ~ ai11)
```

## 🎯 사용 방법

### 1. UI에서 설정 변경

```
Multi-Channel Monitor 열기
→ DAQ Configuration 섹션에서 설정 조정
→ Start Monitoring 또는 Single Read 클릭
→ 자동으로 새 설정 적용됨
```

### 2. 설정 예시

#### 빠른 측정 (실시간 모니터링)
```
Voltage Range: ±5V
Sample Rate: 10,000 Hz
Compression: 10:1
Duration: 1.0s
```

#### 정밀 측정 (Single Read)
```
Voltage Range: ±5V
Sample Rate: 100,000 Hz
Compression: 100:1
Duration: 10.0s
```

#### 넓은 범위 측정
```
Voltage Range: ±10V  ← Rail voltage가 큰 경우
Sample Rate: 30,000 Hz
Compression: 30:1
Duration: 10.0s
```

## 🔄 작동 흐름

### Start Monitoring 클릭 시

```
1. update_daq_settings() 호출
   → UI에서 설정 읽어서 daq_settings에 저장
   
2. Timer 시작 (1초마다)
   
3. _perform_periodic_measurement() 호출
   → read_current_channels_hardware_timed() 호출
   → daq_settings 전달
   
4. 결과를 UI에 표시
```

### Single Read 클릭 시

```
1. update_daq_settings() 호출
   → UI에서 설정 읽어서 daq_settings에 저장
   
2. read_current_channels_hardware_timed() 호출
   → daq_settings 전달
   
3. 결과를 UI에 표시 및 콘솔 출력
```

## 📊 측정 결과 영향

### Sample Rate 변경 효과

```
10,000 Hz:  빠른 측정 (1초 = 10,000 samples)
30,000 Hz:  기본 측정 (1초 = 30,000 samples)  ← 기본값
100,000 Hz: 정밀 측정 (1초 = 100,000 samples)
```

### Compression Ratio 변경 효과

```
10:1:  더 많은 데이터 포인트 (노이즈 많음)
30:1:  균형잡힌 데이터 (기본값)
100:1: 더 적은 데이터 포인트 (노이즈 적음)
```

### Duration 변경 효과

```
0.5s:  빠른 스냅샷
1.0s:  실시간 모니터링용
10.0s: 정밀 측정용 (기본값)
30.0s: 매우 안정적인 측정
```

### Voltage Range 변경 효과

```
±5V:  높은 resolution (작은 전압 측정에 적합)
±10V: 넓은 범위 (큰 전압 측정에 적합)
```

## ✅ 완료 사항

- [x] DAQ Configuration UI 추가 (4개 위젯)
- [x] daq_settings dictionary 추가
- [x] update_daq_settings() 함수 추가
- [x] toggle_monitoring()에서 자동 설정 업데이트
- [x] single_read()에서 자동 설정 업데이트
- [x] read_current_channels_direct → read_current_channels_hardware_timed 전환
- [x] voltage_range 파라미터 전달

## 🔜 추가 가능한 기능

1. **설정 저장/로드**: QSettings로 DAQ 설정 영구 저장
2. **프리셋**: 빠른 측정/정밀 측정/실시간 모니터링 프리셋 버튼
3. **자동 최적화**: 측정 결과에 따라 자동으로 설정 조정
4. **설정 유효성 검사**: 조합이 유효하지 않은 설정 경고

## 📝 테스트 방법

```python
# Multi-Channel Monitor 실행
from ui.multi_channel_monitor import MultiChannelMonitorDialog

dialog = MultiChannelMonitorDialog(parent=main_window)
dialog.show()

# 설정 변경
dialog.voltage_range_cb.setCurrentIndex(1)  # ±10V
dialog.sample_rate_sb.setValue(100000)      # 100kHz
dialog.compression_ratio_sb.setValue(100)   # 100:1
dialog.measurement_duration_sb.setValue(5.0) # 5초

# Single Read 실행
dialog.single_read()

# 설정 확인
print(dialog.daq_settings)
```

---

**완료!** Multi-Channel Monitor에서 DAQ 설정을 UI로 변경할 수 있습니다! 🎉
