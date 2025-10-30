# DOU - Device & Power Testing System

## 프로그램 개요

DOU는 모바일 디바이스 테스트를 위한 통합 전력 및 성능 측정 시스템입니다. HVPM(High Voltage Power Module)과 NI DAQ(National Instruments Data Acquisition) 장비를 활용하여 정밀한 전력 측정과 자동화된 테스트 시나리오를 실행할 수 있습니다.

## 주요 기능

### 1. 전력 측정 및 모니터링
- **HVPM 제어**: 전압/전류 실시간 모니터링 및 설정
- **NI DAQ 다채널 측정**: 최대 8채널 동시 전압/전류 측정
- **실시간 데이터 수집**: 1초 간격 데이터 로깅
- **Excel 결과 자동 저장**: Test_Results 및 Test_Summary 시트 생성

### 2. 자동화 테스트 시스템
- **시나리오 기반 테스트**: 사전 정의된 테스트 시퀀스 자동 실행
- **ADB 통합**: Android 디바이스 자동 제어 (화면 ON/OFF, 앱 실행 등)
- **Phone App 시나리오**: Default Settings + Init mode + DAQ monitoring + Phone app test
- **Progress Bar**: 실시간 테스트 진행률 표시

### 3. 사용자 인터페이스
- **반응형 레이아웃**: 다양한 화면 해상도 지원
- **실시간 상태 표시**: 연결 상태 색상 피드백 (초록색/빨간색)
- **멀티 채널 모니터**: 별도 창에서 모든 채널 동시 모니터링
- **System Log**: 실시간 작업 로그 표시

### 4. 데이터 분석 및 보고
- **통계 정보**: 평균, 최소, 최대, 범위 자동 계산
- **Excel 리포트**: 시나리오별 자동 파일명 생성
- **Power Rail 별 분석**: 각 레일별 상세 통계 정보

## 시스템 구조

### 핵심 컴포넌트

```
main.py
├── HVPM Service (services/hvpm.py)
│   └── 전압/전류 제어 및 모니터링
├── NI DAQ Service (services/ni_daq.py)
│   └── 다채널 데이터 수집
├── ADB Service (services/adb_service.py)
│   └── Android 디바이스 제어
├── Test Scenario Engine (services/test_scenario_engine.py)
│   └── 자동화 테스트 실행 및 관리
└── Auto Test Service (services/auto_test.py)
    └── 백그라운드 테스트 조정
```

### 테스트 시나리오 구조

```
test_scenarios/
├── scenarios/
│   ├── common/
│   │   ├── base_scenario.py (기본 시나리오 클래스)
│   │   └── default_settings.py (공통 설정)
│   └── phone_app/
│       └── phone_app_scenario.py (Phone App 테스트)
├── configs/
│   ├── test_config.py (테스트 설정)
│   └── wifi_config.py (WiFi 설정)
└── scripts/
    └── (테스트 실행 스크립트)
```

## 주요 기술 스택

- **UI Framework**: PyQt6
- **데이터 처리**: Pandas, NumPy
- **Excel 출력**: xlsxwriter, openpyxl
- **하드웨어 제어**: 
  - NI-DAQmx (National Instruments)
  - 커스텀 HVPM 프로토콜
  - Android Debug Bridge (ADB)
- **그래프**: pyqtgraph

## 워크플로우

### 1. 초기 설정
```
1. HVPM 연결 (USB/시리얼)
2. NI DAQ 디바이스 연결 및 채널 선택
3. ADB를 통한 Android 디바이스 연결
4. 각 연결 상태 확인 (색상 피드백)
```

### 2. 테스트 설정
```
1. Test Settings 다이얼로그에서 시나리오 선택
2. DAQ 채널 활성화 및 Rail 이름 설정
3. 측정 모드 선택 (전압/전류)
4. 목표 전압 설정
```

### 3. 테스트 실행
```
1. "Start Test" 버튼 클릭
2. 자동 시퀀스 실행:
   - Default Settings 적용
   - HVPM Init mode 진입
   - DAQ 데이터 수집 시작
   - Phone app 테스트 실행
3. 실시간 Progress 업데이트
4. 완료 후 Excel 자동 저장
```

### 4. 결과 분석
```
1. 생성된 Excel 파일 열기
   - Test_Results: 전체 데이터
   - Test_Summary: 통계 요약
2. 각 Power Rail별 성능 확인
3. 시간대별 전력 소비 분석
```

## 주요 개선 사항 (최근)

