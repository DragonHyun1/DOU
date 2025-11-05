# Traditional DAQ API 마이그레이션 완료

## ✅ 변경 완료

**날짜:** 2025-11-04  
**목적:** DoU를 다른 툴과 동일한 Traditional DAQ API로 변경하여 측정값 일치

---

## 📋 변경된 파일

### 1. `services/ni_daq.py`
**변경 내용:**
- `read_current_channels_hardware_timed()` 메서드가 이제 Traditional DAQ API 우선 사용
- Traditional DAQ 사용 → 실패 시 DAQmx fallback
- 기존 DAQmx 코드는 `_read_using_daqmx()` 메서드로 분리

**주요 변경:**
```python
def read_current_channels_hardware_timed(...):
    # 1. Traditional DAQ API 시도 (다른 툴과 동일!)
    from services.traditional_daq import get_traditional_daq_service, DAQ_DEFAULT
    trad_daq = get_traditional_daq_service()
    
    if trad_daq.is_available():
        # Use Traditional DAQ (SAME AS OTHER TOOL!)
        result = trad_daq.read_current_channels(
            device_name=self.device_name,
            channels=channels,
            shunt_resistors=[...],
            terminal_config=DAQ_DEFAULT  # Hardware jumper 따름!
        )
        return result  # ✓ 성공
    
    # 2. Fallback to DAQmx (Traditional DAQ 없을 때)
    return self._read_using_daqmx(...)
```

### 2. `services/traditional_daq.py` (신규)
**생성됨:**
- Traditional NI-DAQ API wrapper
- `DAQReadNChanNSamp1D` 사용 (다른 툴과 동일!)
- `ctypes`로 `nidaq32.dll` 직접 호출

**핵심 함수:**
```python
class TraditionalDAQService:
    def read_current_channels(
        device_name, 
        channels, 
        shunt_resistors, 
        num_samples=10000,
        terminal_config=DAQ_DEFAULT
    ):
        # Traditional DAQ API 호출
        # → 다른 툴과 100% 동일한 방식!
```

### 3. `requirements.txt`
**추가:**
```
numpy>=1.21.0  # Traditional DAQ API에서 사용
```

### 4. `test_traditional_vs_daqmx.py` (테스트 스크립트)
**생성됨:**
- Traditional DAQ vs DAQmx 비교 테스트
- 어느 것이 Manual 툴과 일치하는지 확인

---

## 🔄 작동 방식

### **우선순위 1: Traditional DAQ API**
```
Phone App Test 실행
    ↓
ni_daq.read_current_channels_hardware_timed()
    ↓
Traditional DAQ API 시도
    ↓
✓ 성공 → Traditional DAQ 사용 (다른 툴과 동일!)
    ↓
결과 반환 → Manual 툴과 일치 예상!
```

### **우선순위 2: DAQmx API (Fallback)**
```
Traditional DAQ 실패 (DLL 없음)
    ↓
DAQmx API 사용 (기존 방식)
    ↓
⚠️ 경고 메시지 출력
    ↓
결과 반환 (Manual과 차이 있을 수 있음)
```

---

## 🎯 예상 결과

### **Before (DAQmx Only):**
```
VBAT:        1.256mA  (DoU - DAQmx)
Manual:      0.409mA
Difference:  3.07x    ✗
```

### **After (Traditional DAQ):**
```
VBAT:        0.409mA  (DoU - Traditional DAQ)
Manual:      0.409mA
Difference:  1.00x    ✓ 일치!
```

---

## 🚀 테스트 방법

### **1. Phone App Test 실행**
```bash
cd /workspace
python test_scenarios/scripts/run_phone_app_scenario.py
```

**확인할 것:**
```
로그에서 찾기:
✓ "✅ SUCCESS: Traditional DAQ API (SAME AS OTHER TOOL!)"
  → Traditional DAQ 사용 성공!

또는:
⚠️ "⚠️ FALLBACK: Using DAQmx API"
  → Traditional DAQ 실패, DAQmx 사용 (DLL 필요)
```

