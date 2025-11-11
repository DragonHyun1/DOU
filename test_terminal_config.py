#!/usr/bin/env python3
"""
Terminal Configuration Test Script

Tests ai3 with different terminal configurations to match Manual tool.
Manual uses RSE mode (terminalConfig = -1).

Usage:
    python test_terminal_config.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration

def test_terminal_configs():
    """Test ai3 with different terminal configurations and voltage ranges"""
    
    print("=" * 80)
    print("🔬 Terminal Configuration & Voltage Range Test for ai3 Channel")
    print("=" * 80)
    print()
    print("📌 Manual Configuration (from NI Trace):")
    print("   → Terminal Config: -1 (RSE)")
    print("   → Voltage Range: ±5V")
    print("   → Sample Rate: 30,000 Hz")
    print("   → Sample Mode: Continuous")
    print("   → Samples Per Chan: 1,000")
    print()
    print("📌 Manual Measurement Result:")
    print("   → ai3 Voltage: 1.05V (Rail voltage)")
    print("   → ai3 Current: 1.018 mA")
    print()
    print("📌 DoU Current Configuration:")
    print("   → Terminal Config: DEFAULT")
    print("   → Voltage Range: ±5V")
    print("   → Measured Voltage: 0.033mV (Shunt drop)")
    print("   → Calculated Current: 6.533 mA (6.42x higher)")
    print()
    print("🔍 Test Objectives:")
    print("   1. Voltage Range: Test ±5V vs ±10V")
    print("   2. Current Calculation: Test Average vs Cumulative")
    print()
    print("=" * 80)
    print()
    
    # Test configuration
    device_name = "Dev1"
    channel = "ai3"
    shunt_r = 0.005  # 5mΩ
    
    # Test different terminal configurations
    configs_to_test = [
        ("RSE", TerminalConfiguration.RSE),
        ("NRSE", TerminalConfiguration.NRSE),
        ("DIFFERENTIAL", TerminalConfiguration.DIFFERENTIAL),
        ("DEFAULT", TerminalConfiguration.DEFAULT),
    ]
    
    # Test different voltage ranges
    voltage_ranges = [
        ("±5V", -5.0, 5.0),
        ("±10V", -10.0, 10.0),
    ]
    
    results = []
    
    for config_name, config_value in configs_to_test:
        for range_name, min_val, max_val in voltage_ranges:
            print(f"{'=' * 80}")
            print(f"🧪 Testing: {config_name} + {range_name}")
            print(f"{'=' * 80}")
            
            try:
                with nidaqmx.Task() as task:
                    # Create voltage channel with specific terminal config and voltage range
                    print(f"Creating channel: {device_name}/{channel}")
                    print(f"  → Terminal Config: {config_name}")
                    print(f"  → Voltage Range: {range_name} ({min_val}V to {max_val}V)")
                    print()
                    
                    task.ai_channels.add_ai_voltage_chan(
                        f"{device_name}/{channel}",
                        terminal_config=config_value,
                        min_val=min_val,
                        max_val=max_val,
                        units=nidaqmx.constants.VoltageUnits.VOLTS
                    )
                
                # Configure timing (match Manual's settings as close as possible)
                sample_rate = 30000.0
                samples_per_channel = 1000  # Same as Manual
                
                task.timing.cfg_samp_clk_timing(
                    rate=sample_rate,
                    sample_mode=AcquisitionType.FINITE,  # Use FINITE for testing
                    samps_per_chan=samples_per_channel
                )
                
                # Read data
                print(f"📊 Reading {samples_per_channel} samples at {sample_rate} Hz...")
                data = task.read(number_of_samples_per_channel=samples_per_channel)
                
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
                
                print(f"📊 Voltage Results ({config_name} + {range_name}):")
                print(f"   → Average: {avg_voltage:.6f} V ({avg_voltage_mv:.3f} mV)")
                print(f"   → Max: {max_voltage:.6f} V ({max_voltage_mv:.3f} mV)")
                print(f"   → Min: {min_voltage:.6f} V ({min_voltage_mv:.3f} mV)")
                print()
                
                # Calculate current - TWO METHODS
                # Method 1: Average Current (현재 DoU 방식)
                avg_current_ma = (avg_voltage / shunt_r) * 1000.0
                max_current_ma = (max_voltage / shunt_r) * 1000.0
                min_current_ma = (min_voltage / shunt_r) * 1000.0
                
                # Method 2: Cumulative Current (누적 방식)
                # 각 샘플의 전류를 계산한 후 합산
                currents_ma = [(v / shunt_r) * 1000.0 for v in data]
                cumulative_current_ma = sum(currents_ma)
                avg_from_cumulative_ma = cumulative_current_ma / len(currents_ma)
                
                print(f"📊 Current Calculation Method 1: AVERAGE (평균 전류)")
                print(f"   → Method: (Avg_Voltage / Shunt_R) × 1000")
                print(f"   → Average Current: {avg_current_ma:.3f} mA")
                print(f"   → Max Current: {max_current_ma:.3f} mA")
                print(f"   → Min Current: {min_current_ma:.3f} mA")
                print()
                
                print(f"📊 Current Calculation Method 2: CUMULATIVE (누적 전류)")
                print(f"   → Method: Sum(Each_Sample / Shunt_R) / Num_Samples")
                print(f"   → Cumulative Sum: {cumulative_current_ma:.3f} mA·samples")
                print(f"   → Average from Cumulative: {avg_from_cumulative_ma:.3f} mA")
                print(f"   → Difference: {abs(avg_current_ma - avg_from_cumulative_ma):.6f} mA")
                print()
                
                # Note: These two methods should give identical results
                if abs(avg_current_ma - avg_from_cumulative_ma) < 0.001:
                    print(f"   ✅ Both methods give same result (as expected)")
                else:
                    print(f"   ⚠️  Methods differ (unexpected!)")
                print()
                
                # Compare with Manual
                manual_voltage = 1.05  # V (Rail voltage)
                manual_current = 1.018  # mA
                
                voltage_ratio = abs(avg_voltage) / manual_voltage if manual_voltage != 0 else 0
                current_ratio_method1 = abs(avg_current_ma) / manual_current if manual_current != 0 else 0
                current_ratio_method2 = abs(avg_from_cumulative_ma) / manual_current if manual_current != 0 else 0
                
                print(f"📈 Comparison with Manual:")
                print(f"   → Voltage: {abs(avg_voltage):.6f} V vs {manual_voltage:.2f} V (Manual)")
                print(f"   → Voltage Ratio: {voltage_ratio:.6f}x")
                print()
                print(f"   → Current (Method 1): {abs(avg_current_ma):.3f} mA vs {manual_current:.3f} mA (Manual)")
                print(f"   → Current Ratio: {current_ratio_method1:.3f}x")
                print()
                print(f"   → Current (Method 2): {abs(avg_from_cumulative_ma):.3f} mA vs {manual_current:.3f} mA (Manual)")
                print(f"   → Current Ratio: {current_ratio_method2:.3f}x")
                print()
                
                # Determine what's being measured
                if abs(avg_voltage) > 0.5:  # > 500mV
                    measurement_type = "Rail Voltage"
                    print(f"   🔍 Measurement Type: {measurement_type}")
                    print(f"   → This measures the power rail voltage (like Manual!)")
                elif abs(avg_voltage_mv) > 0.01:  # > 0.01mV
                    measurement_type = "Shunt Drop"
                    print(f"   🔍 Measurement Type: {measurement_type}")
                    print(f"   → This measures voltage drop across shunt")
                else:
                    measurement_type = "Near Zero"
                    print(f"   🔍 Measurement Type: {measurement_type}")
                print()
                
                # Evaluate match
                if measurement_type == "Rail Voltage":
                    if voltage_ratio > 0.9 and voltage_ratio < 1.1:
                        print(f"   ✅ VOLTAGE MATCHES MANUAL! ({config_name} + {range_name} is correct)")
                    else:
                        print(f"   ⚠️  Rail voltage but different magnitude")
                
                if current_ratio_method1 > 0.9 and current_ratio_method1 < 1.1:
                    print(f"   ✅ CURRENT MATCHES MANUAL! ({config_name} + {range_name} is correct)")
                elif current_ratio_method1 > 0.8 and current_ratio_method1 < 1.2:
                    print(f"   ✓ Close match (within 20%)")
                else:
                    print(f"   ✗ Current mismatch (ratio: {current_ratio_method1:.3f}x)")
                
                print()
                
                results.append({
                    'config': config_name,
                    'range': range_name,
                    'avg_voltage': avg_voltage,
                    'avg_voltage_mv': avg_voltage_mv,
                    'avg_current_ma': avg_current_ma,
                    'cumulative_current_ma': avg_from_cumulative_ma,
                    'voltage_ratio': voltage_ratio,
                    'current_ratio': current_ratio_method1,
                    'measurement_type': measurement_type
                })
                
            except Exception as e:
                print(f"   ❌ {config_name} + {range_name} failed: {e}")
                print()
    
    # Summary
    print("=" * 80)
    print("📋 SUMMARY - Terminal Configuration & Voltage Range Comparison")
    print("=" * 80)
    print()
    
    if results:
        print(f"{'Config':<12} {'Range':<8} {'Voltage':<12} {'Current':<12} {'Type':<15} {'Match':<10}")
        print("-" * 85)
        
        for r in results:
            match_symbol = ""
            if r['current_ratio'] > 0.9 and r['current_ratio'] < 1.1:
                match_symbol = "⭐ BEST"
            elif r['current_ratio'] > 0.8 and r['current_ratio'] < 1.2:
                match_symbol = "✓ Good"
            
            print(f"{r['config']:<12} "
                  f"{r['range']:<8} "
                  f"{abs(r['avg_voltage_mv']):>10.3f}mV "
                  f"{abs(r['avg_current_ma']):>10.3f}mA "
                  f"{r['measurement_type']:<15} "
                  f"{match_symbol}")
        
        print()
        print("=" * 85)
        
        # Find best match
        best = min(results, key=lambda x: abs(x['current_ratio'] - 1.0))
        
        print(f"🎯 RECOMMENDED CONFIGURATION:")
        print(f"   → Terminal Config: {best['config']}")
        print(f"   → Voltage Range: {best['range']}")
        print(f"   → Measured Voltage: {abs(best['avg_voltage_mv']):.3f} mV")
        print(f"   → Calculated Current: {abs(best['avg_current_ma']):.3f} mA")
        print(f"   → Current Ratio: {best['current_ratio']:.3f}x (vs Manual)")
        print(f"   → Measurement Type: {best['measurement_type']}")
        print()
        print(f"📝 Note on Current Calculation:")
        print(f"   → Method 1 (Average): (Avg_Voltage / R) - 현재 DoU 방식")
        print(f"   → Method 2 (Cumulative): Sum(V[i]/R) / N - 동일한 결과")
        print(f"   → Both methods are mathematically equivalent")
        print("=" * 85)
    else:
        print("❌ No successful measurements")
    
    print()
    print("✅ Test completed")

if __name__ == "__main__":
    test_terminal_configs()
