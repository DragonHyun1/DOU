#!/usr/bin/env python3
"""Test different Range settings to find optimal configuration"""

import sys
import os
sys.path.append('/workspace')

try:
    import nidaqmx
    from nidaqmx.constants import TerminalConfiguration, VoltageUnits
    NI_AVAILABLE = True
except:
    NI_AVAILABLE = False
    print("NI-DAQmx not available")
    sys.exit(1)

def test_range(device_name, channel, min_val, max_val, test_name):
    """Test a specific voltage range configuration"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"  Device: {device_name}/{channel}")
    print(f"  Range: {min_val}V to {max_val}V")
    print(f"{'='*60}")
    
    try:
        with nidaqmx.Task() as task:
            # Add channel with specified range
            task.ai_channels.add_ai_voltage_chan(
                f"{device_name}/{channel}",
                terminal_config=TerminalConfiguration.DEFAULT,
                min_val=min_val,
                max_val=max_val,
                units=VoltageUnits.VOLTS
            )
            
            # Read 100 samples
            samples = []
            for i in range(100):
                voltage = task.read()
                samples.append(voltage)
            
            # Calculate statistics
            avg_v = sum(samples) / len(samples)
            min_v = min(samples)
            max_v = max(samples)
            
            print(f"\n  Results (100 samples):")
            print(f"    Avg:   {avg_v:.9f}V ({avg_v*1000:.6f}mV)")
            print(f"    Min:   {min_v:.9f}V ({min_v*1000:.6f}mV)")
            print(f"    Max:   {max_v:.9f}V ({max_v*1000:.6f}mV)")
            print(f"    Range: {(max_v-min_v)*1000:.6f}mV")
            
            # Calculate current with different shunt values
            print(f"\n  Calculated Current:")
            for shunt_r in [0.01, 0.032]:
                current_ma = (avg_v / shunt_r) * 1000
                print(f"    Shunt {shunt_r}Ω: {current_ma:.3f}mA")
            
            return {
                'success': True,
                'avg_voltage': avg_v,
                'min_voltage': min_v,
                'max_voltage': max_v,
                'samples': samples
            }
            
    except Exception as e:
        print(f"\n  ERROR: {type(e).__name__}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def main():
    """Run range optimization tests"""
    print("\n" + "="*60)
    print("NI-DAQmx Range Optimization Test")
    print("="*60)
    
    # Device configuration
    device_name = "Dev1"  # Change if needed
    channel = "ai0"       # VBAT channel
    
    # Test different ranges
    test_configs = [
        # Current configuration
        (-0.2, 0.2, "Current Config (±200mV)"),
        
        # Smaller ranges (better resolution for small signals)
        (-0.05, 0.05, "±50mV (optimized for <0.013mV signal)"),
        (-0.01, 0.01, "±10mV (maximum resolution)"),
        (-0.001, 0.001, "±1mV (if supported)"),
        
        # Larger ranges (for comparison)
        (-0.5, 0.5, "±500mV"),
        (-1.0, 1.0, "±1V"),
        (-5.0, 5.0, "±5V (RSE fallback range)"),
    ]
    
    results = []
    for min_val, max_val, test_name in test_configs:
        result = test_range(device_name, channel, min_val, max_val, test_name)
        results.append({
            'name': test_name,
            'range': (min_val, max_val),
            'result': result
        })
    
    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for test in results:
        if test['result']['success']:
            avg_v = test['result']['avg_voltage']
            print(f"\n{test['name']}:")
            print(f"  Voltage: {avg_v*1000:.6f}mV")
            print(f"  Current (0.01Ω):  {(avg_v/0.01)*1000:.3f}mA")
            print(f"  Current (0.032Ω): {(avg_v/0.032)*1000:.3f}mA")
        else:
            print(f"\n{test['name']}: FAILED")
            print(f"  Error: {test['result']['error']}")
    
    print(f"\n{'='*60}")
    print("RECOMMENDATION")
    print(f"{'='*60}")
    print("""
Based on results:
1. If 0.013mV signal is real, use smallest range that works
2. Smaller range = better ADC resolution
3. Compare calculated current with Manual tool (0.409mA)
4. Check if voltage changes with different ranges
    """)

if __name__ == '__main__':
    main()
