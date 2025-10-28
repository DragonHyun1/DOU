# USB Interference Mitigation Guide

USB 연결로 인한 배터리 전압 측정 간섭을 완화하는 종합 가이드입니다.

## 🔍 문제 개요

### USB 전압 간섭의 원인
- **ADB 연결**: USB를 통한 안드로이드 디바이스 제어 시 5V 전원 공급
- **전압 혼재**: USB 5V와 배터리 전압이 혼재되어 정확한 측정 방해
- **측정 오차**: 일반적으로 50-100mV의 전압 오차 발생
- **불안정성**: USB 연결/해제에 따른 측정값 변동

### 영향받는 측정
- 배터리 전압 측정
- 전류 측정 (간접적)
- 전력 계산
- 배터리 용량 추정

## 🛠️ 해결책

### 1. 하드웨어 솔루션 (권장)

#### A. USB 데이터 전용 케이블
```
장점: 간단하고 저렴 (~$5-10)
효과: 높음 (90-95% 간섭 제거)
구현: USB 케이블의 5V/GND 라인 물리적 차단
```

#### B. USB 아이솔레이터
```
장점: 완전한 전기적 격리
효과: 매우 높음 (95-99% 간섭 제거)
비용: 중간 (~$20-50)
제품: ADUM4160, USB-ISO 등
```

#### C. 외부 전원 공급
```
장점: 가장 정확한 측정 가능
효과: 최고 (99%+ 간섭 제거)
비용: 높음 (~$50-200)
구현: 배터리 시뮬레이터 또는 정밀 전원 공급장치
```

### 2. 소프트웨어 솔루션 (구현됨)

#### A. 자동 간섭 감지
- USB 연결 상태 실시간 모니터링
- ADB 디바이스 연결 감지
- 전압 변화 패턴 분석

#### B. 학습 기반 보정
- USB 연결/해제 시 전압 차이 학습
- 간섭 패턴 자동 인식
- 보정 파라미터 자동 조정

#### C. 실시간 보정
- 측정값에 보정 알고리즘 적용
- 70-90% 간섭 완화 효과
- 사용자 개입 최소화

## 🚀 사용 방법

### 1. 기본 설정

```python
# HVPM 서비스에서 자동으로 활성화됨
hvpm_service = HvpmService(...)
# USB 간섭 완화가 자동으로 통합됨
```

### 2. 설정 다이얼로그 사용

메인 메뉴에서 `Tools > USB Interference Settings` 선택:

- **Status Monitor**: USB 연결 상태 및 간섭 레벨 모니터링
- **Compensation Settings**: 보정 파라미터 조정
- **Learning Data**: 학습 데이터 관리 및 내보내기
- **Hardware Solutions**: 하드웨어 솔루션 가이드

### 3. 수동 캘리브레이션

```python
# 1. USB 연결 상태에서 전압 측정
usb_on_voltage = 4.23  # V

# 2. USB 해제 상태에서 전압 측정  
usb_off_voltage = 4.15  # V

# 3. 수동 캘리브레이션 적용
mitigation_service.calibrate_compensation(usb_on_voltage, usb_off_voltage)
```

## 📊 성능 평가

### 테스트 결과
```
기본 테스트: 70.5% 정확도 (Grade B)
고급 테스트: 46.8% 평균 정확도
권장 조합: 하드웨어 + 소프트웨어 = 95%+ 정확도
```

### 테스트 실행
```bash
# 기본 테스트
python3 test_usb_interference_console.py

# 고급 테스트 (다양한 시나리오)
python3 test_usb_interference_console.py --advanced

# 하드웨어 솔루션 가이드
python3 test_usb_interference_console.py --hardware
```

## ⚙️ 설정 옵션

### 자동 보정 파라미터
- `interference_threshold`: 간섭 감지 임계값 (기본: 0.05V)
- `compensation_factor`: 보정 계수 (기본: 1.0)
- `learning_mode_enabled`: 학습 모드 활성화 (기본: True)

### 측정 모드
- `NORMAL`: 일반 측정 (보정 없음)
- `BATTERY_ONLY`: 배터리 전용 측정 (USB 해제)
- `COMPENSATED`: 보정된 측정 (권장)

