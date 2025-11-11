#!/usr/bin/env python3
"""
Voltage Range Test Script

Tests ai3 channel with different voltage ranges to see if measurement changes.

Usage:
    python test_voltage_range.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nidaqmx
from nidaqmx.constants import AcquisitionType

def test_voltage_ranges():
    """Test ai3 with different voltage ranges"""
    
    print("=" * 80)
    print("🔬 Voltage Range Test for ai3 Channel")
    print("=" * 80)
    print()
    print("📌 Purpose: Check if voltage range affects measured values")
    print()
    print("=" * 80)
    print()
    
    device_name = "Dev1"
    channel = "ai3"
    shunt_r = 0.005  # 5mΩ
    
    # Test different voltage ranges
    voltage_ranges = [
        ("±5V", -5.0, 5.0),
        ("±10V", -10.0, 10.0),
        ("±2V", -2.0, 2.0),
        ("±1V", -1.0, 1.0),
    ]
    
    results = []
    
    for range_name, min_val, max_val in voltage_ranges:
        print(f"{'=' * 80}")
        print(f"🧪 Testing: {range_name}")
        print(f"{'=' * 80}")
        
        try:
            with nidaqmx.Task() as task:
                print(f"Creating channel: {device_name}/{channel}")
                print(f"  → Voltage Range: {range_name} ({min_val}V to {max_val}V)")
                print()
                
                # Try DIFF mode (best for current measurement)
                try:
                    task.ai_channels.add_ai_voltage_chan(
                        f"{device_name}/{channel}",
                        terminal_config=nidaqmx.constants.TerminalConfiguration.DIFF,
                        min_val=min_val,
                        max_val=max_val,
                        units=nidaqmx.constants.VoltageUnits.VOLTS
                    )
                    terminal_mode = "DIFF"
                except:
                    # Fallback to DEFAULT
                    task.ai_channels.add_ai_voltage_chan(
                        f"{device_name}/{channel}",
                        terminal_config=nidaqmx.constants.TerminalConfiguration.DEFAULT,
                        min_val=min_val,
                        max_val=max_val,
                        units=nidaqmx.constants.VoltageUnits.VOLTS
                    )
                    terminal_mode = "DEFAULT"
                
                print(f"✅ Channel created (Terminal: {terminal_mode})")
                
                # Configure timing - Quick test (1000 samples at 10kHz)
                sample_rate = 10000.0
                samples = 1000
                
                task.timing.cfg_samp_clk_timing(
                    rate=sample_rate,
                    sample_mode=AcquisitionType.FINITE,
                    samps_per_chan=samples
                )
                
                # Read data
                print(f"📊 Reading {samples} samples at {sample_rate} Hz...")
                data = task.read(number_of_samples_per_channel=samples)
                
                # Calculate statistics
                avg_voltage = sum(data) / len(data)
                max_voltage = max(data)
                min_voltage = min(data)
                
                # Convert to mV
                avg_voltage_mv = avg_voltage * 1000.0
                max_voltage_mv = max_voltage * 1000.0
                min_voltage_mv = min_voltage * 1000.0
                
                print(f"✅ Read {len(data)} samples")
                print()
                
                print(f"📊 Voltage Results ({range_name}):")
                print(f"   → Average: {avg_voltage:.6f} V ({avg_voltage_mv:.6f} mV)")
                print(f"   → Max: {max_voltage:.6f} V ({max_voltage_mv:.6f} mV)")
                print(f"   → Min: {min_voltage:.6f} V ({min_voltage_mv:.6f} mV)")
                print()
                
                # Calculate current
                avg_current_ma = (avg_voltage / shunt_r) * 1000.0
                max_current_ma = (max_voltage / shunt_r) * 1000.0
                min_current_ma = (min_voltage / shunt_r) * 1000.0
                
                print(f"📊 Calculated Current ({range_name}):")
                print(f"   → Average: {avg_current_ma:.3f} mA")
                print(f"   → Max: {max_current_ma:.3f} mA")
                print(f"   → Min: {min_current_ma:.3f} mA")
                print()
                
                results.append({
                    'range': range_name,
                    'terminal_mode': terminal_mode,
                    'avg_voltage_mv': avg_voltage_mv,
                    'avg_current_ma': avg_current_ma,
                    'max_voltage_mv': max_voltage_mv,
                    'min_voltage_mv': min_voltage_mv
                })
                
        except Exception as e:
            print(f"   ❌ {range_name} failed: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    # Summary
    print("=" * 80)
    print("📋 SUMMARY - Voltage Range Comparison")
    print("=" * 80)
    print()
    
    if results:
        print(f"{'Range':<10} {'Mode':<10} {'Avg Voltage':<15} {'Avg Current':<15}")
        print("-" * 80)
        
        for r in results:
            print(f"{r['range']:<10} "
                  f"{r['terminal_mode']:<10} "
                  f"{r['avg_voltage_mv']:>13.6f} mV "
                  f"{r['avg_current_ma']:>13.3f} mA")
        
        print()
        print("=" * 80)
        
        # Check if results are consistent
        if len(results) >= 2:
            first_current = results[0]['avg_current_ma']
            all_similar = all(
                abs(r['avg_current_ma'] - first_current) / abs(first_current) < 0.01 
                for r in results[1:] if first_current != 0
            )
            
            if all_similar:
                print("✅ All voltage ranges produce similar current values (< 1% difference)")
                print("   → Voltage range does NOT affect measurement significantly")
            else:
                print("⚠️  Voltage ranges produce different current values")
                print("   → Voltage range DOES affect measurement!")
                print()
                print("   Differences from first measurement:")
                for r in results[1:]:
                    diff = r['avg_current_ma'] - first_current
                    ratio = r['avg_current_ma'] / first_current if first_current != 0 else 0
                    print(f"   → {r['range']}: {diff:+.3f} mA ({ratio:.3f}x)")
        
        print("=" * 80)
    else:
        print("❌ No successful measurements")
    
    print()
    print("✅ Test completed")

if __name__ == "__main__":
    test_voltage_ranges()