### UI 반응성 개선
- 테스트 실행을 별도 스레드로 분리
- Qt Signal/Slot 기반 스레드 간 통신
- Stop 버튼 실시간 반응

### Excel 출력 개선
- Summary 시트 추가 (통계 정보)
- Rail별 구분된 레이아웃
- 수식 오류 방지

### 로그 최적화
- 과도한 로그 출력 방지
- 의미 있는 정보만 표시
- 10초 간격 대기 로그

### 연결 상태 표시
- Connect/Disconnect 버튼 즉시 색상 반영
- Refresh 버튼과 독립적으로 동작

## 파일 구조

```
/workspace/
├── main.py                     # 메인 애플리케이션
├── requirements.txt            # Python 패키지 의존성
├── .gitignore                 # Git 제외 파일 목록
│
├── ui/                        # UI 정의 파일
│   ├── main_ui.ui             # Qt Designer 파일
│   ├── multi_channel_monitor.py
│   └── test_settings_dialog.py
│
├── generated/                 # UI 자동 생성 코드
│   └── main_ui.py
│
├── services/                  # 백엔드 서비스
│   ├── hvpm.py               # HVPM 제어
│   ├── ni_daq.py             # NI DAQ 인터페이스
│   ├── adb_service.py        # ADB 제어
│   ├── test_scenario_engine.py
│   ├── auto_test.py
│   ├── theme.py              # UI 테마
│   └── adaptive_ui.py        # 반응형 UI
│
├── test_scenarios/           # 테스트 시나리오
│   ├── scenarios/
│   ├── configs/
│   └── scripts/
│
├── lib/                      # 유틸리티 라이브러리
│   ├── act_library.py
│   ├── device.py
│   └── utils.py
│
└── docs/                     # 문서 (참고 자료)
    ├── PROJECT_OVERVIEW.md   # 이 문서
    ├── AUTO_TEST_GUIDE.md
    ├── UI_IMPROVEMENTS.md
    └── (기타 개발 문서들)
```

## 사용 예시

### 기본 전력 측정
```
1. HVPM 연결 후 "Connect" 클릭
2. 원하는 전압 입력 후 "Set Voltage" 클릭
3. "Read V/I" 클릭하여 현재 상태 확인
4. "Start Monitor" 클릭으로 실시간 모니터링
```

### Phone App 테스트 실행
```
1. 모든 장비 연결 확인 (HVPM, DAQ, ADB)
2. "Test Settings" 버튼 클릭
3. "PhoneApp_Scenario" 선택
4. DAQ 채널 설정 (예: VBAT, VSYS 활성화)
5. "Start Test" 클릭
6. 테스트 진행 상황 모니터링
7. 완료 후 Excel 파일 확인
```

### 멀티 채널 모니터링
```
1. NI DAQ 연결 및 채널 설정
2. "Multi-Channel Monitor" 버튼 클릭
3. 별도 창에서 모든 채널 동시 확인
4. 실시간 전압/전류 값 표시
```

## 트러블슈팅

### HVPM 연결 실패
- USB 케이블 연결 확인
- 장치 관리자에서 COM 포트 확인
- "Refresh" 버튼으로 재검색

### NI DAQ 인식 안됨
- NI-DAQmx 드라이버 설치 확인
- NI MAX에서 디바이스 테스트
- 채널 이름 형식 확인 (ai0, ai1, ...)

### ADB 디바이스 없음
- USB 디버깅 활성화 확인
- `adb devices` 명령으로 수동 확인
- 드라이버 재설치

### Excel 파일 열림 오류
- 파일이 다른 프로그램에서 열려있는지 확인
- 권한 문제 확인
- xlsxwriter 패키지 설치 확인

## 개발자 정보

- **Thread 안전성**: Qt Signal/Slot 메커니즘 사용
- **데이터 수집**: 1초 간격, 최대 10초까지
- **Excel 포맷**: xlsxwriter 우선, openpyxl 대체
- **로그 레벨**: info, warn, error, success

## 향후 계획

- [ ] 더 많은 테스트 시나리오 추가
- [ ] 실시간 그래프 기능 개선
- [ ] 데이터베이스 기반 이력 관리
- [ ] 웹 기반 리포트 생성
- [ ] 자동 이상 감지 알고리즘

## 라이센스

(라이센스 정보 추가)

---

**최종 업데이트**: 2025-10-30
**버전**: 1.0
**개발 환경**: Python 3.13, PyQt6, NI-DAQmx
