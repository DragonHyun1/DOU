# NI USB-6289 DAQ Service for Current Monitoring
import time
from typing import Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import os
import sys
# NOTE: ctypes imports removed (no longer using C API)

# NI-DAQmx 런타임 경로 추가 시도
possible_paths = [
    # Windows 표준 경로
    r"C:\Program Files (x86)\National Instruments\Shared\ExternalCompilerSupport\C\lib64\msvc",
    r"C:\Program Files\National Instruments\Shared\ExternalCompilerSupport\C\lib64\msvc", 
    r"C:\Windows\System32",
    r"C:\Program Files (x86)\National Instruments\RT\NIDAQmx\bin",
    r"C:\Program Files\National Instruments\RT\NIDAQmx\bin",
    r"C:\Program Files (x86)\National Instruments\Shared\CVI\Bin",
    r"C:\Program Files\National Instruments\Shared\CVI\Bin",
    
    # 로컬 NIDAQ 런타임 폴더들
    "./NIDAQ1610Runtime",
    "../NIDAQ1610Runtime", 
    "../../NIDAQ1610Runtime",
    "./NIDAQ1610Runtime/bin",
    "../NIDAQ1610Runtime/bin",
    "../../NIDAQ1610Runtime/bin",
    
    # 상대 경로들
    os.path.join(os.getcwd(), "NIDAQ1610Runtime"),
    os.path.join(os.path.dirname(os.getcwd()), "NIDAQ1610Runtime"),
    os.path.join(os.getcwd(), "NIDAQ1610Runtime", "bin"),
    os.path.join(os.path.dirname(os.getcwd()), "NIDAQ1610Runtime", "bin"),
]

# 사용자 정의 NIDAQ 경로 확인
custom_nidaq_path = os.environ.get('NIDAQ_RUNTIME_PATH')
if custom_nidaq_path:
    possible_paths.insert(0, custom_nidaq_path)
    possible_paths.insert(0, os.path.join(custom_nidaq_path, 'bin'))
    print(f"Using custom NIDAQ path: {custom_nidaq_path}")

# 환경 변수에 경로 추가
found_paths = []
for path in possible_paths:
    if os.path.exists(path):
        print(f"Found NI path: {path}")
        found_paths.append(path)
        if path not in os.environ.get('PATH', ''):
            os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')

if found_paths:
    print(f"Added {len(found_paths)} NI paths to environment")
else:
    print("No NI-DAQmx paths found")

# NOTE: C API (nicaiu.dll) support has been removed for code simplification
# Only Python nidaqmx library is used throughout the codebase
# This provides better maintainability and easier debugging

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType
    NI_AVAILABLE = True
    
    # Get version info
    ni_version = getattr(nidaqmx, '__version__', 'unknown')
    print(f"NI-DAQmx Python package imported successfully")
    print(f"  - Package version: {ni_version}")
    
    # Try to get system info early to verify runtime
    try:
        system = nidaqmx.system.System.local()
        runtime_version = system.driver_version
        print(f"  - Runtime version: {runtime_version}")
        print(f"  - Python package and runtime loaded successfully")
    except Exception as e:
        print(f"  - WARNING: Runtime access failed: {e}")
        print(f"  - This may indicate driver version mismatch")
        
except ImportError as e:
    NI_AVAILABLE = False
    print(f"NI-DAQmx import failed: {e}")
    print("Install with: pip install nidaqmx")
except Exception as e:
    NI_AVAILABLE = False
    print(f"NI-DAQmx import error: {e}")
    print("This may indicate NI-DAQmx runtime is not properly installed")

# NI-DAQmx C API Constants (from nidaqmx.h)
DAQmx_Val_Volts = 10348
DAQmx_Val_Amps = 10342
DAQmx_Val_RSE = 10083  # Referenced Single-Ended
DAQmx_Val_NRSE = 10078  # Non-Referenced Single-Ended
DAQmx_Val_Diff = 10106  # Differential
DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_Rising = 10280
DAQmx_Val_Falling = 10171
DAQmx_Val_OnboardClock = None  # Default, typically 0 or empty string
DAQmx_Val_GroupByChannel = 0
DAQmx_Val_GroupByScanNumber = 1

# NOTE: NICAIUWrapper (C API) has been removed
# All DAQ operations now use Python nidaqmx library exclusively

