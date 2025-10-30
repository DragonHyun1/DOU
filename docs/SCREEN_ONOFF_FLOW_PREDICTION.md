# Screen On/Off 시나리오 실행 흐름 예상도

## 🎯 시나리오 선택 및 시작

### 📋 **사전 상태**
```
UI 상태:
├── testScenario_CB: "Screen On/Off" 선택됨
├── startAutoTest_PB: 활성화 (HVPM + ADB 연결 시)
├── stopAutoTest_PB: 비활성화
├── testProgress_PB: 0%
└── testStatus_LB: "Ready"

연결 상태:
├── HVPM: ✅ 연결됨 (예: 현재 3.2V)
├── ADB Device: ✅ 연결됨 (예: "SM-G998N")
└── NI DAQ: ✅ 연결됨 (예: "Dev1")
```

---

## 🚀 **실행 흐름 (단계별 예상)**

### **[사용자 액션]** Start Auto Test 버튼 클릭

#### **Step 0: 확인 대화상자**
```
📋 Dialog: "Start Auto Test"
┌─────────────────────────────────────────┐
│ Start test scenario: Screen On/Off?     │
│                                         │
│ This will control ADB device, HVPM,    │
│ and DAQ automatically.                  │
│ Make sure all required devices are      │
│ connected and configured properly.      │
│                                         │
│ Test duration: Approximately 1-2 min   │
│                                         │
│           [Yes]    [No]                 │
└─────────────────────────────────────────┘
```

---

### **Step 1: 초기화 (0-10%)**
```
⏱️  시간: 0-5초
📊 Progress: 0% → 10%
📝 Status: "Initializing test scenario..."

🔧 내부 동작:
├── TestScenarioEngine.start_test("screen_onoff") 호출
├── TestResult 객체 생성 (시작 시간 기록)
├── 11개 테스트 스텝 준비
└── 별도 스레드에서 실행 시작

📱 UI 업데이트:
├── startAutoTest_PB: 비활성화
├── stopAutoTest_PB: 활성화  
├── testProgress_PB: 10%
├── testStatus_LB: "Initializing test scenario..."
└── autoTestGroupBox: "Auto Test - RUNNING"
```

---

### **Step 2: HVPM 전압 설정 (10-20%)**
```
⏱️  시간: 5-7초
📊 Progress: 10% → 20%  
📝 Status: "Step 1/11: init_hvpm"

🔧 HVPM 동작:
├── 현재 전압 확인 (예: 3.2V)
├── 목표 전압 4.0V로 설정
├── hvpm_service.set_voltage(4.0) 실행
└── 전압 설정 완료 확인

📋 로그 출력:
[10:30:15] Step 1/11: init_hvpm
[10:30:16] HVPM voltage set to 4.0V
[10:30:17] ⚡ Voltage set to 4.0V, readback: 4.001V

📱 UI 업데이트:
├── hvpmVolt_LB: "4.001 V"
├── testProgress_PB: 20%
└── testStatus_LB: "HVPM voltage set to 4.0V"
```

---

### **Step 3: ADB 디바이스 설정 (20-30%)**
```
⏱️  시간: 7-10초
📊 Progress: 20% → 30%
📝 Status: "Step 2/11: init_adb"

🔧 ADB 동작:
├── 연결된 디바이스 확인 ("SM-G998N")
├── ADB 연결 상태 검증
└── 디바이스 준비 완료

📋 로그 출력:
[10:30:17] Step 2/11: init_adb  
[10:30:18] Connected to ADB device: SM-G998N
[10:30:19] ADB device ready for testing

📱 UI 업데이트:
├── testProgress_PB: 30%
└── testStatus_LB: "ADB device connected: SM-G998N"
```

---

### **Step 4: Flight Mode 활성화 (30-40%)**
```
⏱️  시간: 10-12초
📊 Progress: 30% → 40%
📝 Status: "Step 3/11: flight_mode"

🔧 ADB 명령어:
├── adb shell settings put global airplane_mode_on 1
├── adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true
└── Flight mode 활성화 완료

📋 로그 출력:
[10:30:19] Step 3/11: flight_mode
[10:30:20] Flight mode enabled
[10:30:21] Wireless connections disabled

📱 단말 화면:
┌─────────────────┐
│ ✈️ Flight Mode   │  ← 상단 상태바에 비행기 아이콘
│                 │
│   [Settings]    │
└─────────────────┘
```

---

### **Step 5: Recent Apps 정리 (40-50%)**
```
⏱️  시간: 12-15초
📊 Progress: 40% → 50%
📝 Status: "Step 4/11: clear_apps"

🔧 ADB 명령어:
├── adb shell am task kill-all
├── adb shell input keyevent KEYCODE_APP_SWITCH
├── adb shell input swipe 500 500 500 100 (앱 정리 제스처)
└── Recent apps 정리 완료

📋 로그 출력:
[10:30:21] Step 4/11: clear_apps
[10:30:22] Recent apps cleared
[10:30:24] Background processes minimized

📱 단말 동작:
├── 백그라운드 앱들 종료
├── 최근 앱 목록 정리
└── 메모리 정리 완료
```

