# Traditional DAQ API 전환 가이드

## 🎯 문제 요약

**증상:**
- DoU 측정값: 1.256mA
- Manual 측정값: 0.409mA
- **비율: 약 3배 차이**

**근본 원인 가설:**
```
DoU:         DAQmx API (nidaqmx Python)
다른 툴:     Traditional DAQ API (DAQReadNChanNSamp1D)

→ 같은 하드웨어, 다른 API → 다른 결과!
```

---

## 📚 API 차이점

### Traditional DAQ API (다른 툴)

**특징:**
- Legacy API (2000년대 초)
- C/C++ 기반
- `nidaq32.dll` 사용
- 하드웨어 중심 (Hardware-centric)

**장점:**
```c
DAQReadNChanNSamp1D(...)
↓
- 하드웨어 Gain 자동 보상
- Calibration 자동 적용
- 간단하지만 정확!
```

---

### DAQmx API (현재 DoU)

**특징:**
- Modern API (2003년 이후)
- Python wrapper
- `nidaqmx` package
- 소프트웨어 중심 (Software-centric)

**단점:**
```python
task.read()
↓
- Range를 명시적으로 설정
- Raw data 반환
- 후처리 필요 (I = V / R)
- 보정 과정에서 오차 가능?
```

---

## 🔧 해결 방법

### 1. Traditional DAQ API 사용

**새로 만든 모듈:**
- `services/traditional_daq.py`
- `ctypes`로 `nidaq32.dll` 직접 호출
- 다른 툴과 **정확히 같은 API** 사용!

**주요 함수:**
```python
from services.traditional_daq import get_traditional_daq_service, DAQ_DEFAULT

# Traditional DAQ 사용
trad_daq = get_traditional_daq_service()

result = trad_daq.read_current_channels(
    device_name="Dev1",
    channels=["ai0", "ai1", "ai2", "ai3", "ai4", "ai5"],
    shunt_resistors=[0.01, 0.1, 0.1, 0.005, 0.05, 0.05],
    num_samples=10000,
    terminal_config=DAQ_DEFAULT  # 하드웨어 점퍼 따름!
)

# 결과:
# result['ai0']['avg_current_ma'] = ???mA
# 다른 툴과 동일한 값이 나올까?
```

---

### 2. 비교 테스트 스크립트

**파일:** `test_traditional_vs_daqmx.py`

**실행:**
```bash
cd /workspace
python test_traditional_vs_daqmx.py
```

**테스트 내용:**
1. Traditional DAQ로 측정
2. DAQmx로 측정
3. 두 결과 비교

**예상 결과:**

#### Case A: Traditional DAQ가 Manual과 일치
```
Traditional DAQ: 0.409mA  ✓ (Manual과 동일!)
DAQmx:           1.256mA  ✗ (3배 차이)

→ 결론: API 차이가 원인!
→ DoU를 Traditional DAQ로 전환해야 함!
```

#### Case B: 두 API 모두 비슷한 값
```
Traditional DAQ: 1.250mA
DAQmx:           1.256mA

→ 결론: API는 문제 아님
→ 다른 원인 조사 필요 (Shunt 값? 하드웨어?)
```

---

## 🚨 필요한 사전 작업

### Traditional DAQ 설치 확인

**1. DLL 확인:**
```
위치: C:\Windows\System32\nidaq32.dll

만약 없다면:
→ "NI-DAQ (Legacy)" 설치 필요
→ NI 웹사이트에서 다운로드
```

**2. 설치 버전:**
```
Traditional NI-DAQ 7.x 이상
(DAQmx와 별개!)
```

**3. 확인 방법:**
```bash
# Windows
dir C:\Windows\System32\nidaq32.dll

# Python에서
python test_traditional_vs_daqmx.py
→ "Traditional DAQ API not available" 메시지 확인
```

---

## 📝 DoU 코드 수정 계획

### 만약 Traditional DAQ가 정답이라면:

#### Step 1: `ni_daq.py` 백업
```bash
cp services/ni_daq.py services/ni_daq_daqmx_backup.py
```

#### Step 2: `read_current_channels_hardware_timed()` 수정
```python
# Before (DAQmx)
def read_current_channels_hardware_timed(...):
    with nidaqmx.Task() as task:
        task.ai_channels.add_ai_voltage_chan(...)
        data = task.read(...)
    return result

# After (Traditional DAQ)
def read_current_channels_hardware_timed(...):
    from services.traditional_daq import get_traditional_daq_service, DAQ_DEFAULT
    
    trad_daq = get_traditional_daq_service()
    
    if not trad_daq.is_available():
        # Fallback to DAQmx
        return self._read_using_daqmx(...)
    
    # Use Traditional DAQ (same as other tool!)
    result = trad_daq.read_current_channels(
        device_name=self.device_name,
        channels=channels,
        shunt_resistors=[...],
        num_samples=int(sample_rate * duration_seconds),
        terminal_config=DAQ_DEFAULT
    )
    
    return result
```

#### Step 3: 테스트
```bash
# Phone App Test 실행
python test_scenarios/scripts/run_phone_app_scenario.py

# 결과 확인
→ Manual 툴과 비교
→ 값이 일치하는지 확인!
```

---

## 🎯 다음 단계

### 1. **지금 즉시:**
```bash
python test_traditional_vs_daqmx.py
```

### 2. **결과 분석:**
- Traditional DAQ 값 vs Manual 값
- DAQmx 값 vs Manual 값
- 어느 것이 더 가까운가?

### 3. **결정:**

#### 만약 Traditional DAQ = Manual:
```
✓ API 차이가 원인!
✓ DoU를 Traditional DAQ로 전환
✓ 문제 해결!
```

#### 만약 둘 다 Manual과 다름:
```
✗ API는 문제 아님
✗ 다른 원인 조사:
  - Shunt 저항 값 실측
  - 하드웨어 연결 재확인
  - Calibration 상태 확인
```

---

## 📚 참고자료

### Traditional DAQ API 문서
- NI-DAQ Function Reference
- `DAQReadNChanNSamp1D` 함수
- Legacy DAQ API 매뉴얼

### DLL 경로
```
C:\Windows\System32\nidaq32.dll
C:\Program Files (x86)\National Instruments\...
```

### Python ctypes 사용법
```python
import ctypes
dll = ctypes.WinDLL("nidaq32.dll")
dll.DAQReadNChanNSamp1DWfm.argtypes = [...]
```

---

## ✅ 예상 결과

**만약 이 접근이 정답이라면:**

### Before (DAQmx):
```
VBAT:        1.256mA  (DoU)
Manual:      0.409mA
Difference:  3.07x    ✗
```

### After (Traditional DAQ):
```
VBAT:        0.409mA  (DoU with Traditional API)
Manual:      0.409mA
Difference:  1.00x    ✓ 일치!
```

---

**이제 테스트해보세요!** 🎯
```bash
python test_traditional_vs_daqmx.py
```
