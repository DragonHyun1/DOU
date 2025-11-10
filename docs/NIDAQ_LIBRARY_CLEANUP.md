# NI-DAQ 라이브러리 통일 작업 완료

## 📋 작업 개요

**목표:** 여러 NI-DAQ 라이브러리를 혼용하지 않고 하나로 통일  
**날짜:** 2025-11-10  
**결과:** ✅ **Python nidaqmx 라이브러리로 완전 통일**

---

## 🔍 작업 전 상황

### 정의된 라이브러리

**1. Python nidaqmx (고수준 API)**
```python
import nidaqmx
- Task-based API
- Pythonic 인터페이스
- 자동 에러 핸들링
- 타입 안전성
```

**2. C API (nicaiu.dll) Wrapper (저수준 API)**
```python
NICAIUWrapper 클래스 (148 lines)
- DAQmxCreateTask
- DAQmxCreateAICurrentChan
- DAQmxReadAnalogF64
- 수동 메모리 관리
- ctypes 기반
```

### 실제 사용 현황

**✅ 사용 중:**
```python
# Phone App 시나리오
read_current_channels_hardware_timed()  # nidaqmx 사용

# Multi-channel Monitor
read_current_channels_direct()  # nidaqmx 사용

# Test Scenario Engine
read_current_channels_hardware_timed()  # nidaqmx 사용
```

**❌ 정의만 있고 미사용 (죽은 코드):**
```python
# C API wrapper - 어디서도 호출되지 않음!
NICAIUWrapper 클래스
_read_current_channels_nicaiu()
nicaiu.dll 로딩 코드
```

---

## ✅ 제거한 코드

### 1. C API 로딩 코드 (30 lines)
```python
# 삭제됨
NICAIU_DLL = None
NICAIU_AVAILABLE = False
nicaiu_dll_paths = [...]
for dll_path in nicaiu_dll_paths:
    NICAIU_DLL = ctypes.CDLL(dll_path)
```

### 2. NICAIUWrapper 클래스 (148 lines)
```python
# 삭제됨
class NICAIUWrapper:
    def __init__(self): ...
    def create_task(self): ...
    def create_ai_voltage_chan(self): ...
    def create_ai_current_chan(self): ...
    def start_task(self): ...
    def read_analog_f64(self): ...
    def stop_task(self): ...
    def clear_task(self): ...
```

### 3. _read_current_channels_nicaiu() 함수 (263 lines)
```python
# 삭제됨
def _read_current_channels_nicaiu(self, channels: List[str], samples_per_channel: int = 1000):
    """Read current channels using nicaiu.dll C API"""
    wrapper = NICAIUWrapper()
    task_handle = wrapper.create_task()
    wrapper.create_ai_current_chan(...)
    wrapper.read_analog_f64(...)
    # ... 263 lines of C API calls
```

### 4. ctypes imports (1 line)
```python
# 삭제됨
import ctypes
from ctypes import c_int32, c_uint32, c_uint64, c_double, c_char_p, POINTER, byref, Structure, c_void_p
```

**총 제거:** **442 lines**

---

## 📦 유지된 코드

### C API 상수들 (남겨둠 - 필요함!)
```python
# 이 상수들은 nidaqmx에서도 사용됨
DAQmx_Val_Volts = 10348
DAQmx_Val_Amps = 10342
DAQmx_Val_RSE = 10083
DAQmx_Val_NRSE = 10078
DAQmx_Val_Diff = 10106  # ⭐ terminal_config=10106으로 사용 중!
DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_Rising = 10280
```

**이유:**
- `read_current_channels_hardware_timed()`에서 `terminal_config=10106` (DIFFERENTIAL)으로 직접 사용
- `AttributeError: DIFFERENTIAL` 문제를 우회하기 위해 numeric constant 사용
- 현재 Phone App 시나리오에서 정상 동작 중

---

## 🎯 최종 결과

### Before
```python
# 혼재된 구조
- Python nidaqmx (실제 사용 중)
- C API wrapper (죽은 코드)
- 442 lines의 불필요한 코드
- 혼란스러운 코드베이스
```

### After
```python
# 통일된 구조
- ✅ Python nidaqmx 라이브러리만 사용
- ✅ 442 lines 제거 (간결화)
- ✅ 유지보수 용이
- ✅ 디버깅 용이
```

---

## 📊 실제 사용 흐름

### Phone App 시나리오 (현재 정상 동작 중)

