# NI USB-6289 DAQ Service for Current Monitoring
import time
from typing import Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import os
import sys
import ctypes
from ctypes import c_int32, c_double, c_void_p, POINTER, byref, c_uint64

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

# Legacy DAQ API (Traditional DAQ) support using ctypes
LEGACY_DAQ_AVAILABLE = False
nidaq_dll = None

try:
    # Try to load nidaq.dll (Legacy DAQ API)
    nidaq_dll_paths = [
        r"C:\Program Files (x86)\National Instruments\Shared\CVI\Bin\nidaq.dll",
        r"C:\Program Files\National Instruments\Shared\CVI\Bin\nidaq.dll",
        r"C:\Windows\System32\nidaq.dll",
        "nidaq.dll"
    ]
    
    for dll_path in nidaq_dll_paths:
        try:
            if os.path.exists(dll_path):
                nidaq_dll = ctypes.CDLL(dll_path)
                LEGACY_DAQ_AVAILABLE = True
                print(f"Legacy DAQ API (nidaq.dll) loaded from: {dll_path}")
                break
        except Exception as e:
            continue
    
    if not LEGACY_DAQ_AVAILABLE:
        # Try loading from PATH
        try:
            nidaq_dll = ctypes.CDLL("nidaq.dll")
            LEGACY_DAQ_AVAILABLE = True
            print("Legacy DAQ API (nidaq.dll) loaded from system PATH")
        except Exception as e:
            print(f"Legacy DAQ API (nidaq.dll) not available: {e}")
            print("Will use DAQmx API instead")
            
except Exception as e:
    print(f"Failed to load Legacy DAQ API: {e}")
    LEGACY_DAQ_AVAILABLE = False

