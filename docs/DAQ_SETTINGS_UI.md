# DAQ Settings UI 추가 완료

## 📊 추가된 설정

### Test Settings Dialog에 DAQ Configuration 그룹 추가

**파일:**
- `/workspace/ui/test_settings_dialog.ui` (Qt Designer UI 파일)
- `/workspace/ui/test_settings_dialog.py` (Python 코드)

### 새로운 설정 항목

#### 1. **Voltage Range** (전압 범위)
- **Widget:** ComboBox (`voltageRange_CB`)
- **Options:**
  - `±5V` (기본값)
  - `±10V`
- **용도:** DAQ 측정 범위 설정
- **영향:** ADC resolution과 측정 정확도

#### 2. **Sample Rate** (샘플링 레이트)
- **Widget:** SpinBox (`sampleRate_SB`)
- **Range:** 1,000 ~ 500,000 Hz
- **Default:** 30,000 Hz (30 kHz)
- **Step:** 1,000 Hz
- **용도:** 초당 측정 샘플 수

#### 3. **Compression Ratio** (압축 비율)
- **Widget:** SpinBox (`compressionRatio_SB`)
- **Range:** 1 ~ 100
- **Default:** 30:1
- **용도:** 데이터 압축 (30개 샘플 → 1개 평균값)

#### 4. **Measurement Duration** (측정 시간)
- **Widget:** DoubleSpinBox (`measurementDuration_SB`)
- **Range:** 0.1 ~ 60.0 seconds
- **Default:** 10.0 seconds
- **용도:** 각 측정 사이클의 시간

## 🔧 Python 코드 통합

### Settings Dictionary 구조

```python
settings = {
    # ... 기존 설정 ...
    
    # DAQ Configuration
    'voltage_range': 5.0,          # ±5V or ±10V
    'sample_rate': 30000,          # Hz
    'compression_ratio': 30,       # 30:1
    'measurement_duration': 10.0   # seconds
}
```

### Load Settings

```python
def load_settings(self):
    # Voltage Range
    voltage_range = self.settings.get('voltage_range', 5.0)
    index = 0 if voltage_range == 5.0 else 1
    self.voltageRange_CB.setCurrentIndex(index)
    
    # Sample Rate
    self.sampleRate_SB.setValue(self.settings.get('sample_rate', 30000))
    
    # Compression Ratio
    self.compressionRatio_SB.setValue(self.settings.get('compression_ratio', 30))
    
    # Measurement Duration
    self.measurementDuration_SB.setValue(self.settings.get('measurement_duration', 10.0))
```

### Save Settings

```python
def save_settings(self):
    # Voltage Range
    voltage_range_text = self.voltageRange_CB.currentText()
    self.settings['voltage_range'] = 5.0 if '±5V' in voltage_range_text else 10.0
    
    # Sample Rate
    self.settings['sample_rate'] = self.sampleRate_SB.value()
    
    # Compression Ratio  
    self.settings['compression_ratio'] = self.compressionRatio_SB.value()
    
    # Measurement Duration
    self.settings['measurement_duration'] = self.measurementDuration_SB.value()
```

## 📐 UI 레이아웃

### Dialog 크기 조정
- **Before:** 400 × 500
- **After:** 450 × 650

### 그룹박스 순서
1. Voltage Configuration
2. Test Parameters
3. Data Collection
4. **DAQ Configuration** ← 새로 추가!

## 🎯 사용 방법

### 1. UI에서 설정 변경

```
Settings → DAQ Configuration

Voltage Range:          [±5V ▼]
Sample Rate:            [30000 Hz]
Compression Ratio:      [30:1]
Measurement Duration:   [10.0 s]
```

### 2. 코드에서 설정 가져오기

```python
# Test Settings Dialog 열기
dialog = TestSettingsDialog(parent=self)
if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
    settings = dialog.get_settings()
    
    # DAQ 설정 적용
    voltage_range = settings['voltage_range']      # 5.0 or 10.0
    sample_rate = settings['sample_rate']          # Hz
    compression_ratio = settings['compression_ratio']
    duration = settings['measurement_duration']
    
    # ni_daq.py에 전달
    result = daq_service.read_current_channels_hardware_timed(
        channels=['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5'],
        sample_rate=sample_rate,
        compress_ratio=compression_ratio,
        duration_seconds=duration
    )
```

### 3. ni_daq.py에서 voltage_range 적용

```python
def read_current_channels_hardware_timed(
    self, 
    channels: List[str], 
    sample_rate: float = 30000.0,
    compress_ratio: int = 30,
    duration_seconds: float = 10.0,
    voltage_range: float = 5.0  # ← 새 파라미터
):
    # Voltage range 적용
    min_val = -voltage_range
    max_val = voltage_range
    
    task.ai_channels.add_ai_voltage_chan(
        channel_name,
        terminal_config=nidaqmx.constants.TerminalConfiguration.DIFF,
        min_val=min_val,
        max_val=max_val,
        units=nidaqmx.constants.VoltageUnits.VOLTS
    )
```

## 📊 계산 예시

### Sample Rate = 30,000 Hz
```
1ms당 샘플 수 = 30,000 / 1,000 = 30 samples
```

### Compression 30:1
```
Raw samples: 30,000 Hz × 10초 = 300,000 samples
Compressed: 300,000 / 30 = 10,000 samples
```

### 실제 데이터 포인트
```
10초 측정 → 10,000 개 압축 데이터 포인트
→ 1ms당 1개 데이터 포인트
```

## ✅ 완료 사항

- [x] UI 파일에 DAQ Configuration 그룹박스 추가
- [x] Voltage Range ComboBox 추가
- [x] Sample Rate SpinBox 추가
- [x] Compression Ratio SpinBox 추가
- [x] Measurement Duration DoubleSpinBox 추가
- [x] load_settings() 업데이트
- [x] save_settings() 업데이트
- [x] restore_defaults() 업데이트
- [x] Dialog 크기 조정 (450×650)

## 🔜 다음 단계

1. **main.py 업데이트**: Test Settings Dialog에서 받은 DAQ 설정을 ni_daq.py에 전달
2. **ni_daq.py 업데이트**: voltage_range 파라미터 추가
3. **설정 저장/로드**: QSettings를 사용해 설정을 영구 저장

## 📝 테스트 방법

```python
# 테스트 코드
from ui.test_settings_dialog import TestSettingsDialog
from PyQt6.QtWidgets import QApplication

app = QApplication([])
dialog = TestSettingsDialog()
dialog.show()
app.exec()

# 설정 확인
settings = dialog.get_settings()
print(f"Voltage Range: ±{settings['voltage_range']}V")
print(f"Sample Rate: {settings['sample_rate']} Hz")
print(f"Compression: {settings['compression_ratio']}:1")
print(f"Duration: {settings['measurement_duration']}s")
```

---

**완료!** UI에서 DAQ 설정을 변경할 수 있습니다! 🎉
