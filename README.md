# DOU - Device & Power Testing System

통합 전력 측정 및 디바이스 테스트 자동화 시스템

## 빠른 시작

### 일반 사용자 (실행 파일)

1. **최신 릴리스 다운로드**
   - Releases에서 `DoU_Auto_Test_Toolkit_vX.X.zip` 다운로드

2. **필수 드라이버 설치**
   - **NI-DAQmx**: [National Instruments](https://www.ni.com/en-us/support/downloads/drivers/download.ni-daqmx.html)에서 다운로드
   - **ADB (선택)**: Android 기기 제어용

3. **프로그램 실행**
   - ZIP 파일 압축 해제
   - `DoU_Auto_Test_Toolkit.exe` 더블클릭

### 개발자

1. **의존성 설치**
   ```bash
   pip install -r requirements.txt
   ```

2. **NI-DAQmx 드라이버 설치**
   - [National Instruments](https://www.ni.com/en-us/support/downloads/drivers/download.ni-daqmx.html)에서 다운로드
   - DAQ 기능 사용에 필수

3. **프로그램 실행**
   ```bash
   python main.py
   ```

4. **실행 파일 빌드 (선택사항)**
   ```bash
   # Windows
   build_exe.bat
   
   # Linux/Mac
   ./build_exe.sh
   ```
   자세한 빌드 방법은 [BUILD_GUIDE.md](BUILD_GUIDE.md) 참고

## 주요 기능

- 🔌 **HVPM & NI DAQ 제어**: 정밀한 전력 측정 및 다채널 모니터링
- 🤖 **자동화 테스트**: ADB 기반 Android 디바이스 자동 제어
- 📊 **Excel 리포트**: 자동 데이터 수집 및 통계 분석
- 💻 **반응형 UI**: 실시간 상태 피드백 및 진행률 표시

## 문서

상세한 사용법과 시스템 구조는 다음 문서를 참고하세요:

- **[📘 프로젝트 개요](docs/PROJECT_OVERVIEW.md)** - 전체 시스템 소개 및 사용법
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

---

**최종 업데이트**: 2025-10-30
