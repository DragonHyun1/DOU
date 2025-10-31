# DoU Auto Test Toolkit - 사용자 매뉴얼

## 목차
1. [시작하기](#시작하기)
2. [초기 설정](#초기-설정)
3. [기본 기능](#기본-기능)
4. [자동 테스트](#자동-테스트)
5. [데이터 모니터링](#데이터-모니터링)
6. [문제 해결](#문제-해결)

---

## 시작하기

### 필수 요구사항

#### 소프트웨어
- **Windows 10/11** (64-bit)
- **NI-DAQmx 드라이버** (National Instruments)
  - 다운로드: https://www.ni.com/en-us/support/downloads/drivers/download.ni-daqmx.html
- **Monsoon Power Monitor SDK** (HVPM 장비 사용 시)
  - 다운로드: https://www.msoon.com/downloads
- **Android SDK Platform Tools** (ADB 사용 시)
  - 다운로드: https://developer.android.com/studio/releases/platform-tools

#### 하드웨어
- **Monsoon HVPM** (전력 측정 장비) - 선택사항
- **NI DAQ 장비** (데이터 수집) - 선택사항
- **Android 기기** (자동 테스트 대상) - 선택사항

### 프로그램 실행

1. **DoU_Auto_Test_Toolkit.exe** 더블클릭
2. 프로그램이 시작되면 메인 화면이 표시됩니다

> ⚠️ **주의**: 처음 실행 시 Windows Defender가 경고할 수 있습니다. "추가 정보" → "실행"을 선택하세요.

---

## 초기 설정

### 1. 장비 연결 확인

#### HVPM (전력 측정 장비) 연결

1. **HVPM 장비 연결**
   - USB 케이블로 PC와 HVPM 연결
   - 전원 켜기

2. **프로그램에서 확인**
   - 좌측 상단 "Connection" 섹션 확인
   - **"Port" 버튼** 클릭 → 장비 자동 검색
   - HVPM 콤보박스에 시리얼 번호가 표시되면 연결 성공 ✅
   - 상태: "Connected ✅" (녹색)

3. **연결 실패 시**
   - 상태: "Not Connected ❌" (빨간색)
   - Monsoon SDK가 설치되어 있는지 확인
   - USB 케이블 재연결 후 "Port" 버튼 다시 클릭

#### DAQ (데이터 수집 장비) 연결

1. **DAQ 장비 연결**
   - USB/네트워크로 PC와 DAQ 연결

2. **프로그램에서 확인**
   - "DAQ Device" 콤보박스에서 장비 선택
   - **"Connect" 버튼** 클릭
   - 버튼이 녹색으로 변하면 연결 성공 ✅
   - 버튼이 빨간색이면 연결 실패 ❌

3. **Multi-Channel 모니터링** (선택사항)
   - "Multi-Ch Monitor" 버튼 클릭
   - 다중 채널 실시간 모니터링 창 열림

#### ADB (Android 기기) 연결

1. **Android 기기 준비**
   - USB 디버깅 활성화:
     ```
     설정 → 개발자 옵션 → USB 디버깅 ON
     ```
   - USB 케이블로 PC 연결

2. **프로그램에서 확인**
   - "ADB Port" 콤보박스에 기기 ID 표시
   - "ADB Refresh" 버튼으로 기기 목록 갱신
   - 기기가 보이면 연결 성공 ✅

---

## 기본 기능

### HVPM 전압 설정 및 측정

#### 1. 전압 읽기
```
1. "HVPM Status" 섹션으로 이동
2. "Read V/I" 버튼 클릭
3. 현재 전압/전류 확인
   - Voltage: X.XX V
   - Current: X.XXXX A
```

#### 2. 전압 설정
```
1. "HVPM Output" 입력 필드에 원하는 전압 입력 (예: 4.0)
2. "Set Voltage" 버튼 클릭
3. 로그에서 설정 완료 확인:
   [HVPM] Vout set 4.00 V
```

> ⚠️ **주의**: 
> - 전압 범위: 0.0 ~ 5.5V
> - 비정상 범위 입력 시 확인 메시지 표시

#### 3. 실시간 모니터링
```
1. "Start Monitoring" 버튼 클릭
2. 실시간 전압/전류 그래프 표시
3. "Stop Monitoring" 버튼으로 중지
```

### DAQ 데이터 수집

#### 단일 채널 모드
```
1. DAQ 장비 연결 확인
2. "NI Monitor" 버튼 클릭
3. 실시간 데이터 수집 시작
4. 같은 버튼으로 중지
```

#### 멀티 채널 모드
```
1. "Multi-Ch Monitor" 버튼 클릭
2. 새 창에서 여러 채널 동시 모니터링
3. 채널별 독립적 그래프 표시
4. 창 닫기로 중지
```

---

## 자동 테스트

### 테스트 시나리오 실행

DoU Auto Test Toolkit은 자동화된 테스트 시나리오를 지원합니다.

#### 1. 테스트 준비

**필수 조건:**
- ✅ HVPM 연결됨
- ✅ ADB 기기 연결됨
- ✅ 테스트할 앱이 기기에 설치됨

#### 2. 테스트 시작

```
1. "Auto Test" 섹션으로 이동

2. 테스트 시나리오 선택:
   - Screen On/Off Test: 화면 켜기/끄기 반복
   - Phone App Scenario: 전화 앱 테스트
   - Custom Script: 사용자 정의 스크립트

3. "Start Test" 버튼 클릭

4. 확인 다이얼로그에서 "Yes" 클릭
   - 테스트 시간: 약 1-2분
   - 전압 설정 자동 조정됨

5. 진행 상황 확인:
   - Progress Bar: 진행률 표시
   - Log Window: 실시간 로그
   - Status: 현재 단계 표시
```

#### 3. 테스트 단계

자동 테스트는 다음 순서로 진행됩니다:

```
📋 Phase 1: 초기화
├─ 장비 연결 확인
└─ 테스트 환경 준비

⚡ Phase 2: 전압 안정화
├─ 안정화 전압 설정 (기본: 4.8V)
├─ 대기 시간: 10초
└─ 전압 확인

🔧 Phase 3: 테스트 전압 설정
├─ 테스트 전압 설정 (기본: 4.0V)
└─ 전압 확인

🚀 Phase 4: 테스트 시나리오 실행
├─ ADB 명령 실행
├─ 전력 데이터 수집
└─ 결과 저장

✅ Phase 5: 완료
├─ 데이터 저장
└─ 보고서 생성
```

#### 4. 테스트 중지

```
긴급 중지가 필요한 경우:
1. "Stop Test" 버튼 클릭
2. 확인 다이얼로그에서 "Yes"
3. 테스트 즉시 중단
```

#### 5. 결과 확인

테스트 완료 후:
```
1. 로그 창에서 테스트 결과 확인
2. 수집된 데이터는 자동 저장
3. 실패 시 오류 메시지 확인
```

### 테스트 설정 변경 (고급)

기본 설정을 변경하려면:

```python
# main.py의 test_config 수정
test_config = {
    'stabilization_voltage': 4.8,  # 안정화 전압 (V)
    'test_voltage': 4.0,            # 테스트 전압 (V)
    'test_cycles': 5,               # 반복 횟수
    'test_duration': 10,            # 각 사이클 시간 (초)
    'stabilization_time': 10,       # 안정화 대기 시간 (초)
    'sampling_interval': 1.0,       # 샘플링 간격 (초)
    'skip_stabilization_data': True # 안정화 데이터 제외
}
```

---

## 데이터 모니터링

### 로그 창 사용법

#### 로그 레벨 이해하기

로그 창에는 다양한 색상으로 메시지가 표시됩니다:

- 🟢 **INFO** (녹색): 일반 정보
  ```
  [HVPM] Connected, serial=12345
  [ADB] Device selected: emulator-5554
  ```

- 🟡 **WARN** (노란색): 경고 메시지
  ```
  ⚠️ Test already running
  WARNING: No ADB devices found
  ```

- 🔴 **ERROR** (빨간색): 오류 발생
  ```
  ❌ HVPM not connected
  ERROR: Device connection failed
  ```

- ⚫ **DEBUG** (회색): 디버그 정보
  ```
  Executing ADB command: adb -s device shell...
  ```

#### 로그 관리

```
- 로그 저장: "Save Log" 버튼 → 텍스트 파일로 저장
- 로그 지우기: "Clear Log" 버튼 → 모든 로그 삭제
- 자동 스크롤: 새 로그가 추가되면 자동으로 스크롤
```

### 실시간 그래프

HVPM 모니터링 활성화 시:

```
📊 그래프 구성:
├─ 상단 그래프: 전압 (Voltage)
│  └─ 파란색 선
└─ 하단 그래프: 전류 (Current)
   └─ 빨간색 선

⏱️ 시간 범위: 최근 60초
🔄 업데이트 주기: 100ms (10Hz)
```

---

## 문제 해결

### 자주 발생하는 문제

#### 1. HVPM 연결 안 됨

**증상:**
- Status: "Not Connected ❌"
- 콤보박스에 "-"만 표시

**해결방법:**
```
1. Monsoon SDK 설치 확인
   - 다운로드: https://www.msoon.com/downloads
   - 설치 후 PC 재시작

2. USB 케이블 확인
   - 데이터 전송 가능한 케이블 사용
   - 다른 USB 포트 시도

3. 장비 전원 확인
   - HVPM 전원 켜져 있는지 확인
   - LED 상태 확인

4. 프로그램 재시작
   - DoU Auto Test Toolkit 종료
   - HVPM USB 재연결
   - 프로그램 다시 실행
```

#### 2. DAQ 장비 인식 안 됨

**증상:**
- 콤보박스가 비어있음
- "Connect" 버튼 눌러도 빨간색

**해결방법:**
```
1. NI-DAQmx 드라이버 설치 확인
   - NI MAX (Measurement & Automation Explorer) 실행
   - 장비가 보이는지 확인

2. 장비 연결 확인
   - USB/네트워크 케이블 확인
   - 장비 전원 확인

3. 프로그램 재시작
```

#### 3. ADB 기기 인식 안 됨

**증상:**
- 콤보박스에 "No devices found"
- 기기가 연결되어 있는데도 안 보임

**해결방법:**
```
1. USB 디버깅 확인
   Android 기기:
   설정 → 개발자 옵션 → USB 디버깅 ON

2. USB 연결 모드 변경
   - 파일 전송 모드 선택
   - MTP 또는 PTP 모드

3. ADB 드라이버 재설치
   - Android SDK Platform Tools 다운로드
   - 설치 후 PC 재시작

4. 수동으로 ADB 확인
   명령 프롬프트에서:
   > adb devices
   
   기기가 보이면 "ADB Refresh" 버튼 클릭
```

#### 4. 자동 테스트 시작 안 됨

**증상:**
- "Start Test" 버튼 눌러도 시작 안 됨
- 오류 메시지 표시

**해결방법:**
```
1. 연결 상태 확인
   ✅ HVPM: Connected ✅
   ✅ ADB: 기기 선택됨

2. 로그 확인
   - "❌ No ADB device selected"
     → ADB Refresh 후 기기 선택
   
   - "❌ HVPM not connected"
     → HVPM 연결 후 Port 버튼 클릭
   
   - "⚠️ Test already running"
     → 진행 중인 테스트 완료 대기 또는 Stop Test

3. 프로그램 재시작
```

#### 5. CMD 창이 계속 뜨는 문제

**증상:**
- ADB 명령 실행 시 검은 창이 깜빡임
- 테스트 중 여러 CMD 창이 나타남

**해결방법:**
```
이 문제는 최신 버전에서 수정되었습니다.

업데이트 방법:
1. 최신 버전 다운로드
2. 기존 폴더 백업
3. 새 버전으로 교체

또는 소스 코드로 다시 빌드:
> build_exe.bat
```

#### 6. 테스트 중 에러 발생

**증상:**
- 테스트가 중간에 멈춤
- 오류 메시지와 함께 종료

**해결방법:**
```
1. 로그 확인
   - 빨간색 ERROR 메시지 찾기
   - 오류 내용 파악

2. 일반적인 원인:
   
   a) ADB 연결 끊김
      → USB 케이블 확인
      → 기기 재연결
   
   b) HVPM 전압 설정 실패
      → HVPM 재연결
      → 전압 범위 확인 (0-5.5V)
   
   c) 앱 실행 실패
      → 앱이 설치되어 있는지 확인
      → 패키지 이름 확인

3. 재시도
   - Stop Test
   - 문제 해결 후
   - Start Test
```

### 성능 최적화

#### 느린 응답 속도

```
문제: UI가 느리거나 멈춤

해결방법:
1. 불필요한 모니터링 중지
   - HVPM Monitor 중지
   - NI Monitor 중지

2. 로그 정리
   - Clear Log 버튼으로 오래된 로그 삭제

3. 그래프 비활성화
   - 테스트 중에는 모니터링 중지

4. 시스템 리소스 확인
   - 작업 관리자에서 CPU/메모리 사용량 확인
   - 다른 프로그램 종료
```

---

## 고급 기능

### 커스텀 테스트 스크립트

사용자 정의 ADB 명령을 실행할 수 있습니다.

```
1. 테스트 시나리오: "Custom Script" 선택

2. 스크립트 작성 (예시):
   input tap 500 500
   input swipe 100 500 100 100 300
   am start -n com.android.chrome/com.google.android.apps.chrome.Main
   sleep 5
   input keyevent 4

3. Start Test 클릭
```

### 데이터 내보내기

테스트 결과를 파일로 저장:

```
1. 로그 저장:
   - Save Log 버튼
   - .txt 파일로 저장

2. 수집 데이터:
   - 자동으로 저장됨
   - 위치: 프로그램 폴더/data/
```

---

## 단축키

| 기능 | 단축키 |
|------|--------|
| 장비 새로고침 | F5 |
| 로그 지우기 | Ctrl + L |
| 프로그램 종료 | Alt + F4 |

---

## 추가 정보

### 지원

문제가 계속되면:
- GitHub 이슈 등록
- 로그 파일 첨부
- 재현 방법 설명

### 업데이트

새 버전 확인:
- GitHub 릴리스 페이지 확인
- 변경 사항 확인 후 업데이트

### 라이선스

이 소프트웨어는 내부 사용을 위해 제공됩니다.

---

**DoU Auto Test Toolkit v1.0**  
*Last Updated: 2025-10-31*
