# Refresh 버튼 전압 측정 테스트

## 🎯 목적
Refresh 버튼의 USB 충전 비활성화가 실제 Battery Rail 전압에 영향을 주는지 확인

## 📋 테스트 절차

### 1단계: 초기 설정
- [x] HVPM에서 4.0V 공급 시작
- [x] USB 케이블 연결 (ADB 사용 위해)
- [x] DAQ 데이터 수집 시작

### 2단계: Refresh 전 측정
```
[Refresh 버튼 누르기 전]

DAQ 측정값:
- VBAT = 4.15V  ← USB 충전 중
```

### 3단계: Refresh 버튼 클릭
```
UI에서 "Refresh" 또는 "Single Read" 버튼 클릭

콘솔 출력 확인:
🔌 Disabling USB/AC charging...
  ✓ USB charging set to 0
  ✓ AC charging set to 0
  ✓ Battery unplugged
  ✓ Software charging disabled successfully
  📊 voltage: 3998
  📊 Parsed: 3.998V
  
⚠️  Note: This disables SOFTWARE charging state.
    Hardware charging circuit may still be active.
    Measure actual battery rail voltage with DAQ to verify.
```

### 4단계: Refresh 후 측정
```
[5초 대기 후]

DAQ 측정값:
- VBAT = ???V  ← 이 값을 확인하세요!
```

## ✅ 예상 결과

### 시나리오 A: 성공 ✅
```
Refresh 전:  4.15V
Refresh 후:  3.95V  ← 200mV 감소
결론: 소프트웨어 충전 비활성화로 하드웨어도 멈춤!
```

### 시나리오 B: 실패 ⚠️
```
Refresh 전:  4.15V
Refresh 후:  4.15V  ← 변화 없음
결론: 하드웨어 충전 회로는 계속 작동 중
     → Root 권한 또는 하드웨어 수정 필요
```

## 🔧 시나리오 B인 경우 해결 방법

### Option 1: Root 권한 충전 제어
```bash
# su 명령 형식 테스트
adb shell "su -c 'id'"
adb shell "su 0 id"
adb shell su

# 성공하면:
adb shell "su -c 'echo 0 > /sys/class/power_supply/battery/charging_enabled'"
```

### Option 2: ADB over Wi-Fi
```bash
# USB 물리적 연결 없이 ADB 사용
adb tcpip 5555
adb connect <phone_ip>:5555
# USB 케이블 제거 후 테스트
```

### Option 3: 하드웨어 수정
- Data-Only USB 케이블 사용 (VBUS 없음)
- USB VBUS 라인 물리적 차단

---

**지금 이 테스트를 실행해서 "Refresh 후" 전압을 알려주세요!** 🎯