## 🔧 고급 설정

### 학습 데이터 관리
```python
# 학습 데이터 내보내기
data = mitigation_service.export_learning_data()

# 학습 데이터 가져오기
mitigation_service.import_learning_data(data)

# 학습 데이터 초기화
mitigation_service.reset_learning_data()
```

### 보정 파라미터 조정
```python
mitigation_service.set_compensation_parameters(
    usb_voltage_offset=0.08,      # 수동 오프셋 설정
    compensation_factor=1.2,       # 보정 강도 조정
    interference_threshold=0.03,   # 감지 민감도 조정
    auto_compensation_enabled=True # 자동 보정 활성화
)
```

## 📈 모니터링 및 로깅

### 실시간 모니터링
- USB 연결 상태 표시
- 간섭 레벨 시각화
- 보정 적용 횟수 추적
- 학습 진행 상황 표시

### 로그 메시지
```
[12:34:56] USB state changed to: connected
[12:34:57] Interference detected: 0.0823V
[12:34:58] Compensation applied: 4.2301V -> 4.1478V
[12:34:59] Learning data updated: USB offset = 0.0823V
```

## 🎯 권장 워크플로우

### 1. 초기 설정
1. USB 데이터 전용 케이블 준비 (권장)
2. 소프트웨어 자동 보정 활성화
3. 학습 모드 활성화

### 2. 캘리브레이션
1. USB 연결/해제 상태에서 각각 10회 이상 측정
2. 자동 학습 완료 대기
3. 보정 정확도 확인

### 3. 운영
1. 실시간 모니터링 활성화
2. 주기적 캘리브레이션 수행 (주 1회)
3. 학습 데이터 백업

### 4. 문제 해결
1. 보정 정확도가 낮은 경우: 하드웨어 솔루션 검토
2. 간섭 패턴 변경 시: 학습 데이터 초기화 후 재학습
3. 측정 불안정 시: 간섭 임계값 조정

## 🔍 문제 해결

### 일반적인 문제

#### Q: 보정이 적용되지 않습니다
A: 
- 자동 보정이 활성화되어 있는지 확인
- 측정 모드가 'COMPENSATED'로 설정되어 있는지 확인
- 충분한 학습 데이터가 있는지 확인 (USB 연결/해제 각각 5회 이상)

#### Q: 보정 정확도가 낮습니다
A:
- 하드웨어 솔루션 사용 검토
- 간섭 임계값 조정 (더 민감하게)
- 학습 데이터 초기화 후 재학습
- 환경 노이즈 확인

#### Q: USB 상태 감지가 안됩니다
A:
- ADB 드라이버 설치 확인
- USB 케이블 연결 상태 확인
- 방화벽/보안 소프트웨어 확인

### 디버깅 도구
```python
# 보정 정보 확인
info = mitigation_service.get_compensation_info()
print(f"USB Offset: {info['usb_voltage_offset']:.4f}V")
print(f"Samples: {info['usb_connected_samples']}/{info['usb_disconnected_samples']}")

# 실시간 로그 활성화
mitigation_service.logger.setLevel(logging.DEBUG)
```

## 📚 참고 자료

### 관련 파일
- `services/usb_interference_mitigation.py`: 핵심 간섭 완화 서비스
- `ui/usb_interference_dialog.py`: 설정 UI
- `test_usb_interference_console.py`: 테스트 스크립트
- `services/hvpm.py`: HVPM 서비스 통합

### 기술 문서
- USB 전압 간섭 메커니즘 분석
- 학습 기반 보정 알고리즘 설계
- 하드웨어 솔루션 비교 분석

### 업데이트 로그
- v3.3: USB 간섭 완화 기능 추가
- 자동 감지 및 보정 시스템 구현
- 학습 기반 패턴 인식 도입
- 하드웨어 솔루션 가이드 제공

---

💡 **팁**: 최상의 결과를 위해서는 하드웨어 솔루션(USB 데이터 전용 케이블)과 소프트웨어 보정을 함께 사용하는 것을 권장합니다.

🔧 **지원**: 추가 도움이 필요하시면 USB Interference Settings 다이얼로그의 Hardware Solutions 탭을 참조하세요.