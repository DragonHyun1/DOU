# USB 충전 하드웨어 제어 문제 및 해결 방법

## 📊 문제 분석

### 측정 결과
```
USB 연결 전:        3.95V  ✓ (HVPM 4.0V 공급, 정상)
USB 연결 후:        4.15V  ✗ (USB VBUS 충전 간섭)
Refresh 버튼 후:    4.15V  ✗ (여전히 충전 중)
                           ↑
                  소프트웨어 명령으로 제어 불가
```

### 근본 원인

**소프트웨어 vs 하드웨어 충전 제어의 차이:**

1. **소프트웨어 충전 제어 (현재 구현)**
   ```bash
   adb shell dumpsys battery set usb 0
   adb shell dumpsys battery set ac 0
   adb shell dumpsys battery unplug
   ```
   - ✅ 시스템 배터리 상태 변경 (USB powered: false)
   - ✅ 배터리 관리 앱/서비스에 "충전 안 함" 알림
   - ❌ **실제 충전 IC는 계속 작동**
   - ❌ **VBUS → Battery Rail 전류 계속 흐름**

2. **하드웨어 충전 제어 (필요한 것)**
   - 충전 IC의 EN(Enable) 핀 제어
   - PMIC의 charging_enabled 레지스터 제어
   - 물리적으로 VBUS 전류 차단

### 왜 하드웨어 제어가 안 될까?

```
충전 IC (PMIC)
├─ Software Interface (/sys/class/power_supply/...)
│  ├─ Root 권한 필요
│  └─ OEM Lock으로 제한될 수 있음
│
└─ Hardware Control
   ├─ Charging Enable Pin
   └─ Current Limit Register
```

**현재 폰 상태:**
- Root 권한 없음 (`su : invalid uid/gid '-c'`)
- Bootloader Lock 상태로 추정
- `/sys/class/power_supply/*` 접근 불가

---

## ✅ 해결 방법

### **방법 1: ADB over Wi-Fi (추천!) 🌟**

**장점:**
- ✅ Root 권한 불필요
- ✅ 가장 간단하고 안전
- ✅ USB VBUS 물리적으로 제거됨

**단점:**
- ⚠️ Wi-Fi 연결 필요
- ⚠️ Wi-Fi 끄기 테스트 시 재설정 필요

**실행 방법:**
```bash
./setup_adb_wifi.sh
```

**수동 설정:**
```bash
# 1. USB 연결 상태에서
adb tcpip 5555

# 2. 폰 IP 확인
adb shell ip addr show wlan0 | grep 'inet '

# 3. USB 케이블 제거

# 4. Wi-Fi로 연결
adb connect <phone_ip>:5555

# 5. 확인
adb devices
```

**테스트:**
```
1. Wi-Fi ADB 연결 완료
2. USB 케이블 물리적으로 제거됨
3. HVPM 4.0V만 공급 중
4. Refresh 버튼 클릭
5. DAQ 측정 → 3.95V 예상 ✅
```

---

### **방법 2: Data-Only USB 케이블**

**원리:**
```
일반 USB 케이블:
  Pin 1: VBUS (5V)     ← 이것이 문제!
  Pin 2: D- (Data)
  Pin 3: D+ (Data)
  Pin 4: GND

Data-Only 케이블:
  Pin 1: NC (연결 안 됨)  ← VBUS 없음
  Pin 2: D- (Data)       ✓ ADB 동작
  Pin 3: D+ (Data)       ✓ ADB 동작
  Pin 4: GND
```

**구매:**
- "USB Data Only Cable"
- "Charging Disabled USB Cable"
- "Sync Cable" (충전 안 되는 것)

**또는 자작:**
```
일반 USB 케이블을 열어서:
- VBUS (빨간선) 물리적으로 절단
- D+, D-, GND는 그대로 유지
```

---

### **방법 3: Root 권한 획득 (고급)**

**필요 작업:**
1. Bootloader Unlock
2. Custom Recovery 설치 (TWRP)
3. Magisk로 Root 획득

**Root 후 충전 제어:**
```bash
# Samsung 기기
adb shell "su -c 'echo 0 > /sys/class/power_supply/battery/charging_enabled'"

# Qualcomm PMIC
adb shell "su -c 'echo 0 > /sys/class/power_supply/usb/charging_enabled'"

# MTK 기기
adb shell "su -c 'echo 1 > /sys/class/power_supply/battery/batt_slate_mode'"
```

**주의:**
- ⚠️ Bootloader Unlock 시 데이터 초기화
- ⚠️ Knox 퓨즈 끊어짐 (Samsung Pay 등 사용 불가)
- ⚠️ OTA 업데이트 불가

---

### **방법 4: USB VBUS 물리적 차단**

**임시 방법:**
```
USB 케이블에 Diode 추가:
  Phone ←─┤◄├─ USB Host
         (역방향 차단)
  
ADB는 동작하나, 폰 → PC 방향만 전류 흐름
```

**또는 VBUS 핀 테이핑:**
```
USB 커넥터 Pin 1 (VBUS)에 절연 테이프 붙이기
→ 물리적으로 접촉 차단
```

---

## 🎯 권장 방법

### **상황별 추천:**

| 상황 | 추천 방법 | 이유 |
|------|----------|------|
| **Wi-Fi 사용 가능** | ADB over Wi-Fi | 가장 간단하고 안전 |
| Wi-Fi 테스트 필요 | Data-Only 케이블 | Wi-Fi 끄고도 ADB 가능 |
| 개발 전용 폰 | Root 권한 | 완벽한 제어 가능 |
| 긴급/임시 | VBUS 핀 테이핑 | 빠른 해결 |

---

## 📝 다음 단계

### 1단계: ADB over Wi-Fi 시도 (추천)
```bash
cd /workspace
./setup_adb_wifi.sh
```

### 2단계: 전압 재측정
```
1. USB 케이블 제거 상태
2. Wi-Fi ADB 연결 확인: adb devices
3. Refresh 버튼 클릭
4. DAQ 측정 → 3.95V 확인 ✅
```

### 3단계: Phone App 테스트
```
1. HVPM 4.0V 공급
2. Phone App Test 실행
3. 전체 시나리오 동안 전압 안정성 확인
4. 4.0V ± 0.05V 유지 확인
```

---

## 🔧 코드 수정 계획

**현재:**
- `ui/multi_channel_monitor.py`의 `single_read()`에서 `disable_usb_charging()` 호출
- 소프트웨어 충전 비활성화만 가능

**개선 (나중에):**
- ADB over Wi-Fi 자동 감지
- USB 연결 상태 경고 메시지
- Root 권한 자동 확인 및 하드웨어 제어 시도

---

**지금은 ADB over Wi-Fi로 해결하는 것이 가장 빠르고 안전합니다!** 🚀
