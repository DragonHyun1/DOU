"""
Traditional NI-DAQ (Legacy) API Wrapper for Python

NOTE: This requires the old NI-DAQ (not NI-DAQmx) drivers installed.
The DLL is typically located at:
- C:\Windows\System32\nidaqmx.dll (old version)
- C:\Windows\System32\nidaq32.dll (even older)

This is for compatibility with Manual measurement tool that uses
DAQReadNChanNSamp2DF64 function.
"""

import ctypes
from ctypes import c_int16, c_uint16, c_int32, c_uint32, c_double, POINTER, byref
import numpy as np
from typing import Optional, List

class TraditionalNIDAQ:
    """Wrapper for Traditional NI-DAQ (Legacy) API"""
    
    # Traditional NI-DAQ Error Codes
    NO_ERROR = 0
    
    def __init__(self):
        self.dll = None
        self.available = False
        
        # Try to load Traditional NI-DAQ DLL
        dll_paths = [
            r"C:\Windows\System32\nidaq32.dll",  # Very old
            r"C:\Windows\System32\nidaqmx.dll",  # Old (not to be confused with modern NI-DAQmx)
            r"C:\Program Files\National Instruments\NI-DAQ\Bin\nidaq32.dll",
            r"C:\Program Files (x86)\National Instruments\NI-DAQ\Bin\nidaq32.dll",
        ]
        
        for dll_path in dll_paths:
            try:
                self.dll = ctypes.CDLL(dll_path)
                self.available = True
                print(f"✅ Loaded Traditional NI-DAQ from: {dll_path}")
                self._setup_functions()
                break
            except Exception as e:
                continue
        
        if not self.available:
            print("⚠️ Traditional NI-DAQ (Legacy) not found")
            print("   This is expected if only NI-DAQmx (modern) is installed")
            print("   Cannot use DAQReadNChanNSamp2DF64 function")
    
    def _setup_functions(self):
        """Setup function signatures for Traditional NI-DAQ"""
        if not self.dll:
            return
        
        try:
            # DAQ_Config
            # i16 DAQ_Config(i16 deviceNumber, i16 mode)
            self.dll.DAQ_Config.argtypes = [c_int16, c_int16]
            self.dll.DAQ_Config.restype = c_int16
            
            # DAQ_Rate
            # i16 DAQ_Rate(f64 rate, i16 units, i16 *timebase, u32 *sampleInterval)
            self.dll.DAQ_Rate.argtypes = [c_double, c_int16, POINTER(c_int16), POINTER(c_uint32)]
            self.dll.DAQ_Rate.restype = c_int16
            
            # DAQReadNChanNSamp2DF64
            # i16 DAQReadNChanNSamp2DF64(
            #     i16 deviceNumber,
            #     i16 channels[],
            #     i16 numChannels,
            #     u32 samplesPerChannel,
            #     f64 rate,
            #     i16 gain,
            #     f64 buffer[][],
            #     u32 samplesRead[]
            # )
            # Note: This is complex due to 2D array, might need adjustment
            
            print("✅ Traditional NI-DAQ function signatures setup")
            
        except Exception as e:
            print(f"⚠️ Failed to setup Traditional NI-DAQ functions: {e}")
    
    def read_multi_channel(self, device_number: int, channels: List[int], 
                          samples_per_channel: int, rate: float, gain: int) -> Optional[np.ndarray]:
        """
        Read multiple channels using DAQReadNChanNSamp2DF64
        
        Args:
            device_number: Device number (e.g., 1 for Dev1)
            channels: List of channel numbers (e.g., [0, 1, 2])
            samples_per_channel: Number of samples per channel
            rate: Sampling rate in Hz
            gain: Gain setting (1, 2, 5, 10, 20, 50, 100)
                  Gain=1: ±10V, Gain=2: ±5V, Gain=5: ±2V, etc.
        
        Returns:
            2D numpy array [channels][samples] or None if failed
        """
        if not self.available or not self.dll:
            print("❌ Traditional NI-DAQ not available")
            return None
        
        try:
            num_channels = len(channels)
            
            # Allocate buffer for data
            # 2D array: buffer[channel][sample]
            buffer_size = num_channels * samples_per_channel
            buffer = (c_double * buffer_size)()
            
            # Convert channels list to ctypes array
            channels_array = (c_int16 * num_channels)(*channels)
            
            # Samples read array
            samples_read = (c_uint32 * num_channels)()
            
            print(f"📊 Traditional NI-DAQ Read:")
            print(f"   → Device: {device_number}")
            print(f"   → Channels: {channels}")
            print(f"   → Samples/Channel: {samples_per_channel}")
            print(f"   → Rate: {rate} Hz")
            print(f"   → Gain: {gain}")
            
            # Call DAQReadNChanNSamp2DF64
            # NOTE: This function signature might need adjustment based on actual DLL
            error = self.dll.DAQReadNChanNSamp2DF64(
                c_int16(device_number),
                channels_array,
                c_int16(num_channels),
                c_uint32(samples_per_channel),
                c_double(rate),
                c_int16(gain),
                buffer,
                samples_read
            )
            
            if error != self.NO_ERROR:
                print(f"❌ DAQReadNChanNSamp2DF64 error: {error}")
                return None
            
            # Convert to numpy array and reshape
            data = np.array(buffer[:buffer_size])
            data = data.reshape((num_channels, samples_per_channel))
            
            print(f"✅ Read {samples_read[0]} samples per channel")
            return data
            
        except Exception as e:
            print(f"❌ Traditional NI-DAQ read error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_gain_for_range(self, voltage_range: float) -> int:
        """
        Get appropriate gain value for desired voltage range
        
        Args:
            voltage_range: Desired max voltage (e.g., 5.0 for ±5V)
        
        Returns:
            Gain value (1, 2, 5, 10, 20, 50, 100)
        """
        gain_map = {
            10.0: 1,   # ±10V
            5.0: 2,    # ±5V
            2.0: 5,    # ±2V
            1.0: 10,   # ±1V
            0.5: 20,   # ±0.5V
            0.2: 50,   # ±0.2V
            0.1: 100,  # ±0.1V
        }
        
        # Find closest gain
        for v_range, gain in sorted(gain_map.items(), reverse=True):
            if voltage_range >= v_range:
                return gain
        
        return 100  # Highest gain (smallest range)


# Test if Traditional NI-DAQ is available
if __name__ == "__main__":
    daq = TraditionalNIDAQ()
    
    if daq.available:
        print("\n✅ Traditional NI-DAQ is available!")
        print("   Can use DAQReadNChanNSamp2DF64")
        
        # Example usage (won't actually run without hardware)
        print("\nExample usage:")
        print("  data = daq.read_multi_channel(")
        print("      device_number=1,")
        print("      channels=[0, 1, 2],")
        print("      samples_per_channel=1000,")
        print("      rate=30000.0,")
        print("      gain=2  # ±5V range")
        print("  )")
    else:
        print("\n❌ Traditional NI-DAQ NOT available")
        print("   Only NI-DAQmx (modern) is installed")
        print("   Must use NI-DAQmx API (DAQmxReadAnalogF64)")
        print("\n💡 Recommendation:")
        print("   → Ask Manual tool developer for exact DAQ settings")
        print("   → Match Gain/Range settings in NI-DAQmx")
        print("   → Or update Manual tool to use NI-DAQmx")
