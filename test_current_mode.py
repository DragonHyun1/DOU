#!/usr/bin/env python3
"""
Current Mode Test Script

Tests ai3 using Current Mode instead of Voltage Mode
to match Manual measurement tool behavior.

Usage:
    python test_current_mode.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nidaqmx
from nidaqmx.constants import AcquisitionType, CurrentUnits, CurrentShuntResistorLocation

def test_current_mode():
    """Test ai3 with Current Mode (DAQmxCreateAICurrentChan)"""
    
    print("=" * 80)
    print("🔬 Current Mode Test for ai3 Channel")
    print("=" * 80)
    print()
    print("📌 Manual Measurement Reference:")
    print("   → ai3 Average Current: 1.018 mA")
    print("   → ai3 Voltage: 1.05V (Rail voltage, for reference)")
    print()
    print("🎯 Hypothesis: Manual uses Current Mode (DAQmxCreateAICurrentChan)")
    print("   → DAQ internally measures voltage and converts to current")
    print("   → Uses internal calibration for accuracy")
    print()
    print("=" * 80)
    print()
    
    # Test configuration
    device_name = "Dev1"
    channel = "ai3"
    shunt_r = 0.005  # 5mΩ (ai3 shunt resistor)
    
    print("🔧 Configuration:")
    print(f"   → Device: {device_name}")
    print(f"   → Channel: {channel}")
    print(f"   → Shunt Resistor: {shunt_r} Ω (External)")
    print(f"   → Sample Rate: 30000 Hz (30kHz)")
    print(f"   → Duration: 10 seconds")
    print(f"   → Compression: 30:1")
    print()
    
    # Test 1: Current Mode with External Shunt
    print("=" * 80)
    print("🧪 Test 1: Current Mode with External Shunt")
    print("=" * 80)
    
    try:
        with nidaqmx.Task() as task:
            # Create Current Channel (similar to Manual tool)
            print(f"Creating Current Channel: {device_name}/{channel}")
            print(f"  → Mode: CURRENT (DAQmxCreateAICurrentChan)")
            print(f"  → Range: ±0.1 A (±100 mA)")
            print(f"  → Shunt Location: EXTERNAL")
            print(f"  → Shunt Value: {shunt_r} Ω")
            print()
            
            task.ai_channels.add_ai_current_chan(
                f"{device_name}/{channel}",
                name_to_assign_to_channel=f"Current_{channel}",
                terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
                min_val=-0.1,  # ±100 mA
                max_val=0.1,
                units=CurrentUnits.AMPS,
                shunt_resistor_loc=CurrentShuntResistorLocation.EXTERNAL,
                ext_shunt_resistor_val=shunt_r
            )
            print("✅ Current channel created successfully")
            
            # Configure timing
            sample_rate = 30000.0
            duration = 10.0
            samples_per_channel = int(sample_rate * duration)
            
            print(f"Configuring timing:")
            print(f"  → Sample Rate: {sample_rate} Hz")
            print(f"  → Duration: {duration} seconds")
            print(f"  → Total Samples: {samples_per_channel}")
            print()
            
            task.timing.cfg_samp_clk_timing(
                rate=sample_rate,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=samples_per_channel
            )
            
            # Read data
            print(f"📊 Reading {samples_per_channel} samples...")
            raw_data = task.read(number_of_samples_per_channel=samples_per_channel)
            print(f"✅ Read {len(raw_data)} samples")
            print()
            
            # Compress data (30:1)
            compress_ratio = 30
            compressed_data = []
            for i in range(0, len(raw_data), compress_ratio):
                chunk = raw_data[i:i+compress_ratio]
                if chunk:
                    avg = sum(chunk) / len(chunk)
                    compressed_data.append(avg)
            
            print(f"Compressed {len(raw_data)} → {len(compressed_data)} samples (30:1)")
            print()
            
            # Convert to mA
            current_ma = [i * 1000.0 for i in compressed_data]
            
            # Calculate statistics
            avg_ma = sum(current_ma) / len(current_ma)
            max_ma = max(current_ma)
            min_ma = min(current_ma)
            
            print("=" * 80)
            print("📊 Results (Current Mode)")
            print("=" * 80)
            print(f"   → Average Current: {avg_ma:.3f} mA")
            print(f"   → Max Current: {max_ma:.3f} mA")
            print(f"   → Min Current: {min_ma:.3f} mA")
            print()
            
            # Compare with Manual
            manual_avg = 1.018  # mA
            manual_max = 29.59  # mA
            manual_min = -1.513  # mA
            
            avg_ratio = avg_ma / manual_avg if manual_avg != 0 else 0
            max_ratio = max_ma / manual_max if manual_max != 0 else 0
            min_ratio = min_ma / manual_min if manual_min != 0 else 0
            
            print("📈 Comparison with Manual:")
            print(f"   → Average: {avg_ma:.3f} mA vs {manual_avg:.3f} mA (Manual)")
            print(f"   → Ratio: {avg_ratio:.3f}x")
            print()
            print(f"   → Max: {max_ma:.3f} mA vs {manual_max:.3f} mA (Manual)")
            print(f"   → Ratio: {max_ratio:.3f}x")
            print()
            print(f"   → Min: {min_ma:.3f} mA vs {manual_min:.3f} mA (Manual)")
            print(f"   → Ratio: {min_ratio:.3f}x")
            print()
            
            # Evaluate match
            avg_error = abs(avg_ratio - 1.0)
            if avg_error < 0.1:
                print("   ✅ EXCELLENT MATCH! (within 10%)")
                print("   → Current Mode is the solution!")
            elif avg_error < 0.3:
                print("   ✓ Good match (within 30%)")
            else:
                print(f"   ✗ Still different (ratio: {avg_ratio:.3f}x)")
            print()
            
    except Exception as e:
        print(f"❌ Current Mode Test Failed: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    # Test 2: Voltage Mode with DIFFERENTIAL (for comparison)
    print("=" * 80)
    print("🧪 Test 2: Voltage Mode with DIFFERENTIAL (current method)")
    print("=" * 80)
    
    try:
        with nidaqmx.Task() as task:
            print(f"Creating Voltage Channel: {device_name}/{channel}")
            print(f"  → Mode: VOLTAGE (DAQmxCreateAIVoltageChan)")
            print(f"  → Terminal Config: DEFAULT")
            print(f"  → Range: ±5V")
            print()
            
            task.ai_channels.add_ai_voltage_chan(
                f"{device_name}/{channel}",
                terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
                min_val=-5.0,
                max_val=5.0,
                units=nidaqmx.constants.VoltageUnits.VOLTS
            )
            print("✅ Voltage channel created successfully")
            
            # Configure timing
            sample_rate = 30000.0
            duration = 10.0
            samples_per_channel = int(sample_rate * duration)
            
            task.timing.cfg_samp_clk_timing(
                rate=sample_rate,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=samples_per_channel
            )
            
            # Read data
            print(f"📊 Reading {samples_per_channel} samples...")
            raw_data = task.read(number_of_samples_per_channel=samples_per_channel)
            print(f"✅ Read {len(raw_data)} samples")
            print()
            
            # Compress data (30:1)
            compress_ratio = 30
            compressed_volts = []
            for i in range(0, len(raw_data), compress_ratio):
                chunk = raw_data[i:i+compress_ratio]
                if chunk:
                    avg = sum(chunk) / len(chunk)
                    compressed_volts.append(avg)
            
            print(f"Compressed {len(raw_data)} → {len(compressed_volts)} samples (30:1)")
            print()
            
            # Convert to current (manual calculation)
            current_ma = [(v / shunt_r) * 1000.0 for v in compressed_volts]
            
            # Calculate statistics
            avg_v = sum(compressed_volts) / len(compressed_volts)
            avg_ma = sum(current_ma) / len(current_ma)
            max_ma = max(current_ma)
            min_ma = min(current_ma)
            
            print("=" * 80)
            print("📊 Results (Voltage Mode)")
            print("=" * 80)
            print(f"   → Average Voltage: {avg_v*1000:.6f} mV")
            print(f"   → Average Current: {avg_ma:.3f} mA (calculated: V/{shunt_r}Ω)")
            print(f"   → Max Current: {max_ma:.3f} mA")
            print(f"   → Min Current: {min_ma:.3f} mA")
            print()
            
            # Compare with Manual
            manual_avg = 1.018  # mA
            avg_ratio = avg_ma / manual_avg if manual_avg != 0 else 0
            
            print("📈 Comparison with Manual:")
            print(f"   → Average: {avg_ma:.3f} mA vs {manual_avg:.3f} mA (Manual)")
            print(f"   → Ratio: {avg_ratio:.3f}x")
            print()
            
    except Exception as e:
        print(f"❌ Voltage Mode Test Failed: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("=" * 80)
    print("✅ Test completed")
    print("=" * 80)

if __name__ == "__main__":
    test_current_mode()