---

### **Step 6: 화면 잠금 해제 (50-60%)**
```
⏱️  시간: 15-17초
📊 Progress: 50% → 60%
📝 Status: "Step 5/11: unlock_screen"

🔧 ADB 명령어:
├── adb shell input keyevent KEYCODE_WAKEUP (화면 켜기)
├── adb shell input swipe 500 1000 500 300 (위로 스와이프)
├── adb shell input keyevent KEYCODE_MENU (메뉴키)
└── 화면 잠금 해제 완료

📋 로그 출력:
[10:30:24] Step 5/11: unlock_screen
[10:30:25] Screen unlocked
[10:30:26] Device ready for interaction

📱 단말 화면:
┌─────────────────┐
│    🔓 UNLOCKED   │
│                 │
│   [Home Screen] │
└─────────────────┘
```

---

### **Step 7: 홈 화면 진입 (60-70%)**
```
⏱️  시간: 17-19초
📊 Progress: 60% → 70%
📝 Status: "Step 6/11: go_to_home"

🔧 ADB 명령어:
├── adb shell input keyevent KEYCODE_HOME
└── 홈 화면 진입 완료

📋 로그 출력:
[10:30:26] Step 6/11: go_to_home
[10:30:27] Navigated to home screen
[10:30:28] Home screen active

📱 단말 화면:
┌─────────────────┐
│  🏠 Home Screen │
│                 │
│  📱 📞 📧 🎵    │
│  🌐 📷 ⚙️ 📁    │
└─────────────────┘
```

---

### **Step 8: 전류 안정화 대기 (70-75%)**
```
⏱️  시간: 19-39초 (20초 대기)
📊 Progress: 70% → 75%
📝 Status: "Step 7/11: stabilize - 20s remaining → 1s remaining"

🔧 안정화 과정:
├── 20초 카운트다운 시작
├── 1초마다 진행률 업데이트
├── HVPM 전류 모니터링 (안정화 확인)
└── 전류 스파이크 안정화 완료

📋 로그 출력:
[10:30:28] Step 7/11: wait_stabilization
[10:30:29] Waiting for current stabilization (20 seconds)...
[10:30:30] Stabilization - 19s remaining
[10:30:31] Stabilization - 18s remaining
...
[10:30:47] Stabilization - 2s remaining  
[10:30:48] Stabilization - 1s remaining
[10:30:49] Current stabilization completed

📊 HVPM 전류 변화:
├── 초기: 0.245A (앱 로딩 스파이크)
├── 5초 후: 0.198A (안정화 시작)
├── 15초 후: 0.156A (거의 안정)
└── 20초 후: 0.152A (완전 안정)
```

---

### **Step 9: DAQ 모니터링 시작 (75-80%)**
```
⏱️  시간: 39-40초
📊 Progress: 75% → 80%
📝 Status: "Step 8/11: start_monitoring"

🔧 DAQ 설정:
├── Multi-channel monitor에서 enabled 채널 확인
├── 예: ai0(VDD_CORE), ai1(VDD_MEM), ai2(VDD_GPU) enabled
├── 1초 간격 모니터링 스레드 시작
└── 데이터 수집 배열 초기화

📋 로그 출력:
[10:30:49] Step 8/11: start_daq_monitoring
[10:30:50] DAQ monitoring started
[10:30:50] Monitoring channels: ai0, ai1, ai2
[10:30:50] Data collection interval: 1.0 seconds

📊 Multi-Channel Monitor:
┌─────────────────────────────────────┐
│ Multi-Channel Power Rail Monitor    │
├─────────────────────────────────────┤
│ ✅ ai0 VDD_CORE    0.152A  1.2V    │
│ ✅ ai1 VDD_MEM     0.089A  1.8V    │  
│ ✅ ai2 VDD_GPU     0.034A  1.0V    │
│ ❌ ai3 VDD_IO      ----    ----    │
└─────────────────────────────────────┘
```

---