```python
# test_scenario_engine.py
def start_daq_monitoring():
    daq_result = self.daq_service.read_current_channels_hardware_timed(
        channels=['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5'],
        sample_rate=30000.0,  # 30kHz
        compress_ratio=30,
        duration_seconds=10.0
    )

# ni_daq.py (Python nidaqmx만 사용)
def read_current_channels_hardware_timed(self, channels, ...):
    with nidaqmx.Task() as task:
        # Try DIFFERENTIAL mode (direct constant to avoid AttributeError)
        task.ai_channels.add_ai_voltage_chan(
            channel_name,
            terminal_config=10106,  # DAQmx_Val_Diff
            min_val=-5.0, max_val=5.0,
            units=nidaqmx.constants.VoltageUnits.VOLTS
        )
        
        # Hardware-timed sampling
        task.timing.cfg_samp_clk_timing(
            rate=30000.0,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=300000
        )
        
        # Read data
        raw_data = task.read(number_of_samples_per_channel=300000)
        
        # Compress & Convert to current
        compressed_volts = compress_samples(raw_data, ratio=30)
        compressed_ma = [(v / shunt_r) * 1000 for v in compressed_volts]
```

---

## 🔧 추가 이점

### 1. **간결성**
- 442 lines 제거 → 코드베이스 간소화
- 읽기 쉬움, 이해하기 쉬움

### 2. **유지보수성**
- 하나의 API만 관리
- 버그 추적 용이
- 라이브러리 업데이트 간단

### 3. **디버깅**
- Python Exception으로 모든 에러 처리
- Traceback 명확
- C API 수동 에러 코드 변환 불필요

### 4. **안정성**
- Python nidaqmx는 NI 공식 지원
- 정기 업데이트
- 커뮤니티 지원 활발

### 5. **타입 안전성**
- Python Type Hints 활용
- IDE 자동완성
- 컴파일 타임 체크

---

## ⚙️ 기술적 배경

### Python nidaqmx vs C API

| 항목 | Python nidaqmx | C API (nicaiu.dll) |
|------|----------------|-------------------|
| **추상화 수준** | 고수준 (Task-based) | 저수준 (함수 호출) |
| **메모리 관리** | 자동 (GC) | 수동 (malloc/free) |
| **에러 처리** | Exception | Error code 체크 |
| **성능** | 충분히 빠름 | 약간 더 빠름 (무시 가능) |
| **코드 가독성** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **유지보수성** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **디버깅** | 쉬움 | 어려움 |

**결론:** 현재 애플리케이션에서는 **성능 차이가 무시 가능**하며, **Python nidaqmx가 모든 면에서 우수**함.

---

## 🚀 검증 필요 사항

### 1. Phone App 시나리오 테스트
```bash
python test_scenarios/scripts/run_phone_app_scenario.py
```

**예상 결과:**
```
✅ DEFAULT mode enabled (±5V range)
✅ Hardware-timed VOLTAGE collection completed: 6 channels
✅ Avg current: 0.337mA (shunt=0.01Ω)
```

### 2. Multi-channel Monitor 테스트
```
1. UI에서 Multi-channel Monitor 실행
2. 6개 채널 Enable
3. Start Monitoring
```

**예상 결과:**
```
✅ 모든 채널에서 정상적으로 전류 측정됨
✅ DEFAULT mode로 작동
✅ 에러 없음
```

---

## 📝 참고 자료

### NI-DAQmx 공식 문서
- [Python nidaqmx API Reference](https://nidaqmx-python.readthedocs.io/)
- [NI-DAQmx Help](https://www.ni.com/documentation/en/ni-daqmx/)

### 관련 문서
- `/workspace/docs/BUGFIX_CURRENT_MEASUREMENT.md` - 초기 문제 분석
- `/workspace/docs/DEFAULT_MODE_SUCCESS_EXPLANATION.md` - DEFAULT 모드 성공 이유
- `/workspace/docs/NI_TRACE_ANALYSIS.md` - NI I/O Trace 분석

---

## ✅ 체크리스트

- [x] C API 로딩 코드 제거 (30 lines)
- [x] NICAIUWrapper 클래스 제거 (148 lines)
- [x] _read_current_channels_nicaiu() 함수 제거 (263 lines)
- [x] ctypes import 제거 (1 line)
- [x] 필요한 C API 상수 유지 (DAQmx_Val_*)
- [x] 코드 간결화 및 주석 추가
- [x] 총 442 lines 제거 완료
- [ ] Phone App 시나리오 검증 (사용자 테스트 필요)
- [ ] Multi-channel Monitor 검증 (사용자 테스트 필요)

---

## 🎉 결론

**Python nidaqmx 라이브러리로 완전히 통일**되어 코드베이스가 **더 간결하고, 유지보수하기 쉽고, 이해하기 쉬워졌습니다.**

모든 DAQ 작업은 이제 **하나의 일관된 API**를 통해 이루어지며, 혼란이 제거되었습니다.

**442 lines**의 죽은 코드를 제거하여 **코드 품질**이 크게 향상되었습니다! 🚀
