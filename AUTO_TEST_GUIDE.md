NI I/O Trace에서 dump 받은 것 공유 

[Self-Calibration 기능]
1.  DAQSelfCalibrate ("Dev1", "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:23:15.1923      Call Duration 00:00:18.2035
Status: 0

[Enable 되어있는 ai voltage 측정 실행시킨 결과]
1.  DAQCreateAIVoltageChan ("_unnamedTask<9>", "", "Dev1/ai0", RSE, -5.000000 (-5.000000E+00), 5.000000 (5.000000E+00), Volts, "", "Dev1/ai0", "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6652      Call Duration 00:00:00.0009
Status: 0
2.  DAQCreateAIVoltageChan ("_unnamedTask<9>", "", "Dev1/ai1", RSE, -5.000000 (-5.000000E+00), 5.000000 (5.000000E+00), Volts, "", "Dev1/ai1", "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6662      Call Duration 00:00:00.0000
Status: 0
3.  setTimingI32EnumAP ("_unnamedTask<9>", "", SampTimingType, Sample Clock, "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6662      Call Duration 00:00:00.0000
Status: 0
4.  setTimingI32EnumAP ("_unnamedTask<9>", "", SampQuant.SampMode, Finite Samples, "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6662      Call Duration 00:00:00.0000
Status: 0
5.  setTimingF64U64AP ("_unnamedTask<9>", "", SampQuant.SampPerChan, 1000.000000 (1.000000E+03), "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6662      Call Duration 00:00:00.0000
Status: 0
6.  setTimingI32EnumAP ("_unnamedTask<9>", "", SampClk.ActiveEdge, Rising, "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6672      Call Duration 00:00:00.0000
Status: 0
7.  setTimingF64AP ("_unnamedTask<9>", "", SampClk.Rate, 500.000000 (5.000000E+02), "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6672      Call Duration 00:00:00.0000
Status: 0
8.  setTimingTerminalAP ("_unnamedTask<9>", "", SampClk.Src, "", "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6672      Call Duration 00:00:00.0000
Status: 0
9.  DAQControl ("_unnamedTask<9>", "Start", "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6672      Call Duration 00:00:00.0169
Status: 0
10.  DAQReadNChanNSamp2DF64 ("_unnamedTask<9>", 1000 (0x3E8), 10.000000 (1.000000E+01), 0 (0x0), 2 (0x2), 1000 (0x3E8), {1.75661,1.76097,...}, "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 13:25:38.6841      Call Duration 00:00:01.9990
Status: 0
11.  DAQControl ("_unnamedTask<9>", "Stop", "")
Process ID: 0x00009DA8         Thread ID: 0x00009B98
Start Time: 13:25:40.6832      Call Duration 00:00:00.0089
Status: 0
12.  DAQDestroyTask110 ("_unnamedTask<9>", "")
Process ID: 0x00009DA8         Thread ID: 0x00009B98
Start Time: 13:25:40.6921      Call Duration 00:00:00.0000
Status: 0







# HVPM Monitor Auto Test 기능 가이드

## 🚀 개요

HVPM Monitor의 자동 테스트 기능은 ADB를 통한 디바이스 제어와 HVPM을 통한 전력 측정을 결합하여 자동화된 테스트를 수행할 수 있는 강력한 도구입니다.

### 주요 특징
- **전압 안정화**: 테스트 시작 전 디바이스 안정화를 위한 전압 설정
- **자동 시나리오**: 다양한 테스트 시나리오 지원
- **실시간 모니터링**: 테스트 중 전압/전류 실시간 측정
- **진행률 추적**: 테스트 진행 상황 시각적 표시

## 📋 테스트 시나리오

### 1. Screen On/Off Test
- **설명**: 화면 켜기/끄기를 반복하여 디스플레이 관련 전력 소모 측정
- **동작**:
  1. 화면 켜기 (KEYCODE_WAKEUP)
  2. 지정된 시간 대기 (기본 10초)
  3. 화면 끄기 (KEYCODE_POWER)
  4. 지정된 시간 대기 (기본 5초)
  5. 지정된 사이클 수만큼 반복 (기본 5회)

### 2. Screen On/Off Long Test
- **설명**: 더 긴 주기의 화면 켜기/끄기 테스트
- **특징**: 10사이클, 15초 ON, 10초 OFF

### 3. CPU Stress Test
- **설명**: CPU 부하를 발생시켜 고부하 상황에서의 전력 소모 측정
- **동작**:
  1. CPU 스트레스 프로세스 시작
  2. 지정된 시간 동안 유지 (기본 60초)
  3. 스트레스 프로세스 종료

### 4. CPU Stress Long Test
- **설명**: 장시간 CPU 스트레스 테스트 (5분)

## ⚙️ 설정 및 구성

### 전압 설정
1. **Stabilization Voltage (안정화 전압)**
   - 기본값: 4.8V
   - 목적: 테스트 시작 전 디바이스가 꺼지지 않도록 안정적인 전압 제공
   - 권장 범위: 4.5V - 5.0V

2. **Test Voltage (테스트 전압)**
   - 기본값: 4.0V
   - 목적: 실제 테스트 수행 시 사용할 전압
   - 권장 범위: 3.0V - 4.5V (테스트 목적에 따라 조정)

### 디바이스 연결
1. **HVPM 연결**: USB를 통한 HVPM 디바이스 연결 필요
2. **ADB 연결**: USB 디버깅이 활성화된 Android 디바이스 연결 필요

## 🔄 테스트 실행 과정

### 1. 초기화 단계 (0-20%)
- 연결 상태 확인
- 안정화 전압 설정 (4.8V)
- 10초간 전압 안정화 대기

### 2. 테스트 준비 (20-30%)
- 테스트 전압 설정 (4.0V)
- 전압 안정화 확인

### 3. 테스트 실행 (30-100%)
- 선택된 시나리오 실행
- 실시간 진행률 업데이트
- ADB 명령어를 통한 디바이스 제어
- HVPM을 통한 전력 측정

## 📱 사용 방법

### 기본 사용 순서

1. **디바이스 연결**
   ```
   1. HVPM 디바이스를 USB로 연결
   2. Android 디바이스를 USB로 연결하고 USB 디버깅 활성화
   3. "Refresh" 버튼 클릭하여 디바이스 검색
   ```

2. **테스트 구성**
   ```
   1. Test Scenario 드롭다운에서 원하는 테스트 선택
   2. Stabilization Voltage 설정 (기본 4.8V)
   3. Test Voltage 설정 (기본 4.0V)
   ```

3. **테스트 실행**
   ```
   1. "Start Test" 버튼 클릭
   2. 확인 대화상자에서 설정 확인 후 "Yes" 클릭
   3. 테스트 진행 상황을 Progress Bar와 Status에서 확인
   4. 필요시 "Stop" 버튼으로 중단 가능
   ```

4. **결과 확인**
   ```
   1. 실시간 그래프에서 전압/전류 변화 관찰
   2. System Log에서 상세한 테스트 로그 확인
   3. File > Export Data로 측정 데이터 저장
   ```

## 🛠️ 고급 설정

### 커스텀 테스트 시나리오 추가

새로운 테스트 시나리오를 추가하려면 `services/auto_test.py`에서 `TestScenario` 클래스를 상속받아 구현:

```python
class CustomTest(TestScenario):
    def __init__(self):
        super().__init__("Custom Test", "사용자 정의 테스트")
    
    def execute(self, device: str, log_callback: Callable, progress_callback: Callable = None) -> bool:
        # 테스트 로직 구현
        pass
```

### ADB 명령어 확장

`services/adb.py`에 새로운 ADB 명령어 함수 추가 가능:

```python
def custom_command(device: str, parameter: str) -> bool:
    """사용자 정의 ADB 명령어"""
    return execute_command(device, f"custom_shell_command {parameter}")
```

## 📊 데이터 분석

### 측정 데이터 해석

1. **전압 변화**
   - 안정화 구간: 4.8V에서 시작하여 안정화
   - 테스트 구간: 4.0V로 변경 후 테스트 진행
   - 급격한 전압 변화 시 디바이스 상태 변화를 의미

2. **전류 변화**
   - 화면 ON: 전류 증가 (디스플레이 전력 소모)
   - 화면 OFF: 전류 감소 (대기 전력 소모)
   - CPU 스트레스: 지속적인 높은 전류 소모

### 데이터 내보내기

- **형식**: CSV (Time, Voltage, Current)
- **활용**: Excel, Python pandas 등으로 추가 분석 가능

## ⚠️ 주의사항

### 안전 수칙
1. **전압 범위**: 5.5V를 초과하지 않도록 주의
2. **디바이스 상태**: 테스트 전 디바이스 충전 상태 확인
3. **연결 안정성**: USB 케이블 연결 상태 확인

### 문제 해결

#### 연결 문제
- **HVPM 연결 실패**: 디바이스 드라이버 설치 확인
- **ADB 연결 실패**: USB 디버깅 활성화 및 권한 허용 확인

#### 테스트 실행 문제
- **테스트 시작 실패**: 모든 디바이스 연결 상태 확인
- **중간 중단**: 로그에서 오류 메시지 확인

#### 데이터 측정 문제
- **NaN 값**: HVPM 연결 상태 및 샘플링 설정 확인
- **불안정한 측정**: 전압 안정화 시간 증가 고려

## 🔧 개발자 정보

### 아키텍처
```
AutoTestService
├── TestScenario (추상 클래스)
│   ├── ScreenOnOffTest
│   ├── CPUStressTest
│   └── [사용자 정의 시나리오]
├── HvpmService (전압 제어)
└── ADB Service (디바이스 제어)
```

### 주요 클래스
- `AutoTestService`: 전체 테스트 관리
- `TestScenario`: 테스트 시나리오 기본 클래스
- `ScreenOnOffTest`: 화면 ON/OFF 테스트 구현
- `CPUStressTest`: CPU 스트레스 테스트 구현

### 시그널/슬롯
- `progress_updated`: 진행률 업데이트
- `test_completed`: 테스트 완료
- `voltage_stabilized`: 전압 안정화 완료

## 📈 성능 최적화

### 권장 설정
- **샘플링 주파수**: 10Hz (기본값)
- **버퍼 크기**: 600 샘플 (1분간 데이터)
- **안정화 시간**: 10초 (기본값)

### 시스템 요구사항
- **OS**: Windows 10/11, Linux, macOS
- **Python**: 3.8 이상
- **메모리**: 최소 4GB RAM
- **저장공간**: 100MB 이상

---

## 📞 지원

문제가 발생하거나 추가 기능이 필요한 경우:
1. System Log 확인
2. 오류 메시지 및 재현 단계 기록
3. 디바이스 및 환경 정보 수집

이 가이드를 통해 HVPM Monitor의 자동 테스트 기능을 효과적으로 활용하시기 바랍니다!