### **Step 10: Screen On/Off 테스트 실행 (80-95%)**
```
⏱️  시간: 40-60초 (20초 테스트)
📊 Progress: 80% → 95%
📝 Status: "Step 9/11: screen_test - Screen ON/OFF cycle"

🔧 테스트 시퀀스:
├── 시작: LCD ON 상태 확인
├── 2초 간격으로 ON/OFF 반복 (총 10 사이클)
├── 각 상태 변화마다 로그 기록
└── DAQ에서 전류 변화 실시간 측정

📋 상세 실행 로그:
[10:30:50] Step 9/11: screen_on_off_cycle
[10:30:51] Starting screen on/off cycle (20 seconds, 2-second intervals)
[10:30:52] Screen ON (cycle 1/10)
[10:30:53] Screen OFF (cycle 1/10)  
[10:30:54] Screen ON (cycle 2/10)
[10:30:55] Screen OFF (cycle 2/10)
[10:30:56] Screen ON (cycle 3/10)
[10:30:57] Screen OFF (cycle 3/10)
...
[10:31:08] Screen ON (cycle 10/10)
[10:31:09] Screen OFF (cycle 10/10)
[10:31:10] Screen on/off cycle completed

📊 실시간 전류 변화:
시간    │ 화면상태 │ ai0(Core) │ ai1(Mem) │ ai2(GPU)
────────┼─────────┼──────────┼─────────┼─────────
10:30:52│   ON    │  0.245A  │ 0.156A  │ 0.189A
10:30:53│   OFF   │  0.152A  │ 0.089A  │ 0.034A  
10:30:54│   ON    │  0.241A  │ 0.154A  │ 0.185A
10:30:55│   OFF   │  0.151A  │ 0.088A  │ 0.033A
...

📱 단말 화면 변화:
┌─────────────────┐    ┌─────────────────┐
│  🌟 SCREEN ON   │ ←→ │  ⚫ SCREEN OFF  │
│                 │    │                 │  
│  밝은 홈 화면    │    │   검은 화면      │
└─────────────────┘    └─────────────────┘
     (0.24A)              (0.15A)
```

---

### **Step 11: DAQ 모니터링 중지 (95-98%)**
```
⏱️  시간: 60-61초
📊 Progress: 95% → 98%
📝 Status: "Step 10/11: stop_monitoring"

🔧 모니터링 종료:
├── 모니터링 스레드 중지 신호
├── 수집된 데이터 정리
├── 총 데이터 포인트 수 계산
└── 메모리 정리

📋 로그 출력:
[10:31:10] Step 10/11: stop_daq_monitoring
[10:31:11] DAQ monitoring stopped. Collected 21 data points
[10:31:11] Data collection completed successfully

📊 수집된 데이터 요약:
├── 총 측정 시간: 21초
├── 데이터 포인트: 21개 (1초 간격)
├── 측정 채널: 3개 (ai0, ai1, ai2)
└── 총 데이터 레코드: 63개
```

---

### **Step 12: Excel 파일 저장 (98-100%)**
```
⏱️  시간: 61-63초
📊 Progress: 98% → 100%
📝 Status: "Step 11/11: export_excel"

🔧 Excel 생성:
├── 파일명: screen_onoff_test_20251027_103111.xlsx
├── Test_Data 시트: 타임스탬프 + 채널별 전류 데이터
├── Test_Summary 시트: 테스트 정보 + 통계
└── 자동 포맷팅 적용

📋 로그 출력:
[10:31:11] Step 11/11: export_to_excel
[10:31:12] Enhanced Excel export completed: screen_onoff_test_20251027_103111.xlsx
[10:31:13] Test scenario completed successfully

📊 Excel 파일 구조:
screen_onoff_test_20251027_103111.xlsx
├── 📊 Test_Data 시트
│   ├── timestamp | time_elapsed | ai0_current | ai1_current | ai2_current
│   ├── 10:30:50  | 0.0          | 0.152       | 0.089       | 0.034
│   ├── 10:30:51  | 1.0          | 0.245       | 0.156       | 0.189
│   └── ... (21 rows)
└── 📋 Test_Summary 시트  
    ├── Test Name: Screen On/Off
    ├── Duration: 63.2 seconds
    ├── Data Points: 21
    ├── ai0 Average: 0.198A
    ├── ai1 Average: 0.122A
    └── ai2 Average: 0.111A
```

---

## ✅ **테스트 완료 (100%)**

### **최종 상태**
```
⏱️  총 소요 시간: ~63초
📊 Progress: 100%
📝 Status: "Test completed successfully"

📱 UI 최종 상태:
├── startAutoTest_PB: 활성화 (다시 테스트 가능)
├── stopAutoTest_PB: 비활성화
├── testProgress_PB: 100%
├── testStatus_LB: "Test completed successfully"
├── autoTestGroupBox: "Auto Test - COMPLETED"
└── 상태바: "Auto Test Completed Successfully"

📋 최종 로그:
[10:31:13] Test completed with 21 data points
[10:31:13] ✅ Screen On/Off scenario executed successfully
```

### **완료 대화상자**
```
📋 Dialog: "Test Complete"
┌─────────────────────────────────────────┐
│ Automated test completed successfully!  │
│                                         │
│ Test completed in 63.2 seconds         │
│ Collected 21 data points               │
│ 3 channels monitored                   │
│                                         │
│ Would you like to save detailed        │
│ test results?                          │
│                                         │
│           [Yes]    [No]                 │
└─────────────────────────────────────────┘
```

---

## 📊 **예상 결과 데이터**

### **전력 소비 패턴**
```
화면 ON 시:  VDD_CORE: 0.24A, VDD_MEM: 0.15A, VDD_GPU: 0.18A
화면 OFF 시: VDD_CORE: 0.15A, VDD_MEM: 0.09A, VDD_GPU: 0.03A

전력 절약: 약 38% (화면 OFF 시)
```

이것이 "Screen On/Off" 시나리오가 실행될 때의 전체적인 흐름 예상입니다! 🚀