"""Traditional NI-DAQ API wrapper for Python
Uses ctypes to call legacy NI-DAQ functions directly
This matches the API used by the other tool (DAQReadNChanNSamp1D)
"""

import ctypes
import sys
import os
from typing import Optional, List, Tuple
import numpy as np

# Try to find Traditional NI-DAQ DLL
POSSIBLE_DLL_PATHS = [
    # Windows standard paths
    r"C:\Windows\System32\nidaq32.dll",
    r"C:\Windows\SysWOW64\nidaq32.dll",
    r"C:\Program Files (x86)\National Instruments\Shared\ExternalCompilerSupport\C\lib32\msvc\nidaq32.lib",
    r"C:\Program Files\National Instruments\Shared\ExternalCompilerSupport\C\lib32\msvc\nidaq32.lib",
    
    # Alternative names
    r"C:\Windows\System32\nidaqold.dll",
    r"C:\Windows\System32\nidaqmxbase.dll",
]

# DAQ Constants (from Traditional DAQ API)
DAQ_DEFAULT = -1
DAQ_RSE = 0
DAQ_NRSE = 1
DAQ_DIFFERENTIAL = 2

DAQ_Volts = 0
DAQ_Amps = 1

DAQ_Start = 0
DAQ_Stop = 1

class TraditionalDAQAPI:
    """Wrapper for Traditional NI-DAQ API (pre-DAQmx)"""
    
    def __init__(self):
        self.dll = None
        self.loaded = False
        self._load_dll()
    
    def _load_dll(self):
        """Try to load Traditional NI-DAQ DLL"""
        print("\n=== Loading Traditional NI-DAQ API ===")
        
        for dll_path in POSSIBLE_DLL_PATHS:
            if os.path.exists(dll_path):
                try:
                    print(f"Trying to load: {dll_path}")
                    self.dll = ctypes.WinDLL(dll_path)
                    self.loaded = True
                    print(f"✓ Successfully loaded Traditional DAQ: {dll_path}")
                    self._setup_functions()
                    return
                except Exception as e:
                    print(f"  Failed: {e}")
        
        print("⚠️ Traditional NI-DAQ DLL not found!")
        print("This is the OLD API (pre-2003) that other tool uses.")
        print("You may need to install 'NI-DAQ (Legacy)' or 'Traditional NI-DAQ'")
        self.loaded = False
    
    def _setup_functions(self):
        """Setup function signatures for Traditional DAQ API"""
        if not self.dll:
            return
        
        try:
            # DAQCreateAIVoltageChan
            # i16 DAQCreateAIVoltageChan(i32 *taskHandle, char deviceName[], char channel[],
            #                            i32 terminalConfig, f64 minVal, f64 maxVal,
            #                            i32 units, char customScaleName[])
            self.DAQCreateAIVoltageChan = self.dll.DAQCreateAIVoltageChan
            self.DAQCreateAIVoltageChan.argtypes = [
                ctypes.POINTER(ctypes.c_int32),  # taskHandle
                ctypes.c_char_p,                  # deviceName
                ctypes.c_char_p,                  # channel
                ctypes.c_int32,                   # terminalConfig
                ctypes.c_double,                  # minVal
                ctypes.c_double,                  # maxVal
                ctypes.c_int32,                   # units
                ctypes.c_char_p                   # customScaleName
            ]
            self.DAQCreateAIVoltageChan.restype = ctypes.c_int16  # error code
            
            # DAQControl
            # i16 DAQControl(i32 taskHandle, i32 action)
            self.DAQControl = self.dll.DAQControl
            self.DAQControl.argtypes = [ctypes.c_int32, ctypes.c_int32]
            self.DAQControl.restype = ctypes.c_int16
            
            # DAQReadNChanNSamp1DWfm (this is what other tool uses!)
            # i16 DAQReadNChanNSamp1DWfm(i32 taskHandle, i32 numChans, i32 numSamples,
            #                            f64 timeout, f64 data[], i32 *numSamplesRead,
            #                            i32 *reserved)
            self.DAQReadNChanNSamp1DWfm = self.dll.DAQReadNChanNSamp1DWfm
            self.DAQReadNChanNSamp1DWfm.argtypes = [
                ctypes.c_int32,                   # taskHandle
                ctypes.c_int32,                   # numChans
                ctypes.c_int32,                   # numSamples
                ctypes.c_double,                  # timeout
                ctypes.POINTER(ctypes.c_double),  # data[]
                ctypes.POINTER(ctypes.c_int32),   # numSamplesRead
                ctypes.POINTER(ctypes.c_int32)    # reserved
            ]
            self.DAQReadNChanNSamp1DWfm.restype = ctypes.c_int16
            
            # DAQClearTask
            # i16 DAQClearTask(i32 taskHandle)
            self.DAQClearTask = self.dll.DAQClearTask
            self.DAQClearTask.argtypes = [ctypes.c_int32]
            self.DAQClearTask.restype = ctypes.c_int16
            
            print("✓ Traditional DAQ functions initialized")
            
        except Exception as e:
            print(f"⚠️ Error setting up Traditional DAQ functions: {e}")
            self.loaded = False
    
    def is_available(self) -> bool:
        """Check if Traditional DAQ API is available"""
        return self.loaded
    
    def create_ai_voltage_task(self, device_name: str, channels: List[str],
                               min_val: float = -0.2, max_val: float = 0.2,
                               terminal_config: int = DAQ_DEFAULT) -> Optional[int]:
        """Create analog input voltage task (Traditional API)
        
        Args:
            device_name: Device name (e.g., "Dev1")
            channels: List of channel names (e.g., ["ai0", "ai1"])
            min_val: Minimum voltage (-0.2V for shunt)
            max_val: Maximum voltage (0.2V for shunt)
            terminal_config: DAQ_DEFAULT, DAQ_RSE, DAQ_DIFFERENTIAL, DAQ_NRSE
        
        Returns:
            taskHandle (int) or None if failed
        """
        if not self.loaded:
            print("Traditional DAQ not available")
            return None
        
        try:
            # Create task handle
            task_handle = ctypes.c_int32(0)
            
            # Create channels (Traditional API creates all at once with channel string)
            channel_str = ",".join(channels)  # "ai0,ai1,ai2,..."
            full_channel = f"{device_name}/{channel_str}"
            
            print(f"\n=== Creating Traditional DAQ Task ===")
            print(f"Device: {device_name}")
            print(f"Channels: {channel_str}")
            print(f"Terminal Config: {terminal_config} ({'DEFAULT' if terminal_config == DAQ_DEFAULT else 'RSE' if terminal_config == DAQ_RSE else 'DIFF' if terminal_config == DAQ_DIFFERENTIAL else 'NRSE'})")
            print(f"Range: {min_val}V to {max_val}V")
            
            # Call DAQCreateAIVoltageChan
            error = self.DAQCreateAIVoltageChan(
                ctypes.byref(task_handle),
                device_name.encode('utf-8'),
                full_channel.encode('utf-8'),
                terminal_config,  # DAQ_DEFAULT = -1 (follow hardware jumper)
                min_val,
                max_val,
                DAQ_Volts,
                None  # No custom scale
            )
            
            if error != 0:
                print(f"⚠️ DAQCreateAIVoltageChan failed with error: {error}")
                return None
            
            print(f"✓ Task created: handle={task_handle.value}")
            return task_handle.value
            
        except Exception as e:
            print(f"Error creating Traditional DAQ task: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def read_voltage_channels(self, task_handle: int, num_channels: int,
                             num_samples: int = 10000, timeout: float = 10.0) -> Optional[np.ndarray]:
        """Read voltage data from multiple channels (Traditional API)
        
        This is the EXACT function the other tool uses!
        
        Args:
            task_handle: Task handle from create_ai_voltage_task()
            num_channels: Number of channels to read
            num_samples: Number of samples per channel (10000 = 10 seconds at 1kHz)
            timeout: Read timeout in seconds
        
        Returns:
            numpy array of shape (num_channels, num_samples) with voltage data
        """
        if not self.loaded:
            print("Traditional DAQ not available")
            return None
        
        try:
            print(f"\n=== Reading Traditional DAQ (DAQReadNChanNSamp1DWfm) ===")
            print(f"Task: {task_handle}")
            print(f"Channels: {num_channels}")
            print(f"Samples per channel: {num_samples}")
            print(f"Timeout: {timeout}s")
            
            # Allocate buffer for data (interleaved format)
            total_samples = num_channels * num_samples
            data_buffer = (ctypes.c_double * total_samples)()
            samples_read = ctypes.c_int32(0)
            reserved = ctypes.c_int32(0)
            
            # Start acquisition
            error = self.DAQControl(task_handle, DAQ_Start)
            if error != 0:
                print(f"⚠️ DAQControl(Start) failed: {error}")
                return None
            
            # Read data (this is what other tool uses!)
            error = self.DAQReadNChanNSamp1DWfm(
                task_handle,
                num_channels,
                num_samples,
                timeout,
                data_buffer,
                ctypes.byref(samples_read),
                ctypes.byref(reserved)
            )
            
            # Stop acquisition
            self.DAQControl(task_handle, DAQ_Stop)
            
            if error != 0:
                print(f"⚠️ DAQReadNChanNSamp1DWfm failed: {error}")
                return None
            
            print(f"✓ Read {samples_read.value} samples per channel")
            
            # Convert to numpy array and reshape
            # Data is interleaved: [ch0_s0, ch1_s0, ..., chN_s0, ch0_s1, ch1_s1, ...]
            data_array = np.array(data_buffer[:samples_read.value * num_channels])
            data_array = data_array.reshape((samples_read.value, num_channels))
            data_array = data_array.T  # Transpose to (channels, samples)
            
            # Print first few samples
            print(f"\nFirst 5 samples (Voltage in V):")
            for ch in range(min(num_channels, 3)):
                ch_data = data_array[ch]
                print(f"  Channel {ch}: {ch_data[0]:.9f}V ({ch_data[0]*1000:.6f}mV)")
            
            return data_array
            
        except Exception as e:
            print(f"Error reading Traditional DAQ: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def clear_task(self, task_handle: int):
        """Clear/destroy task"""
        if not self.loaded or task_handle is None:
            return
        
        try:
            error = self.DAQClearTask(task_handle)
            if error != 0:
                print(f"⚠️ DAQClearTask failed: {error}")
            else:
                print(f"✓ Task {task_handle} cleared")
        except Exception as e:
            print(f"Error clearing task: {e}")


class TraditionalDAQService:
    """High-level service for Traditional DAQ API"""
    
    def __init__(self):
        self.api = TraditionalDAQAPI()
        self.device_name = None
        self.current_task = None
    
    def is_available(self) -> bool:
        """Check if Traditional DAQ is available"""
        return self.api.is_available()
    
    def read_current_channels(self, device_name: str, channels: List[str],
                             shunt_resistors: List[float],
                             num_samples: int = 10000,
                             terminal_config: int = DAQ_DEFAULT) -> Optional[dict]:
        """Read current from multiple channels using Traditional DAQ API
        
        This uses the SAME API as the other tool!
        
        Args:
            device_name: Device name (e.g., "Dev1")
            channels: List of channel names (e.g., ["ai0", "ai1", ...])
            shunt_resistors: List of shunt resistor values for each channel (e.g., [0.01, 0.1, ...])
            num_samples: Number of samples per channel (default: 10000)
            terminal_config: DAQ_DEFAULT (follow hardware), DAQ_RSE, DAQ_DIFFERENTIAL
        
        Returns:
            dict: {
                'ai0': {'voltage_data': [...], 'current_data': [...], 'avg_current_ma': float},
                ...
            }
        """
        if not self.api.is_available():
            print("⚠️ Traditional DAQ API not available")
            return None
        
        try:
            # Create task
            task_handle = self.api.create_ai_voltage_task(
                device_name,
                channels,
                min_val=-0.2,
                max_val=0.2,
                terminal_config=terminal_config
            )
            
            if task_handle is None:
                return None
            
            # Read voltage data
            voltage_data = self.api.read_voltage_channels(
                task_handle,
                len(channels),
                num_samples,
                timeout=10.0
            )
            
            # Clear task
            self.api.clear_task(task_handle)
            
            if voltage_data is None:
                return None
            
            # Convert voltage to current
            print(f"\n=== Converting Voltage to Current ===")
            result = {}
            
            for i, channel in enumerate(channels):
                ch_voltage_data = voltage_data[i]  # Voltage in V
                shunt_r = shunt_resistors[i] if i < len(shunt_resistors) else 0.01
                
                # Calculate current: I = V / R
                ch_current_data_a = ch_voltage_data / shunt_r  # Amps
                ch_current_data_ma = ch_current_data_a * 1000  # mA
                
                avg_voltage_v = np.mean(ch_voltage_data)
                avg_current_ma = np.mean(ch_current_data_ma)
                
                result[channel] = {
                    'voltage_data': ch_voltage_data.tolist(),  # List of voltages (V)
                    'current_data': ch_current_data_ma.tolist(),  # List of currents (mA)
                    'avg_voltage_v': avg_voltage_v,
                    'avg_voltage_mv': avg_voltage_v * 1000,
                    'avg_current_ma': avg_current_ma,
                    'sample_count': len(ch_current_data_ma),
                    'shunt_r': shunt_r
                }
                
                print(f"  {channel}: {avg_voltage_v*1000:.6f}mV → {avg_current_ma:.3f}mA (shunt={shunt_r}Ω)")
            
            print(f"✓ Traditional DAQ read completed: {len(result)} channels")
            return result
            
        except Exception as e:
            print(f"Error reading current channels: {e}")
            import traceback
            traceback.print_exc()
            return None


# Create singleton instance
_traditional_daq_service = None

def get_traditional_daq_service() -> TraditionalDAQService:
    """Get Traditional DAQ service singleton"""
    global _traditional_daq_service
    if _traditional_daq_service is None:
        _traditional_daq_service = TraditionalDAQService()
    return _traditional_daq_service
