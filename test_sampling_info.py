#!/usr/bin/env python3
"""
Sampling Information Test Script

Shows detailed sampling configuration and calculates samples per millisecond.

Usage:
    python test_sampling_info.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nidaqmx
from nidaqmx.constants import AcquisitionType

def test_sampling_info():
    """Test and display sampling information"""
    
    print("=" * 80)
    print("📊 Sampling Information Test")
    print("=" * 80)
    print()
    
    # Test configuration
    device_name = "Dev1"
    channel = "ai3"
    
    # Different sample rates to test
    test_rates = [1000, 10000, 30000, 100000, 250000, 500000]
    
    print("🔍 Testing different sampling rates...")
    print()
    
    for sample_rate in test_rates:
        print(f"{'=' * 80}")
        print(f"🧪 Testing Sample Rate: {sample_rate:,} Hz ({sample_rate/1000:.1f} kHz)")
        print(f"{'=' * 80}")
        
        try:
            with nidaqmx.Task() as task:
                # Create voltage channel
                task.ai_channels.add_ai_voltage_chan(
                    f"{device_name}/{channel}",
                    terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
                    min_val=-5.0,
                    max_val=5.0,
                    units=nidaqmx.constants.VoltageUnits.VOLTS
                )
                
                # Configure timing
                samples_per_channel = sample_rate  # 1 second worth
                task.timing.cfg_samp_clk_timing(
                    rate=sample_rate,
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=samples_per_channel
                )
                
                # Get actual configured rate (may differ from requested)
                actual_rate = task.timing.samp_clk_rate
                
                # Calculate samples per millisecond
                samples_per_ms = actual_rate / 1000.0
                
                print(f"📊 Sampling Configuration:")
                print(f"   → Requested Rate: {sample_rate:,} Hz")
                print(f"   → Actual Rate: {actual_rate:,.2f} Hz")
                print(f"   → Samples per 1ms: {samples_per_ms:.2f} samples")
                print(f"   → Time per sample: {(1/actual_rate)*1000:.6f} ms")
                print()
                
                # Calculate for different time intervals
                print(f"📏 Sample counts for different intervals:")
                intervals = [0.001, 0.01, 0.1, 1.0, 10.0]  # seconds
                for interval in intervals:
                    samples = actual_rate * interval
                    print(f"   → {interval*1000:>7.1f} ms ({interval:>5.3f} sec): {samples:>12,.0f} samples")
                
                print()
                
                # Check if rate is achievable
                if abs(actual_rate - sample_rate) > 1:
                    print(f"   ⚠️  Note: Actual rate differs from requested rate")
                    print(f"   → Difference: {abs(actual_rate - sample_rate):.2f} Hz")
                else:
                    print(f"   ✅ Rate achieved successfully")
                
                print()
                
        except Exception as e:
            print(f"   ❌ Failed to configure {sample_rate} Hz: {e}")
            print()
    
    print("=" * 80)
    print("📋 Current DoU Configuration (Phone App Scenario)")
    print("=" * 80)
    print()
    
    # Show current DoU configuration from ni_daq.py
    current_config = {
        'sample_rate': 30000.0,  # Hz
        'duration': 10.0,  # seconds
        'compress_ratio': 30,  # 30:1
        'channels': ['ai0', 'ai1', 'ai2', 'ai3', 'ai4', 'ai5']
    }
    
    rate = current_config['sample_rate']
    duration = current_config['duration']
    compress_ratio = current_config['compress_ratio']
    num_channels = len(current_config['channels'])
    
    raw_samples_per_channel = int(rate * duration)
    compressed_samples_per_channel = raw_samples_per_channel // compress_ratio
    
    samples_per_ms = rate / 1000.0
    compressed_per_ms = samples_per_ms / compress_ratio
    
    print(f"🔧 Configuration:")
    print(f"   → Sample Rate: {rate:,} Hz ({rate/1000:.1f} kHz)")
    print(f"   → Duration: {duration} seconds")
    print(f"   → Channels: {num_channels}")
    print(f"   → Compression Ratio: {compress_ratio}:1")
    print()
    
    print(f"📊 Raw Sampling (before compression):")
    print(f"   → Samples per 1ms: {samples_per_ms:.1f} samples")
    print(f"   → Samples per channel: {raw_samples_per_channel:,} samples")
    print(f"   → Total samples (all channels): {raw_samples_per_channel * num_channels:,} samples")
    print(f"   → Memory per channel: {raw_samples_per_channel * 8:,} bytes ({raw_samples_per_channel * 8 / 1024:.1f} KB)")
    print()
    
    print(f"📦 After Compression ({compress_ratio}:1):")
    print(f"   → Compressed samples per 1ms: {compressed_per_ms:.2f} samples")
    print(f"   → Compressed samples per channel: {compressed_samples_per_channel:,} samples")
    print(f"   → Total compressed (all channels): {compressed_samples_per_channel * num_channels:,} samples")
    print(f"   → Memory per channel: {compressed_samples_per_channel * 8:,} bytes ({compressed_samples_per_channel * 8 / 1024:.1f} KB)")
    print()
    
    print(f"⏱️  Time Resolution:")
    print(f"   → Raw: {1000.0/rate:.6f} ms per sample ({1000000.0/rate:.3f} µs)")
    print(f"   → Compressed: {compress_ratio * 1000.0/rate:.6f} ms per sample ({compress_ratio * 1000.0/rate * 1000:.3f} µs)")
    print()
    
    print(f"📈 Averaging:")
    print(f"   → Each compressed sample = average of {compress_ratio} raw samples")
    print(f"   → Reduces noise by factor of √{compress_ratio} ≈ {compress_ratio**0.5:.2f}x")
    print()
    
    # Calculate maximum sample rate for device
    print("=" * 80)
    print("🚀 Maximum Sampling Rate Test")
    print("=" * 80)
    print()
    
    try:
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan(
                f"{device_name}/{channel}",
                terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
                min_val=-5.0,
                max_val=5.0
            )
            
            # Get max rate from device
            max_rate = task.timing.samp_clk_max_rate
            
            print(f"📊 Device Maximum Sample Rate:")
            print(f"   → Max Rate: {max_rate:,.0f} Hz ({max_rate/1000:.1f} kHz)")
            print(f"   → Max samples per 1ms: {max_rate/1000:.1f} samples")
            print()
            
            # Compare with current rate
            utilization = (rate / max_rate) * 100
            print(f"📈 Current Utilization:")
            print(f"   → Current: {rate:,} Hz")
            print(f"   → Maximum: {max_rate:,.0f} Hz")
            print(f"   → Utilization: {utilization:.1f}%")
            print()
            
            if utilization < 50:
                print(f"   ✅ Safe operating range (< 50%)")
            elif utilization < 80:
                print(f"   ⚠️  Moderate load (50-80%)")
            else:
                print(f"   ⚠️  High load (> 80%) - consider reducing rate")
            
            print()
            
    except Exception as e:
        print(f"❌ Failed to get max rate: {e}")
        print()
    
    print("=" * 80)
    print("✅ Test completed")
    print("=" * 80)

if __name__ == "__main__":
    test_sampling_info()