class LegacyDAQWrapper:
    """Wrapper for Legacy DAQ API (Traditional DAQ) using ctypes"""
    
    def __init__(self, device_name: str = "Dev1"):
        self.device_name = device_name
        self.task_handle = None
        self.dll = nidaq_dll if LEGACY_DAQ_AVAILABLE else None
        
        if self.dll:
            # Define function signatures for Legacy DAQ API
            # DAQCreateTask
            self.dll.DAQCreateTask.argtypes = [ctypes.POINTER(c_int32), ctypes.POINTER(c_int32)]
            self.dll.DAQCreateTask.restype = c_int32
            
            # DAQCreateAIVoltageChan
            self.dll.DAQCreateAIVoltageChan.argtypes = [
                c_int32,  # taskHandle
                ctypes.c_char_p,  # physicalChannel
                ctypes.c_char_p,  # nameToAssignToChannel
                c_int32,  # terminalConfig
                c_double,  # minVal
                c_double,  # maxVal
                c_int32,  # units
                ctypes.c_char_p  # customScaleName
            ]
            self.dll.DAQCreateAIVoltageChan.restype = c_int32
            
            # DAQStartTask
            self.dll.DAQStartTask.argtypes = [c_int32]
            self.dll.DAQStartTask.restype = c_int32
            
            # DAQReadNChanNSamp1DWfm
            self.dll.DAQReadNChanNSamp1DWfm.argtypes = [
                c_int32,  # taskHandle
                c_int32,  # numSampsPerChan
                c_double,  # timeout
                c_int32,  # fillMode
                POINTER(c_double),  # readArray
                c_int32,  # arraySizeInSamps
                POINTER(c_int32),  # sampsPerChanRead
                POINTER(c_int32)  # reserved
            ]
            self.dll.DAQReadNChanNSamp1DWfm.restype = c_int32
            
            # DAQStopTask
            self.dll.DAQStopTask.argtypes = [c_int32]
            self.dll.DAQStopTask.restype = c_int32
            
            # DAQClearTask
            self.dll.DAQClearTask.argtypes = [c_int32]
            self.dll.DAQClearTask.restype = c_int32
            
            # DAQCfgSampClkTiming
            self.dll.DAQCfgSampClkTiming.argtypes = [
                c_int32,  # taskHandle
                ctypes.c_char_p,  # source
                c_double,  # rate
                c_int32,  # activeEdge
                c_int32,  # sampleMode
                ctypes.POINTER(c_uint64)  # sampsPerChan
            ]
            self.dll.DAQCfgSampClkTiming.restype = c_int32
    
    def create_task(self):
        """Create a DAQ task"""
        if not self.dll:
            return False
        task_handle = c_int32()
        error_code = self.dll.DAQCreateTask(ctypes.byref(task_handle), None)
        if error_code == 0:
            self.task_handle = task_handle.value
            return True
        return False
    
    def add_voltage_channel(self, physical_channel: str, min_val: float = -5.0, max_val: float = 5.0):
        """Add voltage channel (matching manual: -5V ~ 5V range)"""
        if not self.dll or not self.task_handle:
            return False
        
        # Terminal config: 10083 = DAQmx_Val_Diff (Differential)
        # Units: 10348 = DAQmx_Val_Volts
        error_code = self.dll.DAQCreateAIVoltageChan(
            c_int32(self.task_handle),
            physical_channel.encode('utf-8'),
            b"",  # nameToAssignToChannel
            c_int32(10083),  # DAQmx_Val_Diff
            c_double(min_val),
            c_double(max_val),
            c_int32(10348),  # DAQmx_Val_Volts
            None  # customScaleName
        )
        return error_code == 0
    
    def configure_timing(self, rate: float = 30000.0, active_edge: int = 10280, sample_mode: int = 10123, samples_per_chan: int = 1000):
        """Configure sampling clock timing
        active_edge: 10280 = DAQmx_Val_Rising
        sample_mode: 10123 = DAQmx_Val_ContSamps (Continuous Samples)
        """
        if not self.dll or not self.task_handle:
            return False
        
        import ctypes
        samps_per_chan = ctypes.c_uint64(samples_per_chan)
        error_code = self.dll.DAQCfgSampClkTiming(
            c_int32(self.task_handle),
            b"",  # source (OnboardClock)
            c_double(rate),
            c_int32(active_edge),  # Rising
            c_int32(sample_mode),  # Continuous Samples
            ctypes.byref(samps_per_chan)
        )
        return error_code == 0
    
    def start_task(self):
        """Start the DAQ task"""
        if not self.dll or not self.task_handle:
            return False
        error_code = self.dll.DAQStartTask(c_int32(self.task_handle))
        return error_code == 0
    
    def read_samples(self, num_samples: int, timeout: float = 10.0):
        """Read samples (matching DAQReadNChanNSamp1DWfm)"""
        if not self.dll or not self.task_handle:
            return None
        
        # Allocate buffer for reading
        read_array = (c_double * num_samples)()
        samps_per_chan_read = c_int32()
        reserved = c_int32()
        
        # Fill mode: 10178 = DAQmx_Val_GroupByChannel
        error_code = self.dll.DAQReadNChanNSamp1DWfm(
            c_int32(self.task_handle),
            c_int32(num_samples),
            c_double(timeout),
            c_int32(10178),  # GroupByChannel
            read_array,
            c_int32(num_samples),
            ctypes.byref(samps_per_chan_read),
            ctypes.byref(reserved)
        )
        
        if error_code == 0:
            return [read_array[i] for i in range(samps_per_chan_read.value)]
        return None
    
    def stop_task(self):
        """Stop the DAQ task"""
        if not self.dll or not self.task_handle:
            return
        self.dll.DAQStopTask(c_int32(self.task_handle))
    
    def clear_task(self):
        """Clear the DAQ task"""
        if not self.dll or not self.task_handle:
            return
        self.dll.DAQClearTask(c_int32(self.task_handle))
        self.task_handle = None

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
        """
        if not NI_AVAILABLE or not self.connected:
            return None
            
        try:
            with nidaqmx.Task() as task:
                print(f"=== Creating CURRENT measurement task for channels: {channels} ===")
                
                # Add current input channels instead of voltage channels
                for channel in channels:
                    channel_name = f"{self.device_name}/{channel}"
                    print(f"Adding CURRENT channel: {channel_name}")
                    
                    # Use current measurement with correct API parameters
                    try:
                        task.ai_channels.add_ai_current_chan(
                            channel_name,
                            terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                            min_val=-0.1,  # ±100mA range
                            max_val=0.1,
                            units=nidaqmx.constants.CurrentUnits.AMPS,
                            shunt_resistor_loc=nidaqmx.constants.CurrentShuntResistorLocation.EXTERNAL,
                            ext_shunt_resist_val=0.010  # 10mΩ shunt
                        )
                    except TypeError as e:
                        print(f"Current channel API error: {e}")
                        print("Trying simplified current channel setup...")
                        # Fallback: try with minimal parameters and safe range
                        task.ai_channels.add_ai_current_chan(
                            channel_name,
                            min_val=-0.040,  # Safe range within hardware limit
                            max_val=0.040,
                            units=nidaqmx.constants.CurrentUnits.AMPS
                        )
                
                # Configure timing for current measurement
                # Match manual measurement settings from NI Trace:
                # - SampClk.Rate = 30000
                # - SampClk.ActiveEdge = Rising
                # - SampClk.Src = "OnboardClock"
                task.timing.cfg_samp_clk_timing(
                    rate=30000.0,
                    sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
                    samps_per_chan=samples_per_channel,
                    active_edge=nidaqmx.constants.Edge.RISING  # Match: SampClk.ActiveEdge = Rising
                )
                # Set clock source to OnboardClock (default, but explicit for matching)
                # Note: OnboardClock is typically the default, but we ensure it matches
                
                print(f"Starting CURRENT measurement task...")
                task.start()
                
                print(f"Reading {samples_per_channel} current samples per channel...")
                # Calculate timeout based on sample count (30kHz rate: samples/30000 + buffer)
                # For 1000 samples: ~33ms + 100ms buffer = ~133ms
                # For 3000 samples: ~100ms + 200ms buffer = ~300ms
                estimated_time = (samples_per_channel / 30000.0) + 0.2  # Add 200ms buffer
                timeout = max(0.5, min(estimated_time, 2.0))  # Min 0.5s, Max 2.0s
                data = task.read(number_of_samples_per_channel=samples_per_channel, timeout=timeout)
                
                task.stop()
                
                print(f"Raw current data: {type(data)}, length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
                
                # Process current measurement data
                result = {}
                
                if len(channels) == 1:
                    # Single channel current measurement
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        avg_current = sum(data) / len(data)
                        print(f"Single channel {channels[0]} current: {avg_current:.6f}A ({avg_current*1000:.3f}mA)")
                        
                        result[channels[0]] = {
                            'current_data': data,
                            'avg_current': avg_current,  # Current in Amps
                            'voltage': 0.0,  # No voltage measurement in current mode
                            'sample_count': len(data)
                        }
                else:
                    # Multiple channel current measurement
                    if isinstance(data, (list, tuple)) and len(data) > 0:
                        for i, channel in enumerate(channels):
                            if i < len(data):
                                channel_data = data[i] if isinstance(data[i], (list, tuple)) else [data[i]]
                                if len(channel_data) > 0:
                                    avg_current = sum(channel_data) / len(channel_data)
                                    print(f"Channel {channel} current: {avg_current:.6f}A ({avg_current*1000:.3f}mA)")
                                    
                                    result[channel] = {
                                        'current_data': channel_data,
                                        'avg_current': avg_current,  # Current in Amps
                                        'voltage': 0.0,  # No voltage in current mode
                                        'sample_count': len(channel_data)
                                    }
                
                print(f"=== Current measurement completed, returning {len(result)} channel results ===")
                return result
                
        except Exception as e:
            error_msg = f"Current measurement error: {e}"
            print(error_msg)
            self.error_occurred.emit(error_msg)
            return None
    
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
            data: Raw data values (list of numbers)
            compress_ratio: How many samples to average (e.g., 30)
            
        Returns:
            Compressed data (averaged, same units as input)
            
        Example:
            Input: 300,000 samples
            Ratio: 30
            Output: 10,000 samples (each is average of 30)
        """
        compressed = []
        
        # Ensure data is a flat list of numbers
        flat_data = []
        for item in data:
            if isinstance(item, (list, tuple)):
                flat_data.extend(item)
            elif isinstance(item, (int, float)):
                flat_data.append(float(item))
            else:
                try:
                    flat_data.append(float(item))
                except (ValueError, TypeError):
                    print(f"Warning: Skipping non-numeric value: {item}")
        
        for i in range(0, len(flat_data), compress_ratio):
            # Get group of samples (e.g., 30 samples)
            group = flat_data[i:i+compress_ratio]
            
            if len(group) > 0:
                # Average the group
                avg_value = sum(group) / len(group)
                compressed.append(avg_value)
        
        return compressed
    
    def read_current_channels_hardware_timed(self, channels: List[str], sample_rate: float = 30000.0, compress_ratio: int = 30, duration_seconds: float = 10.0) -> Optional[dict]:
        """Read current using DAQmx API matching Manual measurement exactly
        
        Matches Manual Trace settings:
        - Continuous Samples mode
        - SampQuant.SampPerChan = 1000 (read exactly 1000 samples)
        - SampClk.Rate = 30000 (30kHz)
        - SampClk.ActiveEdge = Rising
        - Read 60 samples at a time repeatedly (DAQReadNChanNSamp1DWfm style)
        
        Uses NI-DAQmx API to read voltage drop across external shunt resistor.
        Reads exactly 1000 samples per channel (matching manual), then maps to duration.
        
        Args:
            channels: List of channel names (e.g., ['ai0', 'ai1'])
            sample_rate: Sampling rate in Hz (default: 30000.0 = 30kHz)
            compress_ratio: Compression ratio (not used, kept for compatibility)
            duration_seconds: Duration of data collection (default: 10.0 seconds)
            
        Returns:
            dict: {channel: {'current_data': [mA], 'sample_count': int}}
            
        Note:
            Manual Trace shows reading exactly 1000 samples per channel,
            then using those samples for the entire test duration.
        """
        if not NI_AVAILABLE or not self.connected:
            print("DAQ not available or not connected")
            return None
        
        # Use DAQmx API only (Legacy DAQ not available for NI-6289)
        return self._read_current_channels_daqmx(channels, sample_rate, compress_ratio, duration_seconds)
    
    def _read_current_channels_legacy_daq(self, channels: List[str], sample_rate: float = 30000.0, compress_ratio: int = 30, duration_seconds: float = 10.0) -> Optional[dict]:
        """Read current using Legacy DAQ API (Traditional DAQ) - Not used for NI-6289"""
        try:
            # Match manual exactly: 
            # - SampQuant.SampPerChan = 1000
            # - DAQReadNChanNSamp1DWfm: 60 samples repeatedly
            # - Continuous Samples mode
            samples_per_read = 60  # Match manual: 60 samples per read
            samples_per_channel_total = 1000  # Match manual: SampQuant.SampPerChan = 1000
            num_reads_needed = (samples_per_channel_total + samples_per_read - 1) // samples_per_read  # Ceiling division
            
            print(f"=== Using Legacy DAQ API (Traditional DAQ) ===")
            print(f"Channels: {channels}")
            print(f"Sampling rate: {sample_rate} Hz (30kHz)")
            print(f"Samples per channel: {samples_per_channel_total} (match manual: SampQuant.SampPerChan = 1000)")
            print(f"Read size: {samples_per_read} samples per read (match manual: DAQReadNChanNSamp1DWfm)")
            print(f"Number of reads: {num_reads_needed}")
            print(f"Mode: VOLTAGE measurement (-5V~5V range, match manual)")
            
            # Create Legacy DAQ wrapper
            legacy_daq = LegacyDAQWrapper(self.device_name)
            
            if not legacy_daq.create_task():
                print("Failed to create Legacy DAQ task")
                return None
            
            # Add voltage channels (matching manual: -5V ~ 5V range)
            for channel in channels:
                physical_channel = f"{self.device_name}/{channel}"
                if not legacy_daq.add_voltage_channel(physical_channel, min_val=-5.0, max_val=5.0):
                    print(f"Failed to add voltage channel: {physical_channel}")
                    legacy_daq.clear_task()
                    return None
                print(f"Added Legacy DAQ voltage channel: {physical_channel} (-5V~5V range)")
            
            # Configure timing (matching manual: Continuous Samples, Rising edge, 30kHz)
            # active_edge: 10280 = DAQmx_Val_Rising
            # sample_mode: 10123 = DAQmx_Val_ContSamps (Continuous Samples)
            if not legacy_daq.configure_timing(
                rate=sample_rate,
                active_edge=10280,  # Rising
                sample_mode=10123,  # Continuous Samples
                samples_per_chan=samples_per_channel_total
            ):
                print("Failed to configure Legacy DAQ timing")
                legacy_daq.clear_task()
                return None
            
            # Start task
            if not legacy_daq.start_task():
                print("Failed to start Legacy DAQ task")
                legacy_daq.clear_task()
                return None
            
            print(f"Legacy DAQ task started (Continuous Samples, 30kHz, Rising edge)")
            
            # Collect all data from repeated reads (like manual)
            all_channel_data = {ch: [] for ch in channels}
            num_channels = len(channels)
            read_timeout = 10.0  # Match manual: 10.0 seconds timeout
            
            print(f"Reading {samples_per_channel_total} samples per channel in {samples_per_read}-sample chunks...")
            
            # Read repeatedly like manual
            for read_idx in range(num_reads_needed):
                remaining_samples = samples_per_channel_total - len(all_channel_data.get(channels[0], []))
                read_size = min(samples_per_read, remaining_samples)
                
                if read_size <= 0:
                    break
                
                # Read chunk using Legacy DAQ API (matches DAQReadNChanNSamp1DWfm)
                # Note: Legacy DAQ reads all channels at once, returns interleaved data
                total_samples_to_read = read_size * num_channels
                chunk_data = legacy_daq.read_samples(total_samples_to_read, timeout=read_timeout)
                
                if chunk_data is None or len(chunk_data) == 0:
                    print(f"Warning: Failed to read chunk {read_idx + 1}")
                    break
                
                # De-interleave data for multiple channels
                if num_channels > 1:
                    for i, channel in enumerate(channels):
                        channel_chunk = [chunk_data[j] for j in range(i, len(chunk_data), num_channels)]
                        all_channel_data[channel].extend(channel_chunk[:read_size])
                else:
                    all_channel_data[channels[0]].extend(chunk_data[:read_size])
                
                print(f"Read chunk {read_idx + 1}/{num_reads_needed}: {read_size} samples (total: {len(all_channel_data.get(channels[0], []))}/{samples_per_channel_total})")
            
            # Stop and clear task
            legacy_daq.stop_task()
            legacy_daq.clear_task()
            
            print(f"Legacy DAQ acquisition completed")
            
            # Process collected data
            result = {}
            for channel in channels:
                voltage_data_volts = all_channel_data[channel][:samples_per_channel_total]  # Limit to 1000
                print(f"Channel {channel}: {len(voltage_data_volts)} raw voltage samples")
                
                if len(voltage_data_volts) == 0:
                    print(f"Warning: No data collected for channel {channel}")
                    continue
                
                # Convert voltage to current using Ohm's law: I = V / R
                config = self.channel_configs.get(channel, {})
                shunt_r = config.get('shunt_r', 0.01)  # Default 0.01Ω
                current_ma = [(v / shunt_r) * 1000 for v in voltage_data_volts]  # V/R=A, *1000=mA
                
                result[channel] = {
                    'current_data': current_ma,  # Current in mA (1000 samples, match manual)
                    'sample_count': len(current_ma),
                    'name': config.get('name', channel)
                }
                avg_v_mv = sum(voltage_data_volts) * 1000 / len(voltage_data_volts) if voltage_data_volts else 0
                avg_i_ma = sum(current_ma) / len(current_ma) if current_ma else 0
                print(f"Channel {channel}: {len(current_ma)} samples (match manual: 1000 samples)")
                print(f"  Avg voltage: {avg_v_mv:.3f}mV, Avg current: {avg_i_ma:.3f}mA (shunt={shunt_r}Ω)")
            
            print(f"=== Legacy DAQ collection completed: {len(result)} channels ===")
            return result
            
        except Exception as e:
            error_msg = f"Legacy DAQ collection error: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(error_msg)
            return None
    
    def _read_current_channels_daqmx(self, channels: List[str], sample_rate: float = 30000.0, compress_ratio: int = 30, duration_seconds: float = 10.0) -> Optional[dict]:
        """Read current using DAQmx API matching Manual Trace exactly"""
        try:
            # Match manual exactly: 
            # - SampQuant.SampPerChan = 1000
            # - DAQReadNChanNSamp1DWfm: 60 samples repeatedly
            # - Continuous Samples mode
            samples_per_read = 60  # Match manual: 60 samples per read
            samples_per_channel_total = 1000  # Match manual: SampQuant.SampPerChan = 1000
            num_reads_needed = (samples_per_channel_total + samples_per_read - 1) // samples_per_read  # Ceiling division
            
            print(f"=== Using DAQmx API (Matching Manual Trace) ===")
            print(f"Channels: {channels}")
            print(f"Sampling rate: {sample_rate} Hz (30kHz)")
            print(f"Samples per channel: {samples_per_channel_total} (match manual: SampQuant.SampPerChan = 1000)")
            print(f"Read size: {samples_per_read} samples per read (match manual: DAQReadNChanNSamp1DWfm)")
            print(f"Number of reads: {num_reads_needed}")
            print(f"Mode: VOLTAGE measurement (-5V~5V range, match manual)")
            
            # Collect all data from repeated reads (like manual)
            all_channel_data = {ch: [] for ch in channels}
            
            with nidaqmx.Task() as task:
                # Add VOLTAGE input channels (to measure external shunt voltage drop)
                for channel in channels:
                    channel_name = f"{self.device_name}/{channel}"
                    config = self.channel_configs.get(channel, {})
                    
                    print(f"Adding VOLTAGE channel: {channel_name} ({config.get('name', channel)})")
                    
                    # Use voltage measurement with DIFFERENTIAL configuration
                    # to measure voltage drop across external shunt resistor
                    try:
                        # Try DEFAULT first (follow hardware jumper settings, like Traditional DAQ API)
                        try:
                            # Match manual measurement: -5V ~ 5V range (not -0.2V ~ 0.2V)
                            task.ai_channels.add_ai_voltage_chan(
                                channel_name,
                                terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
                                min_val=-5.0,  # Match manual: -5V range
                                max_val=5.0,   # Match manual: +5V range
                                units=nidaqmx.constants.VoltageUnits.VOLTS
                            )
                            print(f"  → DEFAULT mode with -5V~5V range (matching manual)")
                        except Exception as default_error:
                            # Try explicit DIFFERENTIAL
                            print(f"  ⚠️ DEFAULT failed: {type(default_error).__name__}: {str(default_error)}")
                            try:
                                print(f"  → Trying explicit DIFFERENTIAL...")
                                task.ai_channels.add_ai_voltage_chan(
                                    channel_name,
                                    terminal_config=nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL,
                                    min_val=-5.0,  # Match manual: -5V range
                                    max_val=5.0,   # Match manual: +5V range
                                    units=nidaqmx.constants.VoltageUnits.VOLTS
                                )
                                print(f"  → DIFFERENTIAL mode enabled with -5V~5V range")
                            except Exception as diff_error:
                                # Try NRSE (Referenced Single-Ended) as fallback
                                print(f"  ⚠️ DIFFERENTIAL failed: {type(diff_error).__name__}: {str(diff_error)}")
                                try:
                                    print(f"  → Trying NRSE (Referenced Single-Ended)...")
                                    task.ai_channels.add_ai_voltage_chan(
                                        channel_name,
                                        terminal_config=nidaqmx.constants.TerminalConfiguration.NRSE,
                                        min_val=-5.0,  # Match manual: -5V range
                                        max_val=5.0,   # Match manual: +5V range
                                        units=nidaqmx.constants.VoltageUnits.VOLTS
                                    )
                                    print(f"  → NRSE mode enabled with -5V~5V range")
                                except:
                                    # Final fallback to RSE with warning
                                    print(f"  ⚠️ NRSE also failed, falling back to RSE")
                                    print(f"  ⚠️ WARNING: RSE mode will measure Rail voltage, not Shunt drop!")
                                    task.ai_channels.add_ai_voltage_chan(
                                        channel_name,
                                        terminal_config=nidaqmx.constants.TerminalConfiguration.RSE,
                                        min_val=-5.0,  # Match manual: -5V range
                                        max_val=5.0,   # Match manual: +5V range
                                        units=nidaqmx.constants.VoltageUnits.VOLTS
                                    )
                    except Exception as e:
                        print(f"Error adding voltage channel {channel}: {e}")
                        raise
                
                # Configure timing: Match manual exactly
                # Manual: Continuous Samples mode, but SampQuant.SampPerChan = 1000
                # Manual Trace shows: setTimingF64U64AP("", SampQuant.SampPerChan, 1000.0)
                # This sets buffer size or sample limit even in Continuous mode
                num_channels = len(channels)
                total_samples = samples_per_channel_total * num_channels
                
                # Match manual: Set buffer size to handle 1000 samples per channel
                # Manual uses SampPerChan=1000 even in Continuous mode
                task.in_stream.input_buf_size = max(total_samples * 2, 10000)  # At least 2x samples or 10k
                
                # Match manual exactly:
                # - SampQuant.SampMode = Continuous Samples
                # - SampQuant.SampPerChan = 1000
                # - SampClk.Rate = 30000
                # - SampClk.ActiveEdge = Rising
                # - SampClk.Src = "OnboardClock" (default)
                task.timing.cfg_samp_clk_timing(
                    rate=sample_rate,  # 30kHz (SampClk.Rate)
                    sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,  # Continuous Samples (SampQuant.SampMode)
                    samps_per_chan=samples_per_channel_total,  # 1000 (SampQuant.SampPerChan) - sets buffer/limit
                    active_edge=nidaqmx.constants.Edge.RISING  # Rising (SampClk.ActiveEdge)
                )
                
                print(f"Starting CONTINUOUS acquisition (30kHz, Rising edge, match manual)...")
                print(f"Buffer size: {task.in_stream.input_buf_size} samples (to prevent overflow)")
                task.start()
                
                # Read samples exactly like manual: 60 samples repeatedly until we have 1000 per channel
                # Manual: DAQReadNChanNSamp1DWfm with 60 samples, timeout 10.0s
                # Use shorter timeout per chunk to read more frequently and prevent buffer overflow
                read_timeout = 10.0  # Match manual: 10.0 seconds timeout (total)
                chunk_timeout = 0.1  # Read every 0.1 seconds to keep up with hardware
                
                print(f"Reading {samples_per_channel_total} samples per channel in {samples_per_read}-sample chunks...")
                
                # Read repeatedly like manual, but more frequently to prevent buffer overflow
                for read_idx in range(num_reads_needed):
                    remaining_samples = samples_per_channel_total - len(all_channel_data.get(channels[0], []))
                    read_size = min(samples_per_read, remaining_samples)
                    
                    if read_size <= 0:
                        break
                    
                    # Read chunk (matches DAQReadNChanNSamp1DWfm)
                    # Use short timeout to read frequently and prevent buffer overflow
                    try:
                        chunk_data = task.read(
                            number_of_samples_per_channel=read_size,
                            timeout=chunk_timeout
                        )
                    except nidaqmx.errors.DaqReadError as e:
                        # If buffer overflow, try to read available data
                        if -200279 in str(e):  # Buffer overflow error
                            print(f"Warning: Buffer overflow detected, trying to read available data...")
                            try:
                                # Try to read whatever is available
                                chunk_data = task.read(
                                    number_of_samples_per_channel=read_size,
                                    timeout=0.01  # Very short timeout
                                )
                            except:
                                print(f"Failed to recover from buffer overflow at chunk {read_idx + 1}")
                                break
                        else:
                            raise
                    
                    if chunk_data is None:
                        print(f"Warning: Failed to read chunk {read_idx + 1}")
                        break
                    
                    # Process chunk data
                    import numpy as np
                    if isinstance(chunk_data, np.ndarray):
                        chunk_data = chunk_data.tolist()
                    
                    # Handle interleaved data for multiple channels
                    if num_channels > 1:
                        # Interleaved: [ch0_s0, ch1_s0, ..., ch0_s1, ch1_s1, ...]
                        flat_chunk = []
                        for item in chunk_data:
                            if isinstance(item, (list, tuple)):
                                flat_chunk.extend(item)
                            else:
                                flat_chunk.append(float(item))
                        
                        # De-interleave chunk
                        for i, channel in enumerate(channels):
                            channel_chunk = [flat_chunk[j] for j in range(i, len(flat_chunk), num_channels)]
                            all_channel_data[channel].extend(channel_chunk)
                    else:
                        # Single channel
                        flat_chunk = []
                        for item in chunk_data:
                            if isinstance(item, (list, tuple)):
                                flat_chunk.extend(item)
                            else:
                                flat_chunk.append(float(item))
                        all_channel_data[channels[0]].extend(flat_chunk)
                    
                    print(f"Read chunk {read_idx + 1}/{num_reads_needed}: {read_size} samples (total: {len(all_channel_data.get(channels[0], []))}/{samples_per_channel_total})")
                
                task.stop()
                print(f"Hardware VOLTAGE acquisition completed")
                
                # Process collected data: Use all samples directly (match manual)
                # Manual reads 1000 samples and uses them directly (no compression)
                # But we need to convert to data points for 10-second test (1ms intervals)
                result = {}
                
                for channel in channels:
                    voltage_data_volts = all_channel_data[channel][:samples_per_channel_total]  # Limit to 1000
                    print(f"Channel {channel}: {len(voltage_data_volts)} raw voltage samples")
                    
                    if len(voltage_data_volts) == 0:
                        print(f"Warning: No data collected for channel {channel}")
                        continue
                    
                    # Convert voltage to current using Ohm's law: I = V / R
                    config = self.channel_configs.get(channel, {})
                    shunt_r = config.get('shunt_r', 0.01)  # Default 0.01Ω
                    current_ma = [(v / shunt_r) * 1000 for v in voltage_data_volts]  # V/R=A, *1000=mA
                    
                    # Manual uses 1000 samples directly, but for 10-second test we need 10,000 data points
                    # So we'll use the average of 1000 samples for each 1ms data point
                    # Actually, manual reads 1000 samples total, so we'll use them as-is
                    # For 10-second test with 1ms intervals, we need to expand or repeat
                    # But let's match manual exactly: use 1000 samples
                    
                    result[channel] = {
                        'current_data': current_ma,  # Current in mA (1000 samples, match manual)
                        'sample_count': len(current_ma),
                        'name': config.get('name', channel)
                    }
                    avg_v_mv = sum(voltage_data_volts) * 1000 / len(voltage_data_volts) if voltage_data_volts else 0
                    avg_i_ma = sum(current_ma) / len(current_ma) if current_ma else 0
                    print(f"Channel {channel}: {len(current_ma)} samples (match manual: 1000 samples)")
                    print(f"  Avg voltage: {avg_v_mv:.3f}mV, Avg current: {avg_i_ma:.3f}mA (shunt={shunt_r}Ω)")
                
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