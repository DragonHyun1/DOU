# HVPM Monitor with Multi-Channel DAQ

A comprehensive power measurement and automated testing tool that combines HVPM (High Voltage Power Monitor) control with multi-channel DAQ monitoring and Android device automation via ADB.

## 🚀 Features

### Core Functionality
- **HVPM Control**: Voltage setting and real-time voltage/current monitoring
- **Multi-Channel DAQ**: 12-channel simultaneous power rail monitoring
- **ADB Integration**: Android device control for automated testing
- **Real-time Monitoring**: Live voltage/current graphs with 10Hz update rate
- **Automated Testing**: Built-in test scenarios for power consumption analysis

### Advanced Features
- **Test Scenario Engine**: Automated test execution with progress tracking
- **Excel Export**: Automatic data export to Excel with detailed analysis
- **Responsive UI**: Adaptive interface that works on various screen sizes
- **Multi-Channel Monitor**: Dedicated interface for power rail management
- **Real-time Logging**: Color-coded system logs with timestamps

## 📋 System Requirements

### Hardware
- **HVPM Device**: Monsoon HVPM or compatible power monitor
- **NI DAQ**: National Instruments DAQ device (USB-6289 or similar)
- **Android Device**: USB debugging enabled
- **PC**: Windows 10/11, Linux, or macOS

### Software
- **Python**: 3.8 or higher
- **NI-DAQmx Runtime**: For DAQ functionality
- **ADB**: Android Debug Bridge (included with Android SDK)

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd hvpm-monitor
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install NI-DAQmx Runtime
Download and install NI-DAQmx Runtime from National Instruments website.

### 4. Setup ADB
Ensure ADB is installed and accessible from command line.

## 🎮 Usage

### Quick Start
1. **Connect Devices**
   - Connect HVPM via USB
   - Connect NI DAQ via USB
   - Connect Android device with USB debugging enabled

2. **Launch Application**
   ```bash
   python main.py
   ```

3. **Device Setup**
   - Click "Refresh" to detect devices
   - Verify all connections in the status indicators

4. **Basic Monitoring**
   - Set target voltage in HVPM section
   - Click "Start Monitor" for real-time monitoring
   - View live graphs and measurements

### Multi-Channel Monitoring
1. Open **Tools → Multi-Channel Monitor**
2. Configure power rails (names, target voltages, shunt resistors)
3. Enable desired channels
4. Start monitoring for real-time power rail analysis

### Automated Testing
1. Select test scenario from dropdown
2. Configure test parameters if needed
3. Click "Start Auto Test"
4. Monitor progress and view results
5. Results automatically saved to Excel

## 📊 Test Scenarios

### Built-in Scenarios
- **Screen On/Off Test**: Display power consumption analysis
- **CPU Stress Test**: High-load power measurement
- **Custom Scenarios**: User-defined test sequences

### Test Process
1. **Initialization**: Device setup and voltage stabilization
2. **Stabilization**: Wait period for stable measurements
3. **Test Execution**: Automated device control and data collection
4. **Data Export**: Automatic Excel report generation

## 🔧 Configuration

### Voltage Settings
- **Stabilization Voltage**: 4.8V (default) - for device stability
- **Test Voltage**: 4.0V (default) - for actual testing
- **Voltage Range**: 0V - 5.5V (safety limited)

### Multi-Channel Setup
- **Channels**: ai0 - ai11 (12 channels)
- **Shunt Resistors**: Configurable per channel
- **Sampling Rate**: 1Hz - 10Hz adjustable
- **Data Format**: Timestamp + voltage/current per channel

## 📁 Project Structure

```
hvpm-monitor/
├── main.py                     # Main application entry point
├── requirements.txt            # Python dependencies
├── services/                   # Core service modules
│   ├── hvpm.py                # HVPM device control
│   ├── ni_daq.py              # NI DAQ interface
│   ├── adb.py                 # Android device control
│   ├── auto_test.py           # Automated testing engine
│   ├── test_scenario_engine.py # Test scenario management
│   └── theme.py               # UI theme system
├── ui/                        # UI definition files
│   ├── main_ui.ui            # Main window layout
│   └── multi_channel_monitor.py # Multi-channel interface
├── generated/                 # Generated UI code
└── docs/                      # Documentation files
```

## 🔍 Troubleshooting

### Connection Issues
- **HVPM Not Detected**: Check USB connection and drivers
- **DAQ Not Found**: Verify NI-DAQmx Runtime installation
- **ADB Device Missing**: Enable USB debugging and authorize computer

### Measurement Issues
- **NaN Values**: Check device connections and sampling settings
- **Unstable Readings**: Increase stabilization time or check power supply
- **High Current Readings**: Verify shunt resistor values and connections

### Test Execution Issues
- **Test Won't Start**: Ensure all devices are connected and detected
- **Test Interruption**: Check system logs for error messages
- **Data Export Fails**: Verify write permissions in output directory

## 📈 Data Analysis

### Export Formats
- **CSV**: Raw measurement data (Time, Voltage, Current)
- **Excel**: Formatted reports with analysis and charts
- **Real-time**: Live data streaming during tests

### Analysis Features
- **Power Profiles**: Time-based power consumption patterns
- **Statistical Analysis**: Min/max/average calculations per channel
- **Comparative Analysis**: Before/after test comparisons

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Install development dependencies
4. Make changes with proper testing
5. Submit pull request

### Code Style
- Follow PEP 8 Python style guide
- Add docstrings to all functions
- Include type hints where appropriate
- Write unit tests for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues, questions, or feature requests:
1. Check the troubleshooting section
2. Review system logs for error details
3. Create an issue with detailed information
4. Include system specifications and error messages

## 🔄 Version History

- **v3.2**: Multi-channel DAQ integration, automated testing
- **v3.1**: Responsive UI, enhanced logging
- **v3.0**: Complete UI redesign, test scenarios
- **v2.x**: Basic HVPM monitoring and control
- **v1.x**: Initial implementation

---

**HVPM Monitor** - Professional power measurement and automated testing solution for Android device development and power analysis.