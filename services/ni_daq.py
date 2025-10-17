# NI USB-6289 DAQ Service for Current Monitoring
import time
from typing import Optional, List, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

try:
    import nidaqmx
    from nidaqmx.constants import AcquisitionType
    NI_AVAILABLE = True
except ImportError:
    NI_AVAILABLE = False

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
        """Get list of available NI DAQ devices"""
        if not NI_AVAILABLE:
            return []
        
        try:
            system = nidaqmx.system.System.local()
            devices = []
            for device in system.devices:
                devices.append(device.name)
            return devices
        except Exception as e:
            self.error_occurred.emit(f"Failed to get devices: {e}")
            return []
    
    def connect_device(self, device_name: str, channel: str = "ai0") -> bool:
        """Connect to NI DAQ device"""
        if not NI_AVAILABLE:
            self.error_occurred.emit("NI-DAQmx not installed")
            return False
        
        try:
            # Disconnect if already connected
            self.disconnect_device()
            
            # Create task
            self.task = nidaqmx.Task()
            channel_name = f"{device_name}/{channel}"
            
            # Add analog input channel
            self.task.ai_channels.add_ai_voltage_chan(
                channel_name,
                min_val=-self.voltage_range,
                max_val=self.voltage_range
            )
            
            # Test connection by reading once
            test_value = self.task.read()
            
            self.device_name = device_name
            self.channel = channel
            self.connected = True
            self.connection_changed.emit(True)
            
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
        return ["Dev1 (Mock)", "Dev2 (Mock)"]
    
    def connect_device(self, device_name: str, channel: str = "ai0") -> bool:
        self.device_name = device_name
        self.channel = channel
        self.connected = True
        self.connection_changed.emit(True)
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