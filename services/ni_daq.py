# NI USB-6289 DAQ Service for Current Monitoring (C API ONLY)
import time
from typing import Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import os
import sys
import ctypes
from ctypes import c_int32, c_double, c_uint32, c_char_p, c_char, byref, POINTER, create_string_buffer

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

# Load NI-DAQmx C API (nicaiu.dll) - ONLY METHOD
print("="*60)
print("NI-DAQmx Initialization (C API ONLY)")
print("="*60)

try:
    # Try to load nicaiu.dll from system paths
    nicaiu = ctypes.windll.nicaiu
    print("✅ nicaiu.dll loaded successfully")
    print("   → Using C API for ALL DAQ operations")
    C_API_AVAILABLE = True
    
    # Test DLL by getting driver version
    try:
        version_buffer = create_string_buffer(256)
        status = nicaiu.DAQmxGetSysNIDAQMajorVersion(byref(c_uint32()))
        if status == 0:
            print("   → C API verified (function calls working)")
    except:
        print("   ⚠️ C API loaded but verification failed")
        
except Exception as e:
    nicaiu = None
    print(f"❌ nicaiu.dll not found: {e}")
    print("   → DAQ operations will not be available")
    C_API_AVAILABLE = False

print("="*60)

# NI-DAQmx C API Constants (from NIDAQmx.h)
DAQmx_Val_Volts = 10348
DAQmx_Val_Amps = 10342
DAQmx_Val_RSE = 10083  # Referenced Single-Ended
DAQmx_Val_NRSE = 10078  # Non-Referenced Single-Ended
DAQmx_Val_Diff = 10106  # Differential
DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_ContSamps = 10123
DAQmx_Val_Rising = 10280
DAQmx_Val_Falling = 10171
DAQmx_Val_GroupByChannel = 0
DAQmx_Val_GroupByScanNumber = 1

