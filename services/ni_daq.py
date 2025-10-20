# NI USB-6289 DAQ Service for Current Monitoring
import time
from typing import Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import os
import sys

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
    print(f"NI-DAQmx imported successfully, version: {getattr(nidaqmx, '__version__', 'unknown')}")
except ImportError as e:
    NI_AVAILABLE = False
    print(f"NI-DAQmx import failed: {e}")
except Exception as e:
    NI_AVAILABLE = False
    print(f"NI-DAQmx import error: {e}")

class NIDAQService(QObject):
    """Service for NI USB-6289 DAQ current monitoring"""
    
    # Signals
    current_updated = pyqtSignal(float)  # current value
    connection_changed = pyqtSignal(bool)  # connected status
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self):
        super().__init__()
        
        # Connection state
        self.connected = False
        self.device_name = None
        self.channel = "ai0"
        self.task = None
        
        # Monitoring state
        self.monitoring = False
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._read_current)
        self.monitor_interval = 1000  # 1 second
        
        # Current reading
        self.last_current = 0.0
        
        # Configuration
        self.voltage_range = 10.0  # ±10V
        self.current_scale = 1.0   # A/V scaling factor
        self.current_offset = 0.0  # A offset
        
    def get_available_devices(self) -> List[str]:
        """Get list of available NI DAQ devices using proper NI-DAQmx API"""
        if not NI_AVAILABLE:
            print("NI-DAQmx not available")
            return ["NI-DAQmx not installed"]
        
        try:
            print("=== NI-DAQmx Device Detection ===")
            
            # Check environment
            ni_paths = [p for p in os.environ.get('PATH', '').split(os.pathsep) if 'National Instruments' in p or 'NIDAQ' in p]
            print(f"NI paths in environment: {len(ni_paths)}")
            for path in ni_paths:
                print(f"  - {path}")
            
            # Get system instance
            system = nidaqmx.system.System.local()
            print(f"NI-DAQmx System version: {system.driver_version}")
            
            # Get device names first (more reliable)
            device_names = system.devices.device_names
            print(f"Device names from system: {device_names}")
            
            devices = []
            
            if not device_names:
                print("No device names returned from NI-DAQmx system")
                return ["No NI DAQ devices found - check connections"]
            
            for device_name in device_names:
                try:
                    print(f"\n--- Processing device: {device_name} ---")
                    
                    # Get device object
                    device = system.devices[device_name]
                    
                    # Get basic info
                    product_type = device.product_type
                    print(f"Product Type: {product_type}")
                    
                    # Get serial number (different methods for different devices)
                    serial_number = "Unknown"
                    try:
                        serial_number = device.dev_serial_num
                        print(f"Serial Number: {serial_number}")
                    except Exception as e:
                        print(f"Serial number not available: {e}")
                    
                    # Get channel information
                    ai_channels = []
                    ao_channels = []
                    
                    try:
                        ai_channel_names = device.ai_physical_chans.channel_names
                        ai_channels = list(ai_channel_names)
                        print(f"AI Channels ({len(ai_channels)}): {ai_channels[:5]}{'...' if len(ai_channels) > 5 else ''}")
                    except Exception as e:
                        print(f"AI channels not available: {e}")
                    
                    try:
                        ao_channel_names = device.ao_physical_chans.channel_names
                        ao_channels = list(ao_channel_names)
                        print(f"AO Channels ({len(ao_channels)}): {ao_channels[:3]}{'...' if len(ao_channels) > 3 else ''}")
                    except Exception as e:
                        print(f"AO channels not available: {e}")
                    
                    # Format device info for display
                    if serial_number != "Unknown":
                        device_info = f"{device_name} ({product_type}, S/N: {serial_number})"
                    else:
                        device_info = f"{device_name} ({product_type})"
                    
                    devices.append(device_info)
                    print(f"Added device: {device_info}")
                    
                except Exception as e:
                    print(f"ERROR processing device {device_name}: {e}")
                    # Add device with minimal info
                    devices.append(f"{device_name} (Error: {str(e)[:50]})")
            
            if not devices:
                print("No valid devices processed")
                return ["No NI DAQ devices found - check connections"]
            
            print(f"Returning {len(devices)} devices: {devices}")
            return devices
        except Exception as e:
            print(f"Exception in get_available_devices: {e}")
            print(f"Exception type: {type(e)}")
            
            # 특정 에러에 대한 추가 정보
            if "Could not find an installation" in str(e):
                print("NI-DAQmx runtime not found. Checking possible locations...")
                for path in possible_paths:
                    exists = os.path.exists(path)
                    print(f"  {path}: {'EXISTS' if exists else 'NOT FOUND'}")
            
            self.error_occurred.emit(f"Failed to get devices: {e}")
            return [f"Error: NI-DAQmx runtime not found"]
    
    def connect_device(self, device_name: str, channel: str = "ai0") -> bool:
        """Connect to NI DAQ device"""
        if not NI_AVAILABLE:
            self.error_occurred.emit("NI-DAQmx not installed")
            return False
        
        try:
            # Disconnect if already connected
            self.disconnect_device()
            
            # Extract device name from formatted string (remove parentheses info)
            clean_device_name = device_name.split(' (')[0] if ' (' in device_name else device_name
            
            print(f"Attempting to connect to device: {clean_device_name}")
            print(f"Channel: {channel}")
            
            # Create task
            self.task = nidaqmx.Task()
            channel_name = f"{clean_device_name}/{channel}"
            
            print(f"Creating channel: {channel_name}")
            
            # Add analog input channel
            self.task.ai_channels.add_ai_voltage_chan(
                channel_name,
                min_val=-self.voltage_range,
                max_val=self.voltage_range
            )
            
            # Test connection by reading once
            test_value = self.task.read()
            print(f"Test read successful: {test_value}V")
            
            self.device_name = clean_device_name
            self.channel = channel
            self.connected = True
            self.connection_changed.emit(True)
            
            print(f"✅ NI DAQ connected successfully: {clean_device_name}/{channel}")
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
        print("Using Mock NI DAQ Service - no real hardware")
        return [
            "Dev1 (USB-6289, S/N: Mock001)",
            "Dev2 (USB-6008, S/N: Mock002)"
        ]
    
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