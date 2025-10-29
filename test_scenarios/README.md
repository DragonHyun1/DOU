# 📁 Test Scenarios Package

체계적으로 정리된 테스트 시나리오 패키지입니다.

## 📂 폴더 구조

```
test_scenarios/
├── __init__.py                 # 패키지 초기화
├── README.md                   # 이 파일
├── scenarios/                  # 개별 시나리오 구현
│   ├── __init__.py
│   ├── common/                 # 공통 컴포넌트
│   │   ├── __init__.py
│   │   ├── base_scenario.py    # 기본 시나리오 클래스
│   │   ├── default_settings.py # 기본 설정 관리
│   │   └── test_steps.py       # 공통 테스트 단계
│   ├── phone_app/              # Phone App 시나리오
│   │   ├── __init__.py
│   │   └── phone_app_scenario.py
│   ├── screen_onoff/           # Screen On/Off 시나리오
│   │   ├── __init__.py
│   │   └── screen_onoff_scenario.py
│   └── browser_performance/    # Browser Performance 시나리오
│       ├── __init__.py
│       └── browser_performance_scenario.py
├── scripts/                    # 실행 스크립트
│   ├── test_phone_app_scenario.py
│   ├── debug_phone_app_test.py
│   └── test_scenario_loading.py
├── configs/                    # 설정 파일
│   ├── wifi_config.py          # WiFi 네트워크 설정
│   └── test_config.py          # 전역 테스트 설정
└── docs/                       # 문서
    ├── TEST_SCENARIO_GUIDE.md
    ├── PHONE_APP_SCENARIO_UPDATE.md
    └── ENHANCED_TEST_SYSTEM_REPORT.md
```

## 🎯 주요 특징

### 1. 모듈화된 구조
- **시나리오별 분리**: 각 테스트 시나리오가 독립적인 폴더에 구성
- **공통 컴포넌트**: 재사용 가능한 기능들을 common 폴더에 집중
- **설정 중앙화**: 모든 설정을 configs 폴더에서 관리

### 2. 확장 가능성
- **새 시나리오 추가**: `scenarios/` 아래 새 폴더만 생성
- **BaseScenario 상속**: 공통 인터페이스로 일관성 보장
- **설정 재사용**: 기존 설정들을 새 시나리오에서 재활용

### 3. 유지보수성
- **명확한 책임 분리**: 각 컴포넌트의 역할이 명확
- **문서화**: 각 폴더별 상세 문서 제공
- **테스트 스크립트**: 독립적인 테스트 및 디버깅 도구

## 🚀 사용 방법

### 새 시나리오 추가하기

1. **폴더 생성**
```bash
mkdir test_scenarios/scenarios/new_scenario
```

2. **시나리오 클래스 구현**
```python
# test_scenarios/scenarios/new_scenario/new_scenario.py
from ..common.base_scenario import BaseScenario, TestConfig, TestStep

class NewScenario(BaseScenario):
    def get_config(self) -> TestConfig:
        # 시나리오 설정 정의
        pass
    
    def execute_step(self, step: TestStep) -> bool:
        # 단계별 실행 로직
        pass
```

3. **패키지에 등록**
```python
# test_scenarios/scenarios/new_scenario/__init__.py
from .new_scenario import NewScenario
__all__ = ['NewScenario']

# test_scenarios/__init__.py
from .scenarios.new_scenario.new_scenario import NewScenario
```

### 기존 시나리오 실행하기

```python
from test_scenarios.scenarios.phone_app import PhoneAppScenario

# 시나리오 인스턴스 생성
scenario = PhoneAppScenario(
    hvpm_service=hvpm_service,
    daq_service=daq_service,
    adb_service=adb_service,
    log_callback=log_callback
)

# 시나리오 실행
success = scenario.run()
```

## 📋 시나리오 목록

### 1. Phone App Test
- **경로**: `scenarios/phone_app/`
- **설명**: Phone 앱 사용 중 전력 소모 테스트
- **단계**: Default Settings → Init Mode → Phone App Test → Data Export

### 2. Screen On/Off Test (예정)
- **경로**: `scenarios/screen_onoff/`
- **설명**: 화면 켜기/끄기 전력 소모 테스트

### 3. Browser Performance Test (예정)
- **경로**: `scenarios/browser_performance/`
- **설명**: 브라우저 성능 및 전력 소모 테스트

## ⚙️ 설정 관리

### WiFi 설정
```python
from test_scenarios.configs.wifi_config import WiFiConfig

# 2.4GHz 네트워크 정보 가져오기
wifi_2g = WiFiConfig.get_2g_primary()
```

### 테스트 설정
```python
from test_scenarios.configs.test_config import TestConfig

# 환경 설정 가져오기
env = TestConfig.get_environment()
hvpm_voltage = env['hvpm_voltage']
```

## 🔍 디버깅

### 디버그 스크립트 실행
```bash
cd test_scenarios/scripts
python debug_phone_app_test.py
```

### 개별 시나리오 테스트
```bash
cd test_scenarios/scripts
python test_phone_app_scenario.py
```

## 📚 문서

- **TEST_SCENARIO_GUIDE.md**: 테스트 시나리오 작성 가이드
- **PHONE_APP_SCENARIO_UPDATE.md**: Phone App 시나리오 업데이트 내역
- **ENHANCED_TEST_SYSTEM_REPORT.md**: 시스템 개선 보고서

---

이 구조를 통해 테스트 시나리오들을 체계적으로 관리하고 쉽게 확장할 수 있습니다! 🎯