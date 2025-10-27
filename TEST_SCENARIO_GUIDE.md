# 테스트 시나리오 가이드

## 🎯 개요
본격적인 테스트 시나리오 시스템이 구현되었습니다. "Screen on/off" 시나리오를 예시로 체계적인 테스트 자동화가 가능합니다.

## 🔧 시스템 구성

### 제어 대상 (3가지)
1. **테스트 단말 (ADB)**: Android 디바이스 제어
2. **HVPM**: 전원 공급 및 전압 제어  
3. **DAQ**: Multi-channel 전류 측정

## 📋 "Screen On/Off" 시나리오 상세

### 🚀 테스트 시퀀스

#### 1️⃣ **초기 설정 (Initialization)**
```
- 테스트 단말: 4V 전원 ON 상태
- HVPM: 4V로 초기화 설정
- DAQ: Multi-channel monitor에서 enable된 채널들 준비
```

#### 2️⃣ **테스트 시작 (Test Start)**
1. **HVPM 4V 설정**
   - 테스트 전압 4V로 설정
   - 전압 안정화 대기

2. **단말 초기화**
   - Flight mode ON
   - Recent App 초기화  
   - Lockscreen 해제 설정

3. **홈 화면 진입**
   - LCD ON 상태에서 Home key 입력
   - Home screen 진입 확인

#### 3️⃣ **안정화 대기 (Stabilization)**
- **대기 시간**: 20초
- **목적**: HVPM 전류 안정화
- **이유**: 앱 실행 시 전류 스파이크 현상 안정화

#### 4️⃣ **DAQ 모니터링 시작**
- **측정 간격**: 1초 (1Hz)
- **측정 대상**: Enable된 모든 채널의 실시간 전류
- **데이터 수집**: 시작 시점부터 자동 기록

#### 5️⃣ **스크린 On/Off 테스트 실행**
```
시작: LCD ON
반복: 2초 간격으로 LCD ON/OFF 
지속: 20초간 측정 진행
패턴: ON(1초) → OFF(1초) → ON(1초) → OFF(1초) ...
```

#### 6️⃣ **데이터 수집 완료**
- **DAQ 모니터링 중지**
- **수집된 데이터**: 각 rail별 전류 측정값
- **데이터 포맷**: 타임스탬프 + 채널별 전류값

#### 7️⃣ **결과 저장 (Excel Export)**
- **파일명**: `screen_onoff_test_YYYYMMDD_HHMMSS.xlsx`
- **시트1**: Test_Data (측정 데이터)
- **시트2**: Test_Summary (테스트 요약)

## 📊 데이터 구조

### Test_Data 시트
| 컬럼 | 설명 | 예시 |
|------|------|------|
| timestamp | 측정 시각 | 2025-10-27 10:30:15 |
| time_elapsed | 경과 시간(초) | 15.5 |
| ai0_current | 채널0 전류(A) | 0.125 |
| ai1_current | 채널1 전류(A) | 0.089 |
| ... | 추가 채널들 | ... |

### Test_Summary 시트
- 테스트 이름, 시작/종료 시간
- 테스트 지속 시간, 상태
- 데이터 포인트 수
- 채널별 평균 전류

## 🎮 사용 방법

### 1️⃣ **사전 준비**
1. **Multi-Channel Monitor 설정**
   - Tools → Multi-Channel Monitor 열기
   - 측정할 채널들 Enable
   - 각 채널의 Rail 이름 설정

2. **디바이스 연결 확인**
   - ADB 디바이스 연결
   - HVPM 연결
   - NI DAQ 연결

### 2️⃣ **테스트 실행**
1. **시나리오 선택**
   - Auto Test 섹션에서 "Screen On/Off" 선택

2. **테스트 시작**
   - "Start Auto Test" 버튼 클릭
   - 확인 대화상자에서 "Yes" 선택

3. **진행 상황 모니터링**
   - Progress Bar로 진행률 확인
   - Log 창에서 실시간 상태 확인

### 3️⃣ **결과 확인**
1. **자동 저장**
   - 테스트 완료 시 Excel 파일 자동 생성
   - 파일 위치: 실행 폴더

2. **수동 내보내기**
   - 테스트 완료 후 "Save detailed results" 선택
   - 원하는 위치에 저장

## ⚙️ 고급 설정

### 시나리오 커스터마이징
```python
# services/test_scenario_engine.py에서 수정 가능
screen_onoff_config = TestConfig(
    name="Screen On/Off",
    hvpm_voltage=4.0,           # HVPM 전압
    stabilization_time=20.0,    # 안정화 시간
    monitoring_interval=1.0,    # 측정 간격
    test_duration=20.0          # 테스트 지속시간
)
```

### 추가 시나리오 생성
1. `TestConfig` 객체 생성
2. `TestStep` 리스트 정의
3. `_register_builtin_scenarios()`에 등록

## 🚨 주의사항

### 하드웨어 요구사항
- **NI DAQ**: Multi-channel 측정 지원
- **Android 디바이스**: ADB 디버깅 활성화
- **HVPM**: 전압 제어 기능

### 테스트 환경
- **안정된 전원**: 측정 정확도를 위해 필수
- **디바이스 고정**: 테스트 중 물리적 움직임 방지
- **백그라운드 앱**: 측정 영향을 위해 최소화

## 📈 확장 가능성

### 추가 시나리오 예시
1. **CPU Stress Test**: CPU 부하 테스트
2. **WiFi On/Off**: 무선 통신 전력 테스트  
3. **Camera Test**: 카메라 동작 전력 측정
4. **Gaming Test**: 게임 실행 전력 프로파일

### 데이터 분석
- **전력 프로파일 분석**: 시간대별 전력 소비 패턴
- **효율성 측정**: 기능별 전력 효율 비교
- **배터리 수명 예측**: 사용 패턴 기반 예측

---
*테스트 시나리오 시스템 v1.0 - 2025.10.27*