### **2. 결과 비교**
```
1. DoU Phone App Test 결과 확인:
   test_results/phone_app_test_YYYYMMDD_HHMMSS/
   → phone_app_test_current_data.csv

2. Manual 툴 결과와 비교:
   VBAT 평균 전류 확인
   
3. 일치하는가?
   ✓ 일치 → Traditional DAQ API 성공!
   ✗ 여전히 차이 → 추가 조사 필요
```

### **3. 비교 테스트 (Optional)**
```bash
# Traditional DAQ vs DAQmx 직접 비교
python test_traditional_vs_daqmx.py
```

---

## ⚠️ 필수 조건

### **Traditional DAQ DLL 필요**

**확인:**
```bash
# Windows
dir C:\Windows\System32\nidaq32.dll
```

**만약 없다면:**
1. **Option A: 설치**
   - "NI-DAQ (Legacy)" 설치
   - NI 웹사이트에서 다운로드
   - 주의: DAQmx와는 별개 제품!

2. **Option B: Fallback 사용**
   - Traditional DAQ 없으면 자동으로 DAQmx 사용
   - 측정값은 Manual과 차이 있을 수 있음

---

## 📊 로그 메시지

### **성공 케이스:**
```
======================================================================
🔄 ATTEMPTING: Traditional DAQ API (same as other tool)
======================================================================
✓ Traditional DAQ API is available!
Channels: ['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5']
Shunt resistors: [0.01, 0.1, 0.1, 0.005, 0.05, 0.05]

=== Creating Traditional DAQ Task ===
Device: Dev1
Channels: ai0,ai1,ai2,ai3,ai4,ai5
Terminal Config: -1 (DEFAULT)
Range: -0.2V to 0.2V
✓ Task created: handle=1234

=== Reading Traditional DAQ (DAQReadNChanNSamp1DWfm) ===
✓ Read 10000 samples per channel

✓ Traditional DAQ read successful!
  ai0 (VBAT): 0.409mA (compressed to 10000 samples)
  ai1 (VDD_1P8_AP): 0.365mA (compressed to 10000 samples)
  ...

======================================================================
✅ SUCCESS: Traditional DAQ API (SAME AS OTHER TOOL!)
======================================================================
```

### **Fallback 케이스:**
```
======================================================================
🔄 ATTEMPTING: Traditional DAQ API (same as other tool)
======================================================================
⚠️ Traditional DAQ API not available
⚠️ Traditional DAQ module not found: No module named 'ctypes'

======================================================================
⚠️ FALLBACK: Using DAQmx API (may have measurement differences)
======================================================================
=== DAQmx FALLBACK: Hardware-Timed VOLTAGE Collection ===
...
```

---

## 🔍 문제 해결

### **Q1: "Traditional DAQ API not available"**
**원인:** `nidaq32.dll` 없음  
**해결:**
```
1. NI-DAQ (Legacy) 설치
2. 또는 DAQmx fallback 사용 (자동)
```

### **Q2: 여전히 Manual과 차이**
**가능한 원인:**
```
1. Shunt 저항 값 차이 확인
2. 하드웨어 연결 재확인
3. Calibration 상태 확인
4. Terminal Configuration 확인 (DEFAULT vs RSE)
```

### **Q3: Import 에러**
```python
ImportError: cannot import name 'get_traditional_daq_service'
```
**해결:**
```bash
# services/__init__.py 확인
cd /workspace
ls -la services/traditional_daq.py

# Python path 확인
export PYTHONPATH=/workspace:$PYTHONPATH
```

---

## 📚 참고 문서

- `TRADITIONAL_DAQ_SOLUTION.md` - 상세 가이드
- `NI_DAQ_API_COMPARISON.md` - API 차이점 분석
- `services/traditional_daq.py` - 구현 코드
- `test_traditional_vs_daqmx.py` - 비교 테스트

---

## ✅ 체크리스트

변경 후 확인:
- [x] `ni_daq.py` Traditional DAQ 우선 사용
- [x] `traditional_daq.py` 신규 생성
- [x] `requirements.txt` numpy 추가
- [x] DAQmx fallback 유지
- [ ] Phone App Test 실행 → **지금 테스트!**
- [ ] Manual 툴과 결과 비교 → **확인 필요!**

---

**다음 단계: Phone App Test 실행 및 결과 확인** 🚀