class NIDAQService(QObject):
    """Service for NI DAQ multi-channel voltage/current monitoring"""
    
    # Signals
    channel_data_updated = pyqtSignal(dict)  # {channel: {'voltage': V, 'current': A}}
    connection_changed = pyqtSignal(bool)  # connected status
    error_occurred = pyqtSignal(str)  # error message
    current_updated = pyqtSignal(float)  # current value for single channel monitoring
    
    def __init__(self):
        super().__init__()
        
        # Connection state
        self.connected = False
        self.device_name = None
        self.channel = None  # Initialize channel attribute
        self.task = None
        self.voltage_range = 10.0  # Default ±10V range
        self.last_current = 0.0  # Initialize last_current attribute
        
        # Current scaling parameters
        self.current_scale = 1.0  # Default scale factor
        self.current_offset = 0.0  # Default offset
        
        # Multi-channel configuration
        self.active_channels = {}  # {channel: config}
        self.channel_configs = {}  # {channel: {'name': str, 'target_v': float, 'shunt_r': float, 'enabled': bool}}
        
        # Monitoring state
        self.monitoring = False
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._read_all_channels)
        self.monitor_interval = 500  # 0.5 second default
        
        # Last readings
        self.last_readings = {}  # {channel: {'voltage': V, 'current': A}}
        
        # Default configuration for 12 channels
        self._init_default_channels()
    
    def _init_default_channels(self):
        """Initialize default channel configurations
        
        Channel mapping (based on actual hardware configuration):
        - ai0: VBAT (4.0V, 0.01Ω shunt)
        - ai1: VDD_1P8_AP (1.8V, 0.1Ω shunt)
        - ai2: VDD_MLDO_2P0 (2.0V, 0.005Ω shunt)
        - ai3: VDD_WIFI_1P0 (1.0V, 0.005Ω shunt)
        - ai4: VDD_1P2_AP_WIFI (1.2V, 0.1Ω shunt)
        - ai5: VDD_1P35_WIFIPMU (1.35V, 0.01Ω shunt)
        """
        default_rails = [
            # Phone App Test channels (ai0-ai5)
            {'name': 'VBAT', 'target_v': 4.00, 'shunt_r': 0.010},              # ai0
            {'name': 'VDD_1P8_AP', 'target_v': 1.80, 'shunt_r': 0.100},        # ai1
            {'name': 'VDD_MLDO_2P0', 'target_v': 2.00, 'shunt_r': 0.005},      # ai2
            {'name': 'VDD_WIFI_1P0', 'target_v': 1.00, 'shunt_r': 0.005},      # ai3
            {'name': 'VDD_1P2_AP_WIFI', 'target_v': 1.20, 'shunt_r': 0.100},   # ai4
            {'name': 'VDD_1P35_WIFIPMU', 'target_v': 1.35, 'shunt_r': 0.010},  # ai5
            # Additional channels (ai6-ai11) - placeholder values
            {'name': 'Reserved_6', 'target_v': 1.00, 'shunt_r': 0.010},        # ai6
            {'name': 'Reserved_7', 'target_v': 1.50, 'shunt_r': 0.020},        # ai7
            {'name': 'Reserved_8', 'target_v': 2.80, 'shunt_r': 0.010},        # ai8
            {'name': 'Reserved_9', 'target_v': 3.00, 'shunt_r': 0.015},        # ai9
            {'name': 'Reserved_10', 'target_v': 1.35, 'shunt_r': 0.005},       # ai10
            {'name': 'Reserved_11', 'target_v': 2.10, 'shunt_r': 0.010}        # ai11
        ]
        
        for i, rail in enumerate(default_rails):
            channel = f"ai{i}"
            self.channel_configs[channel] = {
                'name': rail['name'],
                'target_v': rail['target_v'],
                'shunt_r': rail['shunt_r'],
                'enabled': False,  # Default disabled
                'voltage_range': 10.0  # ±10V
            }
            self.last_readings[channel] = {'voltage': 0.0, 'current': 0.0}
    
    def set_channel_config(self, channel: str, name: str, target_v: float, shunt_r: float, enabled: bool):
        """Set configuration for a specific channel"""
        if channel not in self.channel_configs:
            self.channel_configs[channel] = {}
            self.last_readings[channel] = {'voltage': 0.0, 'current': 0.0}
        
        self.channel_configs[channel].update({
            'name': name,
            'target_v': target_v,
            'shunt_r': shunt_r,
            'enabled': enabled
        })
        
        print(f"Channel {channel} configured: {name} ({target_v}V, {shunt_r}Ω, {'enabled' if enabled else 'disabled'})")
    
    def get_channel_config(self, channel: str) -> dict:
        """Get configuration for a specific channel"""
        return self.channel_configs.get(channel, {})
    
    def get_all_channel_configs(self) -> dict:
        """Get all channel configurations"""
        return self.channel_configs.copy()
    
    def set_monitoring_interval(self, interval_ms: int):
        """Set monitoring interval (500ms for normal, 1000ms for auto test)"""
        self.monitor_interval = interval_ms
        if self.monitoring:
            self.monitor_timer.setInterval(interval_ms)
        print(f"Monitoring interval set to {interval_ms}ms")
    
    def _read_all_channels(self):
        """Read all enabled channels"""
        if not self.connected or not self.task:
            return
        
        try:
            enabled_channels = [ch for ch, config in self.channel_configs.items() if config.get('enabled', False)]
            
            if not enabled_channels:
                return
            
            # Read all enabled channels at once
            readings = {}
            
            for channel in enabled_channels:
                try:
                    # Create temporary task for single channel read
                    with nidaqmx.Task() as temp_task:
                        channel_name = f"{self.device_name}/{channel}"
                        config = self.channel_configs[channel]
                        
                        # Use VOLTAGE measurement mode to measure shunt voltage drop
                        # Use DEFAULT terminal config to follow hardware jumper settings (DIFFERENTIAL)
                        # This should match the hardware-timed collection method
                        try:
                            temp_task.ai_channels.add_ai_voltage_chan(
                                channel_name,
                                terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
                                min_val=-0.2,  # ±200mV range (for shunt voltage drop)
                                max_val=0.2,
                                units=nidaqmx.constants.VoltageUnits.VOLTS
                            )
                        except:
                            # Fallback to RSE if DEFAULT fails
                            print(f"⚠️ DEFAULT mode failed for {channel}, using RSE fallback")
                            temp_task.ai_channels.add_ai_voltage_chan(
                                channel_name,
                                terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                                min_val=-5.0,  # ±5V range
                                max_val=5.0,
                                units=nidaqmx.constants.VoltageUnits.VOLTS
                            )
                        
                        # Read voltage across shunt resistor
                        voltage = temp_task.read()
                        
                        # Calculate current using Ohm's law: I = V / R
                        # voltage = shunt voltage drop (typically 0.001V ~ 0.1V)
                        # shunt_r = shunt resistance (typically 0.01Ω)
                        shunt_r = config.get('shunt_r', 0.010)
                        current = voltage / shunt_r if shunt_r > 0 else 0.0
                        
                        # Debug logging - ALWAYS print to see actual voltage values
                        print(f"🔍 {channel}: RAW_VOLTAGE={voltage:.9f}V ({voltage*1000:.6f}mV) → CURRENT={current:.9f}A ({current*1000:.6f}mA)")
                        print(f"   Calculation: {voltage:.9f}V / {shunt_r}Ω = {current:.9f}A")
                        
                        # Warning if voltage seems too high (should be < 100mV for shunt)
                        if voltage > 0.1:
                            print(f"⚠️ WARNING: {channel} voltage ({voltage:.3f}V) seems too high for shunt measurement!")
                            print(f"   Expected: < 0.1V, Got: {voltage:.3f}V")
                            print(f"   Check if channel is connected to shunt terminals (not rail voltage)")
                        
                        readings[channel] = {
                            'voltage': voltage,
                            'current': current,
                            'name': config.get('name', channel),
                            'target_v': config.get('target_v', 0.0)
                        }
                        
                        self.last_readings[channel] = {'voltage': voltage, 'current': current}
                        
                except Exception as e:
                    print(f"Error reading channel {channel}: {e}")
                    readings[channel] = {
                        'voltage': 0.0,
                        'current': 0.0,
                        'name': self.channel_configs[channel].get('name', channel),
                        'target_v': self.channel_configs[channel].get('target_v', 0.0),
                        'error': str(e)
                    }
            
            if readings:
                self.channel_data_updated.emit(readings)
                
        except Exception as e:
            self.error_occurred.emit(f"Multi-channel read error: {e}")
    
    def read_single_shot(self) -> dict:
        """Read all enabled channels once"""
        if not self.connected:
            return {}
        
        self._read_all_channels()
        return self.last_readings.copy()
        
    def get_available_devices(self) -> List[str]:
        """Get list of available NI DAQ devices - ALWAYS return devices"""
        print("=== NI-DAQmx Device Detection (FORCED) ===")
        
        # Only use detected devices - no hardcoded entries
        detected_devices = []
        
        # STEP 2: Try to detect real devices if NI-DAQmx is available
        if NI_AVAILABLE:
            print("NI-DAQmx is available, attempting detection...")
            try:
                from nidaqmx.system import System
                sysobj = System.local()
                print(f"System created successfully")
                print(f"NI-DAQmx System version: {sysobj.driver_version}")
                
                # Try direct device access
                try:
                    device_count = len(list(sysobj.devices))
                    print(f"System reports {device_count} devices")
                    
                    if device_count > 0:
                        for i, dev in enumerate(sysobj.devices):
                            try:
                                device_name = dev.name
                                product_type = getattr(dev, 'product_type', 'Unknown')
                                print(f"Real device {i}: {device_name} ({product_type})")
                                
                                detected_devices.append(f"{device_name} (Real - {product_type})")
                                
                            except Exception as e:
                                print(f"Error processing real device {i}: {e}")
                                detected_devices.append(f"Device{i} (Real - Error)")
                    else:
                        print("No real devices found by system")
                        
                except Exception as e:
                    print(f"Error accessing devices: {e}")
                    
            except Exception as e:
                print(f"Error creating NI system: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("NI-DAQmx not available")
        
        # STEP 3: Combine all devices
        print(f"\n=== FINAL DEVICE LIST ===")
        print(f"Total devices: {len(detected_devices)}")
        for i, device in enumerate(detected_devices):
            print(f"  {i+1}. {device}")
        
        # Return only detected devices (empty list if none found)
        return detected_devices
    
    def connect_device(self, device_name: str, channel: str = "ai0") -> bool:
        """Connect to NI DAQ device"""
        if not NI_AVAILABLE:
            self.error_occurred.emit("NI-DAQmx not installed")
            return False
        
        try:
            print("=== NI DAQ Connection Attempt ===")
            
            # Disconnect if already connected
            self.disconnect_device()
            
            # Extract device name from formatted string (remove parentheses info)
            clean_device_name = device_name.split(' (')[0] if ' (' in device_name else device_name
            
            print(f"Original device string: '{device_name}'")
            print(f"Clean device name: '{clean_device_name}'")
            print(f"Channel: '{channel}'")
            
            # Verify device exists in system before creating task
            try:
                system = nidaqmx.system.System.local()
                device_names = list(system.devices.device_names)
                print(f"Available devices in system: {device_names}")
                
                if clean_device_name not in device_names:
                    print(f"ERROR: Device '{clean_device_name}' not found in system")
                    print(f"Available devices: {device_names}")
                    self.error_occurred.emit(f"Device '{clean_device_name}' not found in NI-DAQmx system")
                    return False
                
                # Get device object to verify it's accessible
                device_obj = system.devices[clean_device_name]
                print(f"Device object created successfully: {device_obj}")
                print(f"Device product type: {device_obj.product_type}")
                
            except Exception as e:
                print(f"ERROR: Cannot access device '{clean_device_name}': {e}")
                self.error_occurred.emit(f"Cannot access device: {e}")
                return False
            
            # Create task
            print("Creating NI-DAQmx task...")
            self.task = nidaqmx.Task()
            channel_name = f"{clean_device_name}/{channel}"
            
            print(f"Creating analog input channel: {channel_name}")
            print(f"Voltage range: ±{self.voltage_range}V")
            
            # Add analog input channel (matching NI I/O Trace configuration)
            self.task.ai_channels.add_ai_voltage_chan(
                channel_name,
                terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                min_val=-5.0,  # Use ±5V as shown in trace for better accuracy
                max_val=5.0,
                units=nidaqmx.constants.VoltageUnits.VOLTS
            )
            
            print("Channel created successfully, performing test read...")
            
            # Test connection by reading once
            test_value = self.task.read()
            print(f"Test read successful: {test_value}V")
            
            self.device_name = clean_device_name
            self.channel = channel
            self.connected = True
            self.connection_changed.emit(True)
            
            print(f"SUCCESS: NI DAQ connected: {clean_device_name}/{channel}")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {e}")
            self.disconnect_device()
            return False
    
    def disconnect_device(self):
        """Disconnect from NI DAQ device"""
        try:
            self.stop_monitoring()
            
            if self.task:
                self.task.close()
                self.task = None
            
            self.device_name = None
            self.connected = False
            self.connection_changed.emit(False)
            
        except Exception as e:
            self.error_occurred.emit(f"Disconnect error: {e}")
    
    def perform_self_calibration(self, device_name: str) -> bool:
        """Perform device self-calibration (based on NI I/O Trace)"""
        if not NI_AVAILABLE:
            return False
            
        try:
            print(f"=== Starting Self-Calibration for {device_name} ===")
            start_time = time.time()
            
            # Perform self-calibration using NI-DAQmx
            import nidaqmx.system
            device = nidaqmx.system.Device(device_name)
            device.self_cal()
            
            duration = time.time() - start_time
            print(f"Self-calibration completed in {duration:.1f} seconds")
            return True
            
        except Exception as e:
            print(f"Self-calibration failed: {e}")
            return False
    
    def read_current_channels_direct(self, channels: List[str], samples_per_channel: int = 12) -> Optional[dict]:
        """Read current directly using DAQ current measurement capability (like other tool)
        
        This uses DAQ's built-in current measurement instead of voltage-based calculation.
        Similar to other tool's current mode measurement.
        
        Uses Python nidaqmx package (original method).
        """
        if not self.connected:
            return None
        
        # Use Python nidaqmx package (original method)
        if not NI_AVAILABLE:
            return None
            
        try:
            with nidaqmx.Task() as task:
                print(f"=== Creating CURRENT measurement task for channels: {channels} ===")
                
                # Add current input channels instead of voltage channels
                for channel in channels:
                    channel_name = f"{self.device_name}/{channel}"
                    print(f"Adding CURRENT channel: {channel_name}")
                    
                    # Get shunt resistor value from channel config
                    config = self.channel_configs.get(channel, {})
                    shunt_r = config.get('shunt_r', 0.01)
                    
                    # Use DIFFERENTIAL measurement for highest accuracy (removes noise and ground loops)
                    # External precision shunt resistor for accurate current measurement
                    try:
                        task.ai_channels.add_ai_current_chan(
                            channel_name,
                            terminal_config=nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL,  # DIFFERENTIAL (most accurate)
                            min_val=-0.1,  # ±100mA range
                            max_val=0.1,
                            units=nidaqmx.constants.CurrentUnits.AMPS,
                            shunt_resistor_loc=nidaqmx.constants.CurrentShuntResistorLocation.EXTERNAL,  # External precision shunt
                            ext_shunt_resist_val=shunt_r  # Precise shunt resistor value (critical for accuracy)
                        )
                        print(f"  ✅ Channel {channel}: DIFFERENTIAL mode, External shunt {shunt_r}Ω")
                    except (TypeError, AttributeError) as e:
                        print(f"  ⚠️ Differential + External shunt config failed: {e}")
                        print(f"  → Trying RSE mode as fallback...")
                        try:
                            # Fallback: RSE mode with external shunt
                            task.ai_channels.add_ai_current_chan(
                                channel_name,
                                terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,  # Fallback to RSE
                                min_val=-0.1,
                                max_val=0.1,
                                units=nidaqmx.constants.CurrentUnits.AMPS,
                                shunt_resistor_loc=nidaqmx.constants.CurrentShuntResistorLocation.EXTERNAL,
                                ext_shunt_resist_val=shunt_r
                            )
                            print(f"  ✅ Channel {channel}: RSE mode (fallback), External shunt {shunt_r}Ω")
                        except (TypeError, AttributeError) as e2:
                            print(f"  ⚠️ RSE + External shunt also failed: {e2}")
                            print(f"  → Using minimal configuration...")
                            # Last fallback: minimal config
                            task.ai_channels.add_ai_current_chan(
                                channel_name,
                                min_val=-0.040,  # Safe range within hardware limit
                                max_val=0.040,
                                units=nidaqmx.constants.CurrentUnits.AMPS
                            )
                            print(f"  ⚠️ Channel {channel}: Minimal config (no shunt spec)")
                
                # Configure timing for accurate DC measurement:
                # - FINITE mode: Collect exact number of samples then stop
                # - Sampling rate: 1kHz ~ 10kHz for oversampling
                # - Samples per channel: 100~1000 samples (will be averaged)
                sampling_rate = 10000.0  # 10kHz for oversampling (adjustable: 1000-10000 Hz)
                # Ensure samples_per_channel is in recommended range (100-1000)
                samples_to_collect = max(100, min(samples_per_channel, 1000))
                
                print(f"Configuring sample clock for accurate DC measurement...")
                print(f"  → Mode: FINITE (collect exact {samples_to_collect} samples then stop)")
                print(f"  → Rate: {sampling_rate} Hz (oversampling for noise reduction)")
                print(f"  → Samples per channel: {samples_to_collect} (will be averaged)")
                print(f"  → Strategy: Finite mode, oversample at {sampling_rate}Hz, average {samples_to_collect} samples")
                
                task.timing.cfg_samp_clk_timing(
                    rate=sampling_rate,  # 10kHz oversampling
                    sample_mode=nidaqmx.constants.AcquisitionType.FINITE,  # FINITE mode
                    samps_per_chan=samples_to_collect,  # Exact number of samples (100-1000)
                    active_edge=nidaqmx.constants.Edge.RISING
                )
                
                print(f"Starting CURRENT measurement task...")
                task.start()
                
                # Read multiple samples using ReadMultiSample (NOT ReadSingleSample)
                # FINITE mode: Collect exact number of samples, then average for accurate DC value
                print(f"Reading {samples_to_collect} samples per channel using ReadMultiSample (FINITE mode)...")
                print(f"  → Will average all {samples_to_collect} samples for accurate DC measurement")
                
                # Calculate timeout based on sampling rate
                # Timeout: samples/rate + buffer (e.g., 1000 samples at 10kHz = 0.1s + 1s buffer = 1.1s)
                estimated_time = (samples_to_collect / sampling_rate) + 1.0  # Add 1s buffer
                timeout = max(2.0, min(estimated_time, 10.0))  # Min 2s, Max 10s
                
                # ReadMultiSample: Read exact number of samples (FINITE mode), then average
                data = task.read(number_of_samples_per_channel=samples_to_collect, timeout=timeout)
                
                task.stop()
                
                print(f"Raw current data: {type(data)}, length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
                
                # Process current measurement data with averaging (critical for accuracy)
                # Average all samples to get accurate DC value (removes noise statistically)
                result = {}
                
                if len(channels) == 1:
                    # Single channel current measurement
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        samples = list(data)
                        num_samples = len(samples)
                        
                        # Convert to mA
                        current_data_ma = [val * 1000.0 for val in samples]
                        
                        # Calculate average (arithmetic mean) - accurate DC value
                        avg_current_ma = sum(current_data_ma) / num_samples
                        
                        # Calculate statistics
                        if num_samples > 1:
                            variance = sum((x - avg_current_ma) ** 2 for x in current_data_ma) / num_samples
                            std_dev_ma = variance ** 0.5
                        else:
                            std_dev_ma = 0.0
                        
                        config = self.channel_configs.get(channels[0], {})
                        shunt_r = config.get('shunt_r', 0.01)
                        
                        print(f"Channel {channels[0]} ({config.get('name', channels[0])}):")
                        print(f"  → Samples: {num_samples}")
                        print(f"  → Average: {avg_current_ma:.3f}mA (DC value)")
                        print(f"  → Std Dev: {std_dev_ma:.3f}mA (noise level)")
                        print(f"  → Shunt: {shunt_r}Ω (precision shunt resistor)")
                        
                        result[channels[0]] = {
                            'current_data': current_data_ma,  # All samples in mA
                            'avg_current': avg_current_ma / 1000.0,  # Average in Amps (accurate DC)
                            'std_dev': std_dev_ma / 1000.0,  # Standard deviation in Amps
                            'voltage': 0.0,
                            'sample_count': num_samples,
                            'name': config.get('name', channels[0]),
                            'shunt_resistor': shunt_r
                        }
                else:
                    # Multiple channel current measurement
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        for i, channel in enumerate(channels):
                            if i < len(data):
                                channel_data = data[i] if isinstance(data[i], (list, tuple)) else [data[i]]
                                if len(channel_data) > 0:
                                    samples = list(channel_data)
                                    num_samples = len(samples)
                                    
                                    # Convert to mA
                                    current_data_ma = [val * 1000.0 for val in samples]
                                    
                                    # Calculate average (arithmetic mean)
                                    avg_current_ma = sum(current_data_ma) / num_samples
                                    
                                    # Calculate statistics
                                    if num_samples > 1:
                                        variance = sum((x - avg_current_ma) ** 2 for x in current_data_ma) / num_samples
                                        std_dev_ma = variance ** 0.5
                                    else:
                                        std_dev_ma = 0.0
                                    
                                    config = self.channel_configs.get(channel, {})
                                    shunt_r = config.get('shunt_r', 0.01)
                                    
                                    print(f"Channel {channel} ({config.get('name', channel)}):")
                                    print(f"  → Samples: {num_samples}")
                                    print(f"  → Average: {avg_current_ma:.3f}mA (DC value)")
                                    print(f"  → Std Dev: {std_dev_ma:.3f}mA (noise level)")
                                    print(f"  → Shunt: {shunt_r}Ω (precision shunt resistor)")
                                    
                                    result[channel] = {
                                        'current_data': current_data_ma,  # All samples in mA
                                        'avg_current': avg_current_ma / 1000.0,  # Average in Amps (accurate DC)
                                        'std_dev': std_dev_ma / 1000.0,  # Standard deviation in Amps
                                        'voltage': 0.0,
                                        'sample_count': num_samples,
                                        'name': config.get('name', channel),
                                        'shunt_resistor': shunt_r
                                    }
                
                print(f"=== Current measurement completed, returning {len(result)} channel results ===")
                return result
                
        except Exception as e:
            error_msg = f"Current measurement error: {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    # NOTE: _read_current_channels_nicaiu() (C API) has been removed
    # All DAQ operations now use Python nidaqmx library exclusively
    
    def read_current_via_differential_measurement(self, voltage_channels: List[str], samples_per_channel: int = 12) -> Optional[dict]:
        """Read current using differential measurement across shunt resistors
        
        For proper current measurement, we need to measure voltage difference
        across shunt resistor, not the rail voltage.
        
        Example setup:
        - ai0: Voltage before shunt resistor (rail voltage)
        - ai1: Voltage after shunt resistor (rail voltage - shunt drop)
        - Current = (ai0 - ai1) / shunt_resistance
        """
        if not NI_AVAILABLE or not self.connected:
            return None
            
        try:
            with nidaqmx.Task() as task:
                print(f"=== Creating differential measurement task for channels: {voltage_channels} ===")
                
                # Add channels for differential measurement
                for channel in voltage_channels:
                    channel_name = f"{self.device_name}/{channel}"
                    print(f"Adding channel: {channel_name}")
                    task.ai_channels.add_ai_voltage_chan(
                        channel_name,
                        terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                        min_val=-5.0,
                        max_val=5.0,
                        units=nidaqmx.constants.VoltageUnits.VOLTS
                    )
                
                # Configure timing for differential measurement
                task.timing.cfg_samp_clk_timing(
                    rate=30000.0,
                    sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
                    samps_per_chan=samples_per_channel
                )
                
                print(f"Starting differential measurement task...")
                task.start()
                
                print(f"Reading {samples_per_channel} samples per channel for differential calculation...")
                data = task.read(number_of_samples_per_channel=samples_per_channel, timeout=1.0)
                
                task.stop()
                
                print(f"Raw differential data: {type(data)}, length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
                
                # Process differential measurement for current calculation
                result = {}
                
                if len(voltage_channels) >= 2:
                    # Differential measurement between two channels
                    if isinstance(data, (list, tuple)) and len(data) >= 2:
                        channel1_data = data[0] if isinstance(data[0], (list, tuple)) else [data[0]]
                        channel2_data = data[1] if isinstance(data[1], (list, tuple)) else [data[1]]
                        
                        if len(channel1_data) > 0 and len(channel2_data) > 0:
                            # Calculate voltage difference (shunt voltage drop)
                            voltage_diffs = []
                            min_len = min(len(channel1_data), len(channel2_data))
                            
                            for i in range(min_len):
                                voltage_diff = channel1_data[i] - channel2_data[i]
                                voltage_diffs.append(voltage_diff)
                            
                            avg_voltage_diff = sum(voltage_diffs) / len(voltage_diffs)
                            avg_rail_voltage = sum(channel1_data) / len(channel1_data)
                            
                            print(f"Differential measurement:")
                            print(f"  Rail voltage (ai0): {avg_rail_voltage:.6f}V")
                            print(f"  Voltage difference (ai0-ai1): {avg_voltage_diff:.6f}V")
                            
                            # Store both rail voltage and shunt voltage drop
                            result[voltage_channels[0]] = {
                                'voltage_data': channel1_data,
                                'avg_voltage': avg_rail_voltage,  # Rail voltage
                                'shunt_voltage_drop': avg_voltage_diff,  # Voltage drop across shunt
                                'sample_count': len(channel1_data)
                            }
                            
                            result[voltage_channels[1]] = {
                                'voltage_data': channel2_data,
                                'avg_voltage': sum(channel2_data) / len(channel2_data),
                                'shunt_voltage_drop': avg_voltage_diff,  # Same shunt drop
                                'sample_count': len(channel2_data)
                            }
                else:
                    # Single channel - assume it's measuring shunt voltage drop directly
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        channel_data = data if isinstance(data[0], (int, float)) else data[0]
                        avg_voltage = sum(channel_data) / len(channel_data)
                        
                        print(f"Single channel measurement (assuming shunt voltage): {avg_voltage:.6f}V")
                        
                        result[voltage_channels[0]] = {
                            'voltage_data': channel_data,
                            'avg_voltage': avg_voltage,  # This should be rail voltage
                            'shunt_voltage_drop': avg_voltage,  # Assuming this IS the shunt voltage
                            'sample_count': len(channel_data)
                        }
                
                print(f"=== Differential measurement completed, returning {len(result)} channel results ===")
                return result
                
        except Exception as e:
            error_msg = f"Differential measurement error: {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def _compress_data(self, data: List[float], compress_ratio: int) -> List[float]:
        """Compress data by averaging groups (noise reduction)
        
        Args:
            data: Raw data values
            compress_ratio: How many samples to average (e.g., 30)
            
        Returns:
            Compressed data (averaged, same units as input)
            
        Example:
            Input: 300,000 samples
            Ratio: 30
            Output: 10,000 samples (each is average of 30)
        """
        compressed = []
        
        for i in range(0, len(data), compress_ratio):
            # Get group of samples (e.g., 30 samples)
            group = data[i:i+compress_ratio]
            
            if len(group) > 0:
                # Average the group
                avg_value = sum(group) / len(group)
                compressed.append(avg_value)
        
        return compressed
    
    def read_current_channels_hardware_timed(self, channels: List[str], sample_rate: float = 100000.0, compress_ratio: int = 100, duration_seconds: float = 10.0, voltage_range: float = 0.1) -> Optional[dict]:
        """Read current using DAQ hardware timing with compression
        
        Uses NI-DAQmx API to read voltage drop across external shunt resistor.
        Samples at high rate (30kHz) then compresses by averaging for noise reduction.
        
        Args:
            channels: List of channel names (e.g., ['ai0', 'ai1'])
            sample_rate: Sampling rate in Hz (default: 100000.0 = 100kHz)
            compress_ratio: Compression ratio (default: 100, meaning 100:1 compression)
            duration_seconds: Duration of data collection (default: 10.0 seconds)
            
        Returns:
            dict: {channel: {'current_data': [mA], 'sample_count': int}}
            
        Example:
            - Sampling: 100kHz = 100,000 samples/sec
            - Duration: 10 seconds
            - Raw samples: 1,000,000 (1M)
            - Compress: 100:1 (average 100 samples)
            - Final samples: 10,000 (one per ms)
        """
        if not NI_AVAILABLE or not self.connected:
            print("DAQ not available or not connected")
            return None
            
        try:
            # Calculate total samples to collect
            total_samples = int(sample_rate * duration_seconds)  # 100,000 * 10 = 1,000,000
            compressed_samples = total_samples // compress_ratio  # 1,000,000 / 100 = 10,000
            
            print(f"=== Hardware-Timed VOLTAGE Collection (with Compression) ===")
            print(f"Channels: {channels}")
            print(f"Voltage range: ±{voltage_range}V")
            print(f"Sampling rate: {sample_rate} Hz ({sample_rate/1000:.0f}kHz)")
            print(f"Duration: {duration_seconds} seconds")
            print(f"Raw samples: {total_samples} ({total_samples/1000:.0f}k)")
            print(f"Compress ratio: {compress_ratio}:1 (avg {compress_ratio} samples → 1 per ms)")
            print(f"Final samples: {compressed_samples} (after compression)")
            print(f"Mode: VOLTAGE measurement (external shunt)")
            print(f"Acquisition Type: CONTINUOUS (matches Manual tool)")
            
            with nidaqmx.Task() as task:
                # Add VOLTAGE input channels (to measure external shunt voltage drop)
                for channel in channels:
                    channel_name = f"{self.device_name}/{channel}"
                    config = self.channel_configs.get(channel, {})
                    
                    print(f"Adding VOLTAGE channel: {channel_name} ({config.get('name', channel)})")
                    
                    # Use voltage measurement with DIFFERENTIAL configuration
                    # to measure voltage drop across external shunt resistor
                    # 
                    # Voltage range configuration:
                    # - Narrow range (±0.1V = ±100mV) provides better ADC resolution for small shunt drops
                    # - Typical shunt drops: 0.01mV ~ 100mV
                    # - If DIFFERENTIAL fails with narrow range, fallback modes will be attempted
                    terminal_mode_used = "UNKNOWN"
                    try:
                        # Try DIFFERENTIAL first with current voltage range
                        # Narrow range (±0.1V) improves measurement precision for shunt voltage drops
                        #
                        # Try multiple ways to specify DIFFERENTIAL mode (library version compatibility)
                        differential_success = False
                        diff_error = None
                        
                        # Method 1: Try TerminalConfiguration.DIFF (most compatible)
                        try:
                            print(f"  → Trying DIFFERENTIAL mode (method 1: TerminalConfiguration.DIFF)...")
                            task.ai_channels.add_ai_voltage_chan(
                                channel_name,
                                terminal_config=nidaqmx.constants.TerminalConfiguration.DIFF,
                                min_val=-voltage_range,
                                max_val=voltage_range,
                                units=nidaqmx.constants.VoltageUnits.VOLTS
                            )
                            terminal_mode_used = "DIFFERENTIAL"
                            differential_success = True
                            print(f"  ✅ DIFFERENTIAL mode enabled (method 1)")
                        except (AttributeError, Exception) as e1:
                            diff_error = e1
                            print(f"     Method 1 failed: {type(e1).__name__}: {str(e1)}")
                            
                            # Method 2: Try TerminalConfiguration.DIFFERENTIAL (alternative spelling)
                            try:
                                print(f"  → Trying DIFFERENTIAL mode (method 2: TerminalConfiguration.DIFFERENTIAL)...")
                                task.ai_channels.add_ai_voltage_chan(
                                    channel_name,
                                    terminal_config=nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL,
                                    min_val=-voltage_range,
                                    max_val=voltage_range,
                                    units=nidaqmx.constants.VoltageUnits.VOLTS
                                )
                                terminal_mode_used = "DIFFERENTIAL"
                                differential_success = True
                                print(f"  ✅ DIFFERENTIAL mode enabled (method 2)")
                            except (AttributeError, Exception) as e2:
                                print(f"     Method 2 failed: {type(e2).__name__}: {str(e2)}")
                                diff_error = e2
                        
                        if not differential_success:
                            # All DIFFERENTIAL methods failed, try DEFAULT (follows hardware jumper settings)
                            # Note: DEFAULT often works as DIFFERENTIAL if hardware is configured that way
                            print(f"  ⚠️ All DIFFERENTIAL methods failed")
                            print(f"     Last error: {type(diff_error).__name__}: {str(diff_error)}")
                            try:
                                print(f"  → Trying DEFAULT mode (hardware jumpers)...")
                                task.ai_channels.add_ai_voltage_chan(
                                    channel_name,
                                    terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
                                    min_val=-voltage_range,
                                    max_val=voltage_range,
                                    units=nidaqmx.constants.VoltageUnits.VOLTS
                                )
                                terminal_mode_used = "DEFAULT"
                                print(f"  ✅ DEFAULT mode enabled (±5V range)")
                            except Exception as default_error:
                                # Try NRSE as fallback
                                print(f"  ⚠️ DEFAULT failed: {type(default_error).__name__}: {str(default_error)}")
                                try:
                                    print(f"  → Trying NRSE mode...")
                                    task.ai_channels.add_ai_voltage_chan(
                                        channel_name,
                                        terminal_config=nidaqmx.constants.TerminalConfiguration.NRSE,
                                        min_val=-voltage_range,
                                        max_val=voltage_range,
                                        units=nidaqmx.constants.VoltageUnits.VOLTS
                                    )
                                    terminal_mode_used = "NRSE"
                                    print(f"  ⚠️ NRSE mode enabled (may not measure differential correctly)")
                                except:
                                    # Last resort: RSE mode (will measure rail voltage!)
                                    print(f"  ⚠️ NRSE also failed, using RSE as last resort")
                                    print(f"  🚨 WARNING: RSE mode measures Rail Voltage, NOT shunt drop!")
                                    print(f"  🚨 This will cause ~100,000x error in current measurement!")
                                    task.ai_channels.add_ai_voltage_chan(
                                        channel_name,
                                        terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                                        min_val=-10.0,  # ±10V range for rail voltage
                                        max_val=10.0,
                                        units=nidaqmx.constants.VoltageUnits.VOLTS
                                    )
                                    terminal_mode_used = "RSE"
                    except Exception as e:
                        print(f"❌ Error adding voltage channel {channel}: {e}")
                        raise
                    
                    # Store terminal mode for validation
                    config['terminal_mode'] = terminal_mode_used
                    print(f"  📌 Channel {channel} configured with {terminal_mode_used} mode")
                
                # Configure hardware timing - CONTINUOUS mode (like Manual tool)
                # IMPORTANT: Manual tool uses CONTINUOUS mode, not FINITE
                # This ensures consistent timing and data collection behavior
                task.timing.cfg_samp_clk_timing(
                    rate=sample_rate,  # 100kHz sampling rate
                    sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,  # CONTINUOUS mode (matches Manual tool)
                    samps_per_chan=total_samples  # Buffer size
                )
                
                print(f"Starting hardware-timed VOLTAGE acquisition ({sample_rate/1000:.0f}kHz, CONTINUOUS mode)...")
                task.start()
                
                # Read samples (CONTINUOUS mode - reads from circular buffer)
                timeout = duration_seconds + 5.0  # Add buffer
                print(f"Reading {total_samples} raw samples per channel...")
                data = task.read(number_of_samples_per_channel=total_samples, timeout=timeout)
                
                task.stop()
                print(f"Hardware VOLTAGE acquisition completed, starting compression...")
                
                # Process and compress voltage data, then convert to current
                result = {}
                
                if len(channels) == 1:
                    # Single channel
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        voltage_data_volts = list(data)
                        print(f"Raw voltage samples collected: {len(voltage_data_volts)}")
                        
                        # Compress voltage data by averaging (30:1 ratio)
                        compressed_volts = self._compress_data(voltage_data_volts, compress_ratio)
                        
                        # Convert voltage to current using Ohm's law: I = V / R
                        config = self.channel_configs.get(channels[0], {})
                        shunt_r = config.get('shunt_r', 0.01)  # Default 0.01Ω
                        terminal_mode = config.get('terminal_mode', 'UNKNOWN')
                        target_v = config.get('target_v', 0.0)
                        
                        # Calculate average voltage for validation
                        avg_v_volts = sum(compressed_volts) / len(compressed_volts) if compressed_volts else 0
                        avg_v_mv = avg_v_volts * 1000
                        
                        # VALIDATION: Check if measuring rail voltage instead of shunt drop
                        # Expected shunt drop: 0.01mV ~ 100mV (typically < 10mV for most cases)
                        # Rail voltage: 1V ~ 5V (1000mV ~ 5000mV)
                        is_rail_voltage = False
                        if abs(avg_v_volts) > 0.5:  # > 500mV is suspicious for shunt drop
                            is_rail_voltage = True
                            print(f"")
                            print(f"  🚨 CRITICAL WARNING for {channels[0]} 🚨")
                            print(f"  🚨 Measured voltage ({avg_v_mv:.1f}mV) is too high for shunt drop!")
                            print(f"  🚨 Expected shunt drop: < 100mV")
                            print(f"  🚨 Measured value: {avg_v_mv:.1f}mV (likely measuring Rail Voltage!)")
                            print(f"  🚨 Rail voltage for this channel: ~{target_v*1000:.0f}mV")
                            print(f"  🚨 Terminal mode: {terminal_mode}")
                            if terminal_mode == "RSE":
                                print(f"  🚨 RSE mode measures rail voltage, not shunt drop!")
                                print(f"  🚨 Hardware must be connected in DIFFERENTIAL mode")
                            print(f"  🚨 Current calculation will be INCORRECT!")
                            print(f"")
                        
                        # WARNING: Calibration factors are DISABLED
                        # Reason: Only validated for Phone App scenario (1~6mA range)
                        # Different scenarios (Idle, WiFi Heavy, etc.) may have different current ranges
                        # If error is non-linear, same calibration factor won't work for all scenarios
                        # TODO: Find root cause (likely incorrect shunt resistor values or measurement mode issue)
                        
                        # Calibration factors (DISABLED - for reference only)
                        # These were determined from Phone App scenario only:
                        # 'ai0': 0.237, 'ai1': 0.507, 'ai2': 0.431, 
                        # 'ai3': 0.156, 'ai4': 0.415, 'ai5': 0.015
                        
                        # Use ENABLE_CALIBRATION = True to enable (not recommended without validation)
                        ENABLE_CALIBRATION = False
                        
                        if ENABLE_CALIBRATION:
                            CALIBRATION_FACTORS = {
                                'ai0': 0.237, 'ai1': 0.507, 'ai2': 0.431,
                                'ai3': 0.156, 'ai4': 0.415, 'ai5': 0.015,
                            }
                            calibration_factor = CALIBRATION_FACTORS.get(channels[0], 1.0)
                            print(f"  ⚙️ Calibration factor: {calibration_factor:.3f} (Phone App scenario only!)")
                        else:
                            calibration_factor = 1.0
                        
                        compressed_ma = [(v / shunt_r) * 1000 * calibration_factor for v in compressed_volts]
                        avg_i_ma = sum(compressed_ma) / len(compressed_ma) if compressed_ma else 0
                        
                        # Additional validation: Check if current is unreasonably high
                        if abs(avg_i_ma) > 10000:  # > 10A (10,000mA)
                            print(f"  🚨 WARNING: Current {avg_i_ma:.1f}mA is unreasonably high!")
                            print(f"  🚨 This confirms measurement error (likely rail voltage)")
                        
                        result[channels[0]] = {
                            'current_data': compressed_ma,  # Current in mA (compressed)
                            'sample_count': len(compressed_ma),
                            'name': config.get('name', channels[0]),
                            'validation': {
                                'is_rail_voltage': is_rail_voltage,
                                'terminal_mode': terminal_mode,
                                'avg_voltage_mv': avg_v_mv,
                                'expected_shunt_drop_mv': '< 100mV'
                            }
                        }
                        
                        print(f"Channel {channels[0]}: {len(compressed_ma)} compressed samples")
                        print(f"  Avg voltage: {avg_v_mv:.3f}mV, Avg current: {avg_i_ma:.3f}mA (shunt={shunt_r}Ω)")
                        print(f"  Terminal mode: {terminal_mode}, Validation: {'❌ FAILED' if is_rail_voltage else '✅ PASSED'}")
                else:
                    # Multiple channels
                    if isinstance(data, (list, tuple)) and len(data) == len(channels):
                        for i, channel in enumerate(channels):
                            channel_data = data[i] if isinstance(data[i], (list, tuple)) else [data[i]]
                            voltage_data_volts = list(channel_data)
                            print(f"Channel {channel}: {len(voltage_data_volts)} raw voltage samples")
                            
                            # Compress voltage data by averaging (30:1 ratio)
                            compressed_volts = self._compress_data(voltage_data_volts, compress_ratio)
                            
                            # Convert voltage to current using Ohm's law: I = V / R
                            config = self.channel_configs.get(channel, {})
                            shunt_r = config.get('shunt_r', 0.01)  # Default 0.01Ω
                            terminal_mode = config.get('terminal_mode', 'UNKNOWN')
                            target_v = config.get('target_v', 0.0)
                            
                            # Calculate average voltage for validation
                            avg_v_volts = sum(compressed_volts) / len(compressed_volts) if compressed_volts else 0
                            avg_v_mv = avg_v_volts * 1000
                            
                            # VALIDATION: Check if measuring rail voltage instead of shunt drop
                            is_rail_voltage = False
                            if abs(avg_v_volts) > 0.5:  # > 500mV is suspicious for shunt drop
                                is_rail_voltage = True
                                print(f"")
                                print(f"  🚨 CRITICAL WARNING for {channel} 🚨")
                                print(f"  🚨 Measured voltage ({avg_v_mv:.1f}mV) is too high for shunt drop!")
                                print(f"  🚨 Expected shunt drop: < 100mV")
                                print(f"  🚨 Measured value: {avg_v_mv:.1f}mV (likely measuring Rail Voltage!)")
                                print(f"  🚨 Rail voltage for this channel: ~{target_v*1000:.0f}mV")
                                print(f"  🚨 Terminal mode: {terminal_mode}")
                                if terminal_mode == "RSE":
                                    print(f"  🚨 RSE mode measures rail voltage, not shunt drop!")
                                    print(f"  🚨 Hardware must be connected in DIFFERENTIAL mode")
                                print(f"  🚨 Current calculation will be INCORRECT!")
                                print(f"")
                            
                            # WARNING: Calibration factors are DISABLED (see above for details)
                            ENABLE_CALIBRATION = False
                            
                            if ENABLE_CALIBRATION:
                                CALIBRATION_FACTORS = {
                                    'ai0': 0.237, 'ai1': 0.507, 'ai2': 0.431,
                                    'ai3': 0.156, 'ai4': 0.415, 'ai5': 0.015,
                                }
                                calibration_factor = CALIBRATION_FACTORS.get(channel, 1.0)
                                print(f"  ⚙️ Calibration: {calibration_factor:.3f} (Phone App only!)")
                            else:
                                calibration_factor = 1.0
                            
                            compressed_ma = [(v / shunt_r) * 1000 * calibration_factor for v in compressed_volts]
                            avg_i_ma = sum(compressed_ma) / len(compressed_ma) if compressed_ma else 0
                            
                            # Additional validation: Check if current is unreasonably high
                            if abs(avg_i_ma) > 10000:  # > 10A (10,000mA)
                                print(f"  🚨 WARNING: Current {avg_i_ma:.1f}mA is unreasonably high!")
                                print(f"  🚨 This confirms measurement error (likely rail voltage)")
                            
                            result[channel] = {
                                'current_data': compressed_ma,  # Current in mA (compressed)
                                'sample_count': len(compressed_ma),
                                'name': config.get('name', channel),
                                'validation': {
                                    'is_rail_voltage': is_rail_voltage,
                                    'terminal_mode': terminal_mode,
                                    'avg_voltage_mv': avg_v_mv,
                                    'expected_shunt_drop_mv': '< 100mV'
                                }
                            }
                            
                            print(f"Channel {channel}: {len(compressed_ma)} compressed samples")
                            print(f"  Avg voltage: {avg_v_mv:.3f}mV, Avg current: {avg_i_ma:.3f}mA (shunt={shunt_r}Ω)")
                            print(f"  Terminal mode: {terminal_mode}, Validation: {'❌ FAILED' if is_rail_voltage else '✅ PASSED'}")
                
                print(f"=== Hardware-timed VOLTAGE collection completed: {len(result)} channels ===")
                return result
                
        except Exception as e:
            error_msg = f"Hardware-timed collection error: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)
            return None
    
    def read_voltage_channels_trace_based(self, channels: List[str], samples_per_channel: int = 12) -> Optional[dict]:
        """Read multiple voltage channels simultaneously (matching other tool's NI I/O Trace)"""
        if not NI_AVAILABLE or not self.connected:
            return None
            
        try:
            with nidaqmx.Task() as task:
                print(f"=== Creating task for channels: {channels} ===")
                
                # Add multiple channels as shown in other tool's trace
                for channel in channels:
                    channel_name = f"{self.device_name}/{channel}"
                    print(f"Adding channel: {channel_name}")
                    task.ai_channels.add_ai_voltage_chan(
                        channel_name,
                        terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                        min_val=-5.0,
                        max_val=5.0,
                        units=nidaqmx.constants.VoltageUnits.VOLTS
                    )
                
                # Configure timing like other tool (continuous sampling)
                task.timing.cfg_samp_clk_timing(
                    rate=30000.0,  # Higher rate like other tool (30kHz vs 500Hz)
                    sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,  # Continuous instead of Finite
                    samps_per_chan=samples_per_channel
                )
                
                print(f"Starting task with {len(channels)} channels...")
                task.start()
                
                # Read data like DAQReadNChanNSamp1DWfm (small chunks continuously)
                print(f"Reading {samples_per_channel} samples per channel...")
                data = task.read(number_of_samples_per_channel=samples_per_channel, timeout=1.0)
                
                print(f"Stopping task...")
                task.stop()
                
                print(f"Raw data received: {type(data)}, length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
                
                # Process data for each channel
                result = {}
                if len(channels) == 1:
                    # Single channel
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        avg_voltage = sum(data) / len(data)
                        print(f"Single channel {channels[0]}: {len(data)} samples, avg: {avg_voltage:.6f}V")
                        result[channels[0]] = {
                            'voltage_data': data,
                            'avg_voltage': avg_voltage,
                            'sample_count': len(data)
                        }
                    else:
                        print(f"No valid data for single channel {channels[0]}")
                        result[channels[0]] = {'voltage_data': [], 'avg_voltage': 0.0, 'sample_count': 0}
                else:
                    # Multiple channels
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        for i, channel in enumerate(channels):
                            if i < len(data):
                                channel_data = data[i] if isinstance(data[i], (list, tuple)) else [data[i]]
                                if len(channel_data) > 0:
                                    avg_voltage = sum(channel_data) / len(channel_data)
                                    print(f"Channel {channel}: {len(channel_data)} samples, avg: {avg_voltage:.6f}V")
                                    result[channel] = {
                                        'voltage_data': channel_data,
                                        'avg_voltage': avg_voltage,
                                        'sample_count': len(channel_data)
                                    }
                                else:
                                    print(f"No data for channel {channel}")
                                    result[channel] = {'voltage_data': [], 'avg_voltage': 0.0, 'sample_count': 0}
                    else:
                        print(f"No valid multi-channel data received")
                        for channel in channels:
                            result[channel] = {'voltage_data': [], 'avg_voltage': 0.0, 'sample_count': 0}
                
                print(f"=== Read completed, returning {len(result)} channel results ===")
                return result
                
        except Exception as e:
            error_msg = f"Multi-channel read error: {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
    def read_current_once(self) -> Optional[float]:
        """Read current value once"""
        if not self.connected or not self.task:
            return None
        
        try:
            voltage = self.task.read()
            current = (voltage * self.current_scale) + self.current_offset
            self.last_current = current
            self.current_updated.emit(current)
            return current
            
        except Exception as e:
            self.error_occurred.emit(f"Read error: {e}")
            return None
    
    def start_monitoring(self, interval_ms: int = 1000):
        """Start continuous current monitoring"""
        if not self.connected:
            self.error_occurred.emit("Device not connected")
            return False
        
        self.monitor_interval = interval_ms
        self.monitor_timer.setInterval(interval_ms)
        self.monitor_timer.start()
        self.monitoring = True
        return True
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitor_timer.stop()
        self.monitoring = False
    
    def _read_current(self):
        """Internal method for timer-based current reading"""
        self.read_current_once()
    
    def set_scaling(self, scale: float, offset: float = 0.0):
        """Set current scaling parameters"""
        self.current_scale = scale
        self.current_offset = offset
    
    def set_voltage_range(self, voltage_range: float):
        """Set voltage input range"""
        self.voltage_range = voltage_range
        
        # Reconnect if already connected to apply new range
        if self.connected and self.device_name:
            device = self.device_name
            channel = self.channel
            self.disconnect_device()
            self.connect_device(device, channel)
    
    def is_connected(self) -> bool:
        """Check if device is connected"""
        return self.connected
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active"""
        return self.monitoring
    
    def get_last_current(self) -> float:
        """Get last current reading"""
        return self.last_current
    
    def get_device_info(self) -> dict:
        """Get current device information"""
        return {
            'connected': self.connected,
            'device_name': self.device_name,
            'channel': self.channel,
            'monitoring': self.monitoring,
            'last_current': self.last_current,
            'voltage_range': self.voltage_range,
            'current_scale': self.current_scale,
            'current_offset': self.current_offset
        }

# Mock service for when NI-DAQmx is not available
class MockNIDAQService(NIDAQService):
    """Mock NI DAQ service for testing without hardware"""
    
    def __init__(self):
        super().__init__()
        self.mock_current = 0.0
        
    def get_available_devices(self) -> List[str]:
        # NI-DAQmx 없을 때 테스트용 Mock 장비 표시
        print("=== Using Mock NI DAQ Service (GUARANTEED) ===")
        print("No real NI-DAQmx hardware/software available")
        print("Returning comprehensive mock devices for testing...")
        
        mock_devices = [
            "Dev1 (Mock USB-6289)",
            "Dev2 (Mock USB-6008)", 
            "Dev3 (Mock USB-6001)",
            "Dev4 (Mock PXI-6289)",
            "Dev5 (Mock USB-6211)"
        ]
        
        print(f"Mock service returning {len(mock_devices)} devices:")
        for i, device in enumerate(mock_devices):
            print(f"  {i+1}. {device}")
            
        return mock_devices
    
    def connect_device(self, device_name: str, channel: str = "ai0") -> bool:
        # Extract clean device name from formatted string
        clean_device_name = device_name.split(' (')[0] if ' (' in device_name else device_name
        
        print(f"Mock: Connecting to {clean_device_name}/{channel}")
        
        self.device_name = clean_device_name
        self.channel = channel
        self.connected = True
        self.connection_changed.emit(True)
        
        print(f"Mock: Connected successfully to {clean_device_name}/{channel}")
        return True
    
    def read_current_once(self) -> Optional[float]:
        if not self.connected:
            return None
        
        # Simulate current reading with some variation
        import random
        self.mock_current = 1.5 + random.uniform(-0.1, 0.1)
        self.last_current = self.mock_current
        self.current_updated.emit(self.mock_current)
        return self.mock_current

def create_ni_service() -> NIDAQService:
    """Factory function to create NI DAQ service"""
    if NI_AVAILABLE:
        return NIDAQService()
    else:
        return MockNIDAQService()