class NIDAQService(QObject):
    """Service for NI DAQ multi-channel voltage/current monitoring (C API ONLY)"""
    
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
        self.channel = None
        self.task_handle = None  # C API task handle (c_uint32)
        self.voltage_range = 10.0  # Default ±10V range
        self.last_current = 0.0
        
        # Current scaling parameters
        self.current_scale = 1.0
        self.current_offset = 0.0
        
        # Multi-channel configuration
        self.active_channels = {}
        self.channel_configs = {}
        
        # Monitoring state
        self.monitoring = False
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._read_all_channels)
        self.monitor_interval = 500  # 0.5 second default
        
        # Last readings
        self.last_readings = {}
        
        # Default configuration for 12 channels
        self._init_default_channels()
    
    def _init_default_channels(self):
        """Initialize default channel configurations"""
        default_rails = [
            # Phone App Test channels (ai0-ai5)
            {'name': 'VBAT', 'target_v': 4.00, 'shunt_r': 0.010},              # ai0
            {'name': 'VDD_1P8_AP', 'target_v': 1.80, 'shunt_r': 0.100},        # ai1
            {'name': 'VDD_MLDO_2P0', 'target_v': 2.00, 'shunt_r': 0.005},      # ai2
            {'name': 'VDD_WIFI_1P0', 'target_v': 1.00, 'shunt_r': 0.005},      # ai3
            {'name': 'VDD_1P2_AP_WIFI', 'target_v': 1.20, 'shunt_r': 0.100},   # ai4
            {'name': 'VDD_1P35_WIFIPMU', 'target_v': 1.35, 'shunt_r': 0.010},  # ai5
            # Additional channels (ai6-ai11)
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
                'enabled': False,
                'voltage_range': 10.0
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
        """Read all enabled channels using C API"""
        if not self.connected or not C_API_AVAILABLE:
            return
        
        try:
            enabled_channels = [ch for ch, config in self.channel_configs.items() if config.get('enabled', False)]
            
            if not enabled_channels:
                return
            
            readings = {}
            
            # Read each channel using C API (single-shot per channel)
            for channel in enabled_channels:
                try:
                    # Create temporary task for single channel read
                    task_handle = c_uint32(0)
                    status = nicaiu.DAQmxCreateTask(b"", byref(task_handle))
                    if status != 0:
                        print(f"Failed to create task for {channel}: {status}")
                        continue
                    
                    try:
                        channel_name = f"{self.device_name}/{channel}".encode('ascii')
                        config = self.channel_configs[channel]
                        
                        # Add voltage channel (DIFFERENTIAL first, RSE fallback)
                        status = nicaiu.DAQmxCreateAIVoltageChan(
                            task_handle,
                            channel_name,
                            b"",
                            DAQmx_Val_Diff,  # DIFFERENTIAL
                            c_double(-0.2),
                            c_double(0.2),
                            c_int32(DAQmx_Val_Volts),
                            None
                        )
                        
                        if status != 0:
                            # Fallback to RSE
                            status = nicaiu.DAQmxCreateAIVoltageChan(
                                task_handle,
                                channel_name,
                                b"",
                                DAQmx_Val_RSE,
                                c_double(-5.0),
                                c_double(5.0),
                                c_int32(DAQmx_Val_Volts),
                                None
                            )
                        
                        if status != 0:
                            print(f"Failed to add channel {channel}: {status}")
                            continue
                        
                        # Read single sample
                        voltage = c_double(0.0)
                        samples_read = c_int32(0)
                        
                        status = nicaiu.DAQmxReadAnalogScalarF64(
                            task_handle,
                            c_double(1.0),  # 1 second timeout
                            byref(voltage),
                            None
                        )
                        
                        if status == 0:
                            # Calculate current
                            shunt_r = config.get('shunt_r', 0.010)
                            current = voltage.value / shunt_r if shunt_r > 0 else 0.0
                            
                            readings[channel] = {
                                'voltage': voltage.value,
                                'current': current,
                                'name': config.get('name', channel),
                                'target_v': config.get('target_v', 0.0)
                            }
                            
                            self.last_readings[channel] = {'voltage': voltage.value, 'current': current}
                        else:
                            print(f"Read failed for {channel}: {status}")
                            
                    finally:
                        nicaiu.DAQmxClearTask(task_handle)
                        
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
        """Get list of available NI DAQ devices using C API"""
        print("=== NI-DAQmx Device Detection (C API) ===")
        
        detected_devices = []
        
        if C_API_AVAILABLE and nicaiu:
            print("C API available, detecting devices...")
            try:
                # DAQmxGetSysDevNames
                buffer_size = 4096
                device_buffer = create_string_buffer(buffer_size)
                
                status = nicaiu.DAQmxGetSysDevNames(device_buffer, c_uint32(buffer_size))
                
                if status == 0:
                    device_string = device_buffer.value.decode('ascii', errors='ignore').strip()
                    
                    if device_string:
                        device_names = [d.strip() for d in device_string.split(',') if d.strip()]
                        print(f"Found {len(device_names)} devices: {device_names}")
                        
                        for dev_name in device_names:
                            # Get product type
                            product_buffer = create_string_buffer(256)
                            status2 = nicaiu.DAQmxGetDevProductType(
                                dev_name.encode('ascii'),
                                product_buffer,
                                c_uint32(256)
                            )
                            
                            if status2 == 0:
                                product_type = product_buffer.value.decode('ascii', errors='ignore')
                                detected_devices.append(f"{dev_name} (Real - {product_type})")
                            else:
                                detected_devices.append(f"{dev_name} (Real)")
                    else:
                        print("No devices found (empty string)")
                else:
                    print(f"DAQmxGetSysDevNames failed: {status}")
                    
            except Exception as e:
                print(f"Error detecting devices: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("C API not available")
        
        print(f"\n=== FINAL DEVICE LIST ===")
        print(f"Total devices: {len(detected_devices)}")
        for i, device in enumerate(detected_devices):
            print(f"  {i+1}. {device}")
        
        return detected_devices
    
    def connect_device(self, device_name: str, channel: str = "ai0") -> bool:
        """Connect to NI DAQ device using C API"""
        if not C_API_AVAILABLE:
            self.error_occurred.emit("NI-DAQmx C API not available")
            return False
        
        try:
            print("=== NI DAQ Connection (C API) ===")
            
            # Disconnect if already connected
            self.disconnect_device()
            
            # Extract device name from formatted string
            clean_device_name = device_name.split(' (')[0] if ' (' in device_name else device_name
            
            print(f"Device: {clean_device_name}, Channel: {channel}")
            
            # Create task
            task_handle = c_uint32(0)
            status = nicaiu.DAQmxCreateTask(b"", byref(task_handle))
            if status != 0:
                print(f"DAQmxCreateTask failed: {status}")
                self.error_occurred.emit(f"Failed to create task: {status}")
                return False
            
            print(f"✅ Task created: handle={task_handle.value}")
            
            # Add voltage channel
            channel_name = f"{clean_device_name}/{channel}".encode('ascii')
            
            status = nicaiu.DAQmxCreateAIVoltageChan(
                task_handle,
                channel_name,
                b"",
                DAQmx_Val_RSE,
                c_double(-5.0),
                c_double(5.0),
                c_int32(DAQmx_Val_Volts),
                None
            )
            
            if status != 0:
                print(f"DAQmxCreateAIVoltageChan failed: {status}")
                nicaiu.DAQmxClearTask(task_handle)
                self.error_occurred.emit(f"Failed to add channel: {status}")
                return False
            
            print(f"✅ Channel added: {channel_name.decode('ascii')}")
            
            # Test read
            voltage = c_double(0.0)
            status = nicaiu.DAQmxReadAnalogScalarF64(
                task_handle,
                c_double(1.0),
                byref(voltage),
                None
            )
            
            if status != 0:
                print(f"Test read failed: {status}")
                nicaiu.DAQmxClearTask(task_handle)
                self.error_occurred.emit(f"Test read failed: {status}")
                return False
            
            print(f"✅ Test read successful: {voltage.value}V")
            
            self.device_name = clean_device_name
            self.channel = channel
            self.task_handle = task_handle
            self.connected = True
            self.connection_changed.emit(True)
            
            print(f"SUCCESS: Connected to {clean_device_name}/{channel}")
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {e}")
            self.disconnect_device()
            return False
    
    def disconnect_device(self):
        """Disconnect from NI DAQ device"""
        try:
            self.stop_monitoring()
            
            if self.task_handle and C_API_AVAILABLE:
                nicaiu.DAQmxClearTask(self.task_handle)
                self.task_handle = None
            
            self.device_name = None
            self.connected = False
            self.connection_changed.emit(False)
            
        except Exception as e:
            self.error_occurred.emit(f"Disconnect error: {e}")
    
    def read_current_once(self) -> Optional[float]:
        """Read current value once using C API"""
        if not self.connected or not self.task_handle or not C_API_AVAILABLE:
            return None
        
        try:
            voltage = c_double(0.0)
            status = nicaiu.DAQmxReadAnalogScalarF64(
                self.task_handle,
                c_double(1.0),
                byref(voltage),
                None
            )
            
            if status == 0:
                current = (voltage.value * self.current_scale) + self.current_offset
                self.last_current = current
                self.current_updated.emit(current)
                return current
            else:
                return None
            
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
    
    def set_scaling(self, scale: float, offset: float = 0.0):
        """Set current scaling parameters"""
        self.current_scale = scale
        self.current_offset = offset
    
    def set_voltage_range(self, voltage_range: float):
        """Set voltage input range"""
        self.voltage_range = voltage_range
        
        # Reconnect if already connected
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

# Mock service for when C API is not available
class MockNIDAQService(NIDAQService):
    """Mock NI DAQ service for testing without hardware"""
    
    def __init__(self):
        super().__init__()
        self.mock_current = 0.0
        
    def get_available_devices(self) -> List[str]:
        print("=== Using Mock NI DAQ Service ===")
        print("C API not available, returning mock devices...")
        
        mock_devices = [
            "Dev1 (Mock USB-6289)",
            "Dev2 (Mock USB-6008)", 
            "Dev3 (Mock USB-6001)"
        ]
        
        return mock_devices
    
    def connect_device(self, device_name: str, channel: str = "ai0") -> bool:
        clean_device_name = device_name.split(' (')[0] if ' (' in device_name else device_name
        
        print(f"Mock: Connecting to {clean_device_name}/{channel}")
        
        self.device_name = clean_device_name
        self.channel = channel
        self.connected = True
        self.connection_changed.emit(True)
        
        return True
    
    def read_current_once(self) -> Optional[float]:
        if not self.connected:
            return None
        
        import random
        self.mock_current = 1.5 + random.uniform(-0.1, 0.1)
        self.last_current = self.mock_current
        self.current_updated.emit(self.mock_current)
        return self.mock_current

def create_ni_service() -> NIDAQService:
    """Factory function to create NI DAQ service"""
    if C_API_AVAILABLE:
        return NIDAQService()
    else:
        return MockNIDAQService()
