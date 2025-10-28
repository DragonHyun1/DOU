# Test Scenario Guide

## 🎯 Overview
A comprehensive test scenario system has been implemented. Systematic test automation is possible using the "Screen on/off" scenario as an example.

## 🔧 System Configuration

### Control Targets (3 types)
1. **Test Device (ADB)**: Android device control
2. **HVPM**: Power supply and voltage control  
3. **DAQ**: Multi-channel current measurement

## 📋 "Screen On/Off" Scenario Details

### 🚀 Test Sequence

#### 1️⃣ **Initialization**
```
- Test Device: 4V power ON state
- HVPM: Initialize to 4V setting
- DAQ: Prepare enabled channels in Multi-channel monitor
```

#### 2️⃣ **Test Start**
1. **HVPM 4V Setting**
   - Set test voltage to 4V
   - Wait for voltage stabilization

2. **Device Initialization**
   - Flight mode ON
   - Recent App initialization  
   - Lockscreen unlock setting

3. **Home Screen Entry**
   - Home key input with LCD ON
   - Confirm Home screen entry

#### 3️⃣ **Stabilization Wait**
- **Wait Time**: 20 seconds
- **Purpose**: HVPM current stabilization
- **Reason**: Stabilize current spike phenomenon during app execution

#### 4️⃣ **DAQ Monitoring Start**
- **Measurement Interval**: 1 second (1Hz)
- **Measurement Target**: Real-time current of all enabled channels
- **Data Collection**: Automatic recording from start point

#### 5️⃣ **Screen On/Off Test Execution**
```
Start: LCD ON
Repeat: LCD ON/OFF at 2-second intervals 
Duration: 20 seconds of measurement
Pattern: ON(1sec) → OFF(1sec) → ON(1sec) → OFF(1sec) ...
```

#### 6️⃣ **Data Collection Complete**
- **Stop DAQ Monitoring**
- **Collected Data**: Current measurement values for each rail
- **Data Format**: Timestamp + current values by channel

#### 7️⃣ **Result Save (Excel Export)**
- **Filename**: `screen_onoff_test_YYYYMMDD_HHMMSS.xlsx`
- **Sheet1**: Test_Data (measurement data)
- **Sheet2**: Test_Summary (test summary)

## 📊 Data Structure

### Test_Data Sheet
| Column | Description | Example |
|--------|-------------|---------|
| timestamp | Measurement time | 2025-10-27 10:30:15 |
| time_elapsed | Elapsed time(sec) | 15.5 |
| ai0_current | Channel0 current(A) | 0.125 |
| ai1_current | Channel1 current(A) | 0.089 |
| ... | Additional channels | ... |

### Test_Summary Sheet
- Test name, start/end time
- Test duration, status
- Number of data points
- Average current by channel

## 🎮 Usage Instructions

### 1️⃣ **Preparation**
1. **Multi-Channel Monitor Setup**
   - Open Tools → Multi-Channel Monitor
   - Enable channels to measure
   - Set Rail names for each channel

2. **Device Connection Check**
   - ADB device connection
   - HVPM connection
   - NI DAQ connection

### 2️⃣ **Test Execution**
1. **Scenario Selection**
   - Select "Screen On/Off" in Auto Test section

2. **Test Start**
   - Click "Start Auto Test" button
   - Select "Yes" in confirmation dialog

3. **Progress Monitoring**
   - Check progress with Progress Bar
   - Monitor real-time status in Log window

### 3️⃣ **Result Verification**
1. **Automatic Save**
   - Excel file automatically generated upon test completion
   - File location: Execution folder

2. **Manual Export**
   - Select "Save detailed results" after test completion
   - Save to desired location

## ⚙️ Advanced Settings

### Scenario Customization
```python
# Modifiable in services/test_scenario_engine.py
screen_onoff_config = TestConfig(
    name="Screen On/Off",
    hvpm_voltage=4.0,           # HVPM voltage
    stabilization_time=20.0,    # Stabilization time
    monitoring_interval=1.0,    # Measurement interval
    test_duration=20.0          # Test duration
)
```

### Creating Additional Scenarios
1. Create `TestConfig` object
2. Define `TestStep` list
3. Register in `_register_builtin_scenarios()`

## 🚨 Precautions

### Hardware Requirements
- **NI DAQ**: Multi-channel measurement support
- **Android Device**: ADB debugging enabled
- **HVPM**: Voltage control capability

### Test Environment
- **Stable Power**: Essential for measurement accuracy
- **Device Fixation**: Prevent physical movement during test
- **Background Apps**: Minimize for measurement impact

## 📈 Expandability

### Additional Scenario Examples
1. **CPU Stress Test**: CPU load testing
2. **WiFi On/Off**: Wireless communication power test  
3. **Camera Test**: Camera operation power measurement
4. **Gaming Test**: Game execution power profile

### Data Analysis
- **Power Profile Analysis**: Time-based power consumption patterns
- **Efficiency Measurement**: Power efficiency comparison by function
- **Battery Life Prediction**: Usage pattern-based prediction

---
*Test Scenario System v1.0 - 2025.10.27*