# Screen On/Off Scenario Execution Flow Prediction

## 🎯 Scenario Selection and Start

### 📋 **Pre-conditions**
```
UI State:
├── testScenario_CB: "Screen On/Off" selected
├── startAutoTest_PB: enabled (when HVPM + ADB connected)
├── stopAutoTest_PB: disabled
├── testProgress_PB: 0%
└── testStatus_LB: "Ready"

Connection Status:
├── HVPM: ✅ Connected (e.g., current 3.2V)
├── ADB Device: ✅ Connected (e.g., "SM-G998N")
└── NI DAQ: ✅ Connected (e.g., "Dev1")
```

---

## 🚀 **Execution Flow (Step-by-Step Prediction)**

### **[User Action]** Start Auto Test Button Click

#### **Step 0: Confirmation Dialog**
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

### **Step 1: Initialization (0-10%)**
```
⏱️  Time: 0-5 seconds
📊 Progress: 0% → 10%
📝 Status: "Initializing test scenario..."

🔧 Internal Operations:
├── TestScenarioEngine.start_test("screen_onoff") called
├── TestResult object created (start time recorded)
├── 11 test steps prepared
└── Execution started in separate thread

📱 UI Updates:
├── startAutoTest_PB: disabled
├── stopAutoTest_PB: enabled  
├── testProgress_PB: 10%
├── testStatus_LB: "Initializing test scenario..."
└── autoTestGroupBox: "Auto Test - RUNNING"
```

---

### **Step 2: HVPM Voltage Setting (10-20%)**
```
⏱️  Time: 5-7 seconds
📊 Progress: 10% → 20%  
📝 Status: "Step 1/11: init_hvpm"

🔧 HVPM Operations:
├── Check current voltage (e.g., 3.2V)
├── Set target voltage to 4.0V
├── Execute hvpm_service.set_voltage(4.0)
└── Confirm voltage setting completion

📋 Log Output:
[10:30:15] Step 1/11: init_hvpm
[10:30:16] HVPM voltage set to 4.0V
[10:30:17] ⚡ Voltage set to 4.0V, readback: 4.001V

📱 UI Updates:
├── hvpmVolt_LB: "4.001 V"
├── testProgress_PB: 20%
└── testStatus_LB: "HVPM voltage set to 4.0V"
```

---

### **Step 3: ADB Device Setup (20-30%)**
```
⏱️  Time: 7-10 seconds
📊 Progress: 20% → 30%
📝 Status: "Step 2/11: init_adb"

🔧 ADB Operations:
├── Verify connected device ("SM-G998N")
├── Validate ADB connection status
└── Device ready confirmation

📋 Log Output:
[10:30:17] Step 2/11: init_adb  
[10:30:18] Connected to ADB device: SM-G998N
[10:30:19] ADB device ready for testing

📱 UI Updates:
├── testProgress_PB: 30%
└── testStatus_LB: "ADB device connected: SM-G998N"
```

---

### **Step 4: Flight Mode Activation (30-40%)**
```
⏱️  Time: 10-12 seconds
📊 Progress: 30% → 40%
📝 Status: "Step 3/11: flight_mode"

🔧 ADB Commands:
├── adb shell settings put global airplane_mode_on 1
├── adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true
└── Flight mode activation completed

📋 Log Output:
[10:30:19] Step 3/11: flight_mode
[10:30:20] Flight mode enabled
[10:30:21] Wireless connections disabled

📱 Device Screen:
┌─────────────────┐
│ ✈️ Flight Mode   │  ← Airplane icon in status bar
│                 │
│   [Settings]    │
└─────────────────┘
```

---

### **Step 8: Current Stabilization Wait (70-75%)**
```
⏱️  Time: 19-39 seconds (20 second wait)
📊 Progress: 70% → 75%
📝 Status: "Step 7/11: stabilize - 20s remaining → 1s remaining"

🔧 Stabilization Process:
├── 20-second countdown start
├── Progress update every second
├── HVPM current monitoring (stabilization check)
└── Current spike stabilization completed

📋 Log Output:
[10:30:28] Step 7/11: wait_stabilization
[10:30:29] Waiting for current stabilization (20 seconds)...
[10:30:30] Stabilization - 19s remaining
[10:30:31] Stabilization - 18s remaining
...
[10:30:47] Stabilization - 2s remaining  
[10:30:48] Stabilization - 1s remaining
[10:30:49] Current stabilization completed

📊 HVPM Current Changes:
├── Initial: 0.245A (app loading spike)
├── After 5s: 0.198A (stabilization start)
├── After 15s: 0.156A (nearly stable)
└── After 20s: 0.152A (fully stable)
```

---

### **Step 10: Screen On/Off Test Execution (80-95%)**
```
⏱️  Time: 40-60 seconds (20 second test)
📊 Progress: 80% → 95%
📝 Status: "Step 9/11: screen_test - Screen ON/OFF cycle"

🔧 Test Sequence:
├── Start: Verify LCD ON state
├── ON/OFF repeat at 2-second intervals (total 10 cycles)
├── Log each state change
└── Real-time current measurement via DAQ

📋 Detailed Execution Log:
[10:30:50] Step 9/11: screen_on_off_cycle
[10:30:51] Starting screen on/off cycle (20 seconds, 2-second intervals)
[10:30:52] Screen ON (cycle 1/10)
[10:30:53] Screen OFF (cycle 1/10)  
[10:30:54] Screen ON (cycle 2/10)
[10:30:55] Screen OFF (cycle 2/10)
...
[10:31:08] Screen ON (cycle 10/10)
[10:31:09] Screen OFF (cycle 10/10)
[10:31:10] Screen on/off cycle completed

📊 Real-time Current Changes:
Time    │ Screen │ ai0(Core) │ ai1(Mem) │ ai2(GPU)
────────┼────────┼───────────┼──────────┼─────────
10:30:52│   ON   │  0.245A   │ 0.156A   │ 0.189A
10:30:53│   OFF  │  0.152A   │ 0.089A   │ 0.034A  
10:30:54│   ON   │  0.241A   │ 0.154A   │ 0.185A
10:30:55│   OFF  │  0.151A   │ 0.088A   │ 0.033A
...

📱 Device Screen Changes:
┌─────────────────┐    ┌─────────────────┐
│  🌟 SCREEN ON   │ ←→ │  ⚫ SCREEN OFF  │
│                 │    │                 │  
│  Bright Home    │    │   Black Screen  │
└─────────────────┘    └─────────────────┘
     (0.24A)              (0.15A)
```

---

## ✅ **Test Completion (100%)**

### **Final State**
```
⏱️  Total Duration: ~63 seconds
📊 Progress: 100%
📝 Status: "Test completed successfully"

📱 Final UI State:
├── startAutoTest_PB: enabled (can test again)
├── stopAutoTest_PB: disabled
├── testProgress_PB: 100%
├── testStatus_LB: "Test completed successfully"
├── autoTestGroupBox: "Auto Test - COMPLETED"
└── Status bar: "Auto Test Completed Successfully"

📋 Final Log:
[10:31:13] Test completed with 21 data points
[10:31:13] ✅ Screen On/Off scenario executed successfully
```

### **Completion Dialog**
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

## 📊 **Expected Result Data**

### **Power Consumption Pattern**
```
Screen ON:  VDD_CORE: 0.24A, VDD_MEM: 0.15A, VDD_GPU: 0.18A
Screen OFF: VDD_CORE: 0.15A, VDD_MEM: 0.09A, VDD_GPU: 0.03A

Power Savings: ~38% (when screen OFF)
```

This is the overall expected flow when the "Screen On/Off" scenario is executed! 🚀