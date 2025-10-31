# DOU - Device & Power Testing System

통합 전력 측정 및 디바이스 테스트 자동화 시스템

## 빠른 시작

### 설치
```bash
pip install -r requirements.txt
```

### 실행
```bash
python main.py
```

## 주요 기능

- 🔌 **HVPM & NI DAQ 제어**: 정밀한 전력 측정 및 다채널 모니터링
- 🤖 **자동화 테스트**: ADB 기반 Android 디바이스 자동 제어
- 📊 **Excel 리포트**: 자동 데이터 수집 및 통계 분석
- 💻 **반응형 UI**: 실시간 상태 피드백 및 진행률 표시

## 문서

### 📚 사용자 가이드
- **[⚡ 빠른 시작 가이드](docs/QUICK_START.md)** - 5분 안에 시작하기
- **[📖 사용자 매뉴얼](docs/USER_MANUAL.md)** - 전체 기능 설명 및 문제 해결

### 🔧 개발 문서
- **[📘 프로젝트 개요](docs/PROJECT_OVERVIEW.md)** - 전체 시스템 소개 및 아키텍처
- [자동 테스트 가이드](docs/AUTO_TEST_GUIDE.md)
- [UI 개선 사항](docs/UI_IMPROVEMENTS.md)
- [테스트 시나리오 구조](docs/TEST_SCENARIOS_ORGANIZATION_SUMMARY.md)

## 시스템 요구사항

- Python 3.12+
- PyQt6
- NI-DAQmx 드라이버 (NI DAQ 사용 시)
- Android Debug Bridge (ADB) - Android 디바이스 제어 시

## 주요 구성요소

```
├── main.py                 # 메인 애플리케이션
├── services/              # 백엔드 서비스 (HVPM, DAQ, ADB)
├── ui/                    # UI 정의 파일
├── test_scenarios/        # 테스트 시나리오
└── docs/                  # 문서 및 가이드
```

## 지원 하드웨어

- HVPM (High Voltage Power Module)
- NI DAQ (National Instruments Data Acquisition)
- Android 디바이스 (ADB 호환)

## 라이센스

(라이센스 정보)

## 배포 버전 사용

실행 파일 버전을 사용하는 경우:

```
1. dist/DoU_Auto_Test_Toolkit/ 폴더 열기
2. DoU_Auto_Test_Toolkit.exe 실행
3. 빠른 시작 가이드 참조
```

> 📘 **처음 사용하시나요?** [빠른 시작 가이드](docs/QUICK_START.md)를 확인하세요!

---

**최종 업데이트**: 2025-10-31
