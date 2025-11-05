#!/usr/bin/env python3
"""Compare Traditional DAQ API vs DAQmx API
This will show if the API difference causes the measurement discrepancy
"""

import sys
sys.path.append('/workspace')

from services.traditional_daq import get_traditional_daq_service, DAQ_DEFAULT
from services.ni_daq import NIDAQService
import numpy as np

# Test configuration
DEVICE_NAME = "Dev1"
CHANNELS = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5"]
CHANNEL_NAMES = ["VBAT", "VDD_1P8_AP", "VDD_MLDO_2P0", "VDD_WIFI_1P0", "VDD_1P2_AP_WIFI", "VDD_1P35_WIFIPMU"]
SHUNT_RESISTORS = [0.01, 0.1, 0.1, 0.005, 0.05, 0.05]  # Same as DoU config
NUM_SAMPLES = 10000  # 10 seconds at 1kHz

def test_traditional_daq():
    """Test Traditional DAQ API (like other tool)"""
    print("\n" + "="*70)
    print("TEST 1: Traditional DAQ API (같은 API - 다른 툴)")
    print("="*70)
    
    trad_daq = get_traditional_daq_service()
    
    if not trad_daq.is_available():
        print("\n⚠️ Traditional DAQ API not available!")
        print("You need to install 'NI-DAQ (Legacy)' or 'Traditional NI-DAQ'")
        print("This is the OLD API that the other tool uses.")
        return None
    
    # Read using Traditional API
    result = trad_daq.read_current_channels(
        device_name=DEVICE_NAME,
        channels=CHANNELS,
        shunt_resistors=SHUNT_RESISTORS,
        num_samples=NUM_SAMPLES,
        terminal_config=DAQ_DEFAULT  # Follow hardware jumper (like other tool)
    )
    
    if result:
        print("\n✓ Traditional DAQ measurement completed!")
        print("\nResults:")
        for i, channel in enumerate(CHANNELS):
            if channel in result:
                data = result[channel]
                print(f"  {CHANNEL_NAMES[i]:20s} ({channel}): "
                      f"{data['avg_voltage_mv']:8.3f}mV → "
                      f"{data['avg_current_ma']:8.3f}mA "
                      f"(shunt={data['shunt_r']}Ω)")
    
    return result

def test_daqmx():
    """Test DAQmx API (current DoU)"""
    print("\n" + "="*70)
    print("TEST 2: DAQmx API (현재 DoU 툴)")
    print("="*70)
    
    daq = NIDAQService()
    
    # Configure channels
    for i, channel in enumerate(CHANNELS):
        daq.set_channel_config(
            channel=channel,
            name=CHANNEL_NAMES[i],
            target_v=0.0,
            shunt_r=SHUNT_RESISTORS[i],
            enabled=True
        )
    
    # Connect
    if not daq.connect_device(DEVICE_NAME, CHANNELS[0]):
        print("⚠️ Failed to connect to device")
        return None
    
    # Read using hardware-timed acquisition (matching DoU)
    result = daq.read_current_channels_hardware_timed(
        channels=CHANNELS,
        sample_rate=1000.0,  # 1kHz (1 sample per ms)
        compress_ratio=1,     # No compression for fair comparison
        duration_seconds=10.0
    )
    
    daq.disconnect_device()
    
    if result:
        print("\n✓ DAQmx measurement completed!")
        print("\nResults:")
        for i, channel in enumerate(CHANNELS):
            if channel in result:
                data = result[channel]
                current_data = data['current_data']
                avg_current_ma = np.mean(current_data)
                config = daq.get_channel_config(channel)
                shunt_r = config.get('shunt_r', 0.01)
                avg_voltage_mv = avg_current_ma * shunt_r  # Reverse calculate
                
                print(f"  {CHANNEL_NAMES[i]:20s} ({channel}): "
                      f"{avg_voltage_mv:8.3f}mV → "
                      f"{avg_current_ma:8.3f}mA "
                      f"(shunt={shunt_r}Ω)")
    
    return result

def compare_results(trad_result, daqmx_result):
    """Compare Traditional DAQ vs DAQmx results"""
    print("\n" + "="*70)
    print("COMPARISON: Traditional DAQ vs DAQmx")
    print("="*70)
    
    if not trad_result or not daqmx_result:
        print("⚠️ Cannot compare - one or both measurements failed")
        return
    
    print(f"\n{'Channel':20s} {'Traditional':>12s} {'DAQmx':>12s} {'Ratio':>8s} {'Diff':>10s}")
    print("-" * 70)
    
    for i, channel in enumerate(CHANNELS):
        if channel in trad_result and channel in daqmx_result:
            trad_ma = trad_result[channel]['avg_current_ma']
            daqmx_ma = np.mean(daqmx_result[channel]['current_data'])
            
            ratio = daqmx_ma / trad_ma if trad_ma != 0 else 0
            diff = daqmx_ma - trad_ma
            
            # Color code based on difference
            if abs(ratio - 1.0) < 0.05:  # Within 5%
                status = "✓"
            elif abs(ratio - 1.0) < 0.20:  # Within 20%
                status = "~"
            else:
                status = "✗"
            
            print(f"{CHANNEL_NAMES[i]:20s} "
                  f"{trad_ma:12.3f} "
                  f"{daqmx_ma:12.3f} "
                  f"{ratio:8.2f}x "
                  f"{diff:+10.3f} {status}")
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
If Traditional DAQ values match the "Manual tool" better:
  → API difference is the root cause
  → DoU should switch to Traditional DAQ API

If both APIs give similar values:
  → Problem is elsewhere (shunt values, hardware setup, etc.)
  → Need to investigate further
    """)

def main():
    """Run comparison test"""
    print("\n" + "="*70)
    print("Traditional DAQ vs DAQmx API Comparison")
    print("="*70)
    print("""
This test will:
1. Measure using Traditional DAQ API (like other tool)
2. Measure using DAQmx API (current DoU)
3. Compare the results

Expected outcome:
- If Traditional DAQ matches Manual tool better
  → We found the root cause!
  → Switch DoU to Traditional DAQ API
    """)
    
    input("\nPress Enter to start test...")
    
    # Test 1: Traditional DAQ
    trad_result = test_traditional_daq()
    
    if trad_result is None:
        print("\n" + "="*70)
        print("⚠️ Traditional DAQ API NOT AVAILABLE")
        print("="*70)
        print("""
Traditional NI-DAQ DLL not found!

The other tool uses Traditional DAQ API (nidaq32.dll).
You need to install it:

1. Download "NI-DAQ (Legacy)" from ni.com
2. Or check if nidaq32.dll exists in:
   - C:\\Windows\\System32\\
   - C:\\Program Files\\National Instruments\\...

Without this, we cannot test if API difference is the cause.
        """)
        return
    
    input("\nPress Enter to continue with DAQmx test...")
    
    # Test 2: DAQmx
    daqmx_result = test_daqmx()
    
    # Compare
    if daqmx_result:
        compare_results(trad_result, daqmx_result)
    
    print("\n✓ Test completed!")

if __name__ == '__main__':
    main()
