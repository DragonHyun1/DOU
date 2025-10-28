[Current measurement results from other tool]
4209.  DAQReadNChanNSamp1DWfm ("_unnamedTask<1F>", 12 (0xC), 10.000000 (1.000000E+01), 0.000033 (3.330000E-05), {4.7491E-05,8.75428E-05,...}, 0.000033 (3.330000E-05), {-7.26645E-05,7.43914E-06,...}, "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 15:56:27.8469      Call Duration 00:00:00.0000
Status: 0

[Voltage measurement results from other tool]
5019.  DAQReadNChanNSamp1DWfm ("_unnamedTask<20>", 12 (0xC), 10.000000 (1.000000E+01), 0.000033 (3.330000E-05), {1.76457,1.75729,...}, 0.000033 (3.330000E-05), {-0.0407253,-0.0476142,...}, "")
Process ID: 0x00009DA8         Thread ID: 0x00005068
Start Time: 15:58:18.6388      Call Duration 00:00:00.0000
Status: 0




# HVPM Monitor Auto Test Feature Guide

## 🚀 Overview

The HVPM Monitor's automated test feature is a powerful tool that combines device control via ADB and power measurement via HVPM to perform automated testing.

### Key Features
- **Voltage Stabilization**: Voltage setting for device stabilization before test start
- **Automated Scenarios**: Support for various test scenarios
- **Real-time Monitoring**: Real-time voltage/current measurement during tests
- **Progress Tracking**: Visual display of test progress

## 📋 Test Scenarios

### 1. Screen On/Off Test
- **Description**: Measures display-related power consumption by repeatedly turning screen on/off
- **Operation**:
  1. Turn screen on (KEYCODE_WAKEUP)
  2. Wait for specified time (default 10 seconds)
  3. Turn screen off (KEYCODE_POWER)
  4. Wait for specified time (default 5 seconds)
  5. Repeat for specified number of cycles (default 5 times)

### 2. Screen On/Off Long Test
- **Description**: Longer cycle screen on/off test
- **Features**: 10 cycles, 15 seconds ON, 10 seconds OFF

### 3. CPU Stress Test
- **Description**: Measures power consumption under high load by generating CPU stress
- **Operation**:
  1. Start CPU stress process
  2. Maintain for specified time (default 60 seconds)
  3. Terminate stress process

### 4. CPU Stress Long Test
- **Description**: Long-duration CPU stress test (5 minutes)

## ⚙️ Settings and Configuration

### Voltage Settings
1. **Stabilization Voltage**
   - Default: 4.8V
   - Purpose: Provide stable voltage to prevent device shutdown before test start
   - Recommended range: 4.5V - 5.0V

2. **Test Voltage**
   - Default: 4.0V
   - Purpose: Voltage to use during actual test execution
   - Recommended range: 3.0V - 4.5V (adjust according to test purpose)

### Device Connection
1. **HVPM Connection**: HVPM device connection via USB required
2. **ADB Connection**: Android device with USB debugging enabled required

## 🔄 Test Execution Process

### 1. Initialization Phase (0-20%)
- Check connection status
- Set stabilization voltage (4.8V)
- Wait 10 seconds for voltage stabilization

### 2. Test Preparation (20-30%)
- Set test voltage (4.0V)
- Confirm voltage stabilization

### 3. Test Execution (30-100%)
- Execute selected scenario
- Real-time progress updates
- Device control via ADB commands
- Power measurement via HVPM

## 📱 Usage Instructions

### Basic Usage Steps

1. **Device Connection**
   ```
   1. Connect HVPM device via USB
   2. Connect Android device via USB and enable USB debugging
   3. Click "Refresh" button to search for devices
   ```

2. **Test Configuration**
   ```
   1. Select desired test from Test Scenario dropdown
   2. Set Stabilization Voltage (default 4.8V)
   3. Set Test Voltage (default 4.0V)
   ```

3. **Test Execution**
   ```
   1. Click "Start Test" button
   2. Confirm settings in confirmation dialog and click "Yes"
   3. Monitor test progress via Progress Bar and Status
   4. Can stop with "Stop" button if needed
   ```

4. **Result Verification**
   ```
   1. Observe voltage/current changes in real-time graph
   2. Check detailed test logs in System Log
   3. Save measurement data via File > Export Data
   ```

## 🛠️ Advanced Settings

### Adding Custom Test Scenarios

To add new test scenarios, implement by inheriting the `TestScenario` class in `services/auto_test.py`:

```python
class CustomTest(TestScenario):
    def __init__(self):
        super().__init__("Custom Test", "User-defined test")
    
    def execute(self, device: str, log_callback: Callable, progress_callback: Callable = None) -> bool:
        # Implement test logic
        pass
```

### Extending ADB Commands

New ADB command functions can be added to `services/adb.py`:

```python
def custom_command(device: str, parameter: str) -> bool:
    """User-defined ADB command"""
    return execute_command(device, f"custom_shell_command {parameter}")
```

## 📊 Data Analysis

### Interpreting Measurement Data

1. **Voltage Changes**
   - Stabilization phase: Starts at 4.8V and stabilizes
   - Test phase: Changes to 4.0V and proceeds with test
   - Sudden voltage changes indicate device state changes

2. **Current Changes**
   - Screen ON: Current increase (display power consumption)
   - Screen OFF: Current decrease (standby power consumption)
   - CPU stress: Sustained high current consumption

### Data Export

- **Format**: CSV (Time, Voltage, Current)
- **Usage**: Can be analyzed further with Excel, Python pandas, etc.

## ⚠️ Precautions

### Safety Guidelines
1. **Voltage Range**: Be careful not to exceed 5.5V
2. **Device Status**: Check device charge status before testing
3. **Connection Stability**: Verify USB cable connection status

### Troubleshooting

#### Connection Issues
- **HVPM Connection Failure**: Check device driver installation
- **ADB Connection Failure**: Check USB debugging activation and permission allowance

#### Test Execution Issues
- **Test Start Failure**: Check all device connection status
- **Mid-test Interruption**: Check error messages in logs

#### Data Measurement Issues
- **NaN Values**: Check HVPM connection status and sampling settings
- **Unstable Measurements**: Consider increasing voltage stabilization time

## 🔧 Developer Information

### Architecture
```
AutoTestService
├── TestScenario (Abstract class)
│   ├── ScreenOnOffTest
│   ├── CPUStressTest
│   └── [User-defined scenarios]
├── HvpmService (Voltage control)
└── ADB Service (Device control)
```

### Key Classes
- `AutoTestService`: Overall test management
- `TestScenario`: Test scenario base class
- `ScreenOnOffTest`: Screen ON/OFF test implementation
- `CPUStressTest`: CPU stress test implementation

### Signals/Slots
- `progress_updated`: Progress update
- `test_completed`: Test completion
- `voltage_stabilized`: Voltage stabilization complete

## 📈 Performance Optimization

### Recommended Settings
- **Sampling Frequency**: 10Hz (default)
- **Buffer Size**: 600 samples (1 minute of data)
- **Stabilization Time**: 10 seconds (default)

### System Requirements
- **OS**: Windows 10/11, Linux, macOS
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM
- **Storage**: 100MB or more

---

## 📞 Support

If you encounter issues or need additional features:
1. Check System Log
2. Record error messages and reproduction steps
3. Collect device and environment information

We hope you can effectively utilize the HVPM Monitor's automated test features through this guide!