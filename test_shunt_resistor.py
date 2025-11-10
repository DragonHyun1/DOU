#!/usr/bin/env python3
"""
Shunt Resistor Test Script for ai3 channel

Tests different shunt resistor values to find the correct one.
Compares with Manual measurement: ai3 = 1.018mA

Usage:
    python test_shunt_resistor.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ni_daq import NIDAQService
from PyQt6.QtCore import QCoreApplication

def test_shunt_values():
    """Test ai3 with different shunt resistor values"""
    
    print("=" * 80)
    print("🔬 Shunt Resistor Test for ai3 Channel")
    print("=" * 80)
    print()
    print("📌 Manual Measurement Reference:")
    print("   → ai3 Average Current: 1.018 mA")
    print("   → ai3 Max Current: 29.59 mA")
    print("   → ai3 Min Current: -1.513 mA")
    print()
    print("=" * 80)
    print()
    
    # Initialize QCoreApplication (required for QObject)
    app = QCoreApplication(sys.argv)
    
    # Create NI DAQ Service
    daq_service = NIDAQService()
    
    # Connect to device
    print("🔌 Connecting to NI DAQ device...")
    if not daq_service.connect():
        print("❌ Failed to connect to DAQ device!")
        return
    
    print("✅ Connected to DAQ device")
    print()
    
    # Test shunt resistor values
    test_values = [0.001, 0.01, 0.1, 1.0]  # Ohms
    
    print("🧪 Testing different shunt resistor values...")
    print()
    
    results = []
    
    for shunt_r in test_values:
        print(f"{'=' * 80}")
        print(f"🔧 Testing with Shunt Resistor = {shunt_r} Ω")
        print(f"{'=' * 80}")
        
        # Update channel config with new shunt value
        daq_service.channel_configs['ai3'] = {
            'name': 'VDD_WIFI_1P0',
            'shunt_r': shunt_r,
            'enabled': True
        }
        
        # Measure using hardware-timed collection (same as Phone App scenario)
        result = daq_service.read_current_channels_hardware_timed(
            channels=['ai3'],
            sample_rate=30000.0,  # 30kHz (same as Phone App)
            compress_ratio=30,    # 30:1 compression
            duration_seconds=10.0  # 10 seconds
        )
        
        if result and 'ai3' in result:
            channel_data = result['ai3']
            current_data = channel_data.get('current_data', [])
            
            if current_data:
                avg_current_ma = sum(current_data) / len(current_data)
                max_current_ma = max(current_data)
                min_current_ma = min(current_data)
                
                # Calculate voltage from current (reverse calculation)
                avg_voltage_mv = avg_current_ma * shunt_r
                
                print()
                print(f"📊 Results with Shunt = {shunt_r} Ω:")
                print(f"   → Average Current: {avg_current_ma:.3f} mA")
                print(f"   → Max Current: {max_current_ma:.3f} mA")
                print(f"   → Min Current: {min_current_ma:.3f} mA")
                print(f"   → Measured Voltage: {avg_voltage_mv:.6f} mV (calculated from I×R)")
                print()
                
                # Compare with Manual measurement
                manual_avg = 1.018  # mA
                manual_max = 29.59  # mA
                manual_min = -1.513  # mA
                
                avg_ratio = avg_current_ma / manual_avg if manual_avg != 0 else 0
                max_ratio = max_current_ma / manual_max if manual_max != 0 else 0
                min_ratio = min_current_ma / manual_min if manual_min != 0 else 0
                
                print(f"📈 Comparison with Manual (1.018 mA):")
                print(f"   → Average Ratio: {avg_ratio:.3f}x (DoU/Manual)")
                print(f"   → Max Ratio: {max_ratio:.3f}x (DoU/Manual)")
                print(f"   → Min Ratio: {min_ratio:.3f}x (DoU/Manual)")
                
                # Score the match (closer to 1.0 is better)
                avg_error = abs(avg_ratio - 1.0)
                max_error = abs(max_ratio - 1.0)
                min_error = abs(min_ratio - 1.0)
                total_error = avg_error + max_error + min_error
                
                print(f"   → Total Error: {total_error:.3f} (lower is better)")
                
                if avg_error < 0.1:  # Within 10%
                    print(f"   ✅ EXCELLENT MATCH! (within 10%)")
                elif avg_error < 0.3:  # Within 30%
                    print(f"   ✓ Good match (within 30%)")
                else:
                    print(f"   ✗ Poor match (off by {avg_error*100:.1f}%)")
                
                print()
                
                results.append({
                    'shunt_r': shunt_r,
                    'avg_current_ma': avg_current_ma,
                    'max_current_ma': max_current_ma,
                    'min_current_ma': min_current_ma,
                    'avg_ratio': avg_ratio,
                    'total_error': total_error,
                    'avg_voltage_mv': avg_voltage_mv
                })
            else:
                print(f"❌ No current data received")
        else:
            print(f"❌ Measurement failed for shunt = {shunt_r} Ω")
        
        print()
    
    # Summary
    print("=" * 80)
    print("📋 SUMMARY - Best Shunt Resistor Value")
    print("=" * 80)
    print()
    
    if results:
        # Sort by total error (ascending)
        results.sort(key=lambda x: x['total_error'])
        
        print(f"{'Shunt (Ω)':<12} {'Avg (mA)':<12} {'Max (mA)':<12} {'Min (mA)':<12} {'Ratio':<8} {'Error':<8} {'Match':<10}")
        print("-" * 80)
        
        for i, r in enumerate(results):
            match_symbol = "⭐" if i == 0 else "✓" if i == 1 else ""
            match_text = "BEST" if i == 0 else "Good" if i == 1 else ""
            
            print(f"{r['shunt_r']:<12.4f} "
                  f"{r['avg_current_ma']:<12.3f} "
                  f"{r['max_current_ma']:<12.3f} "
                  f"{r['min_current_ma']:<12.3f} "
                  f"{r['avg_ratio']:<8.3f} "
                  f"{r['total_error']:<8.3f} "
                  f"{match_symbol} {match_text}")
        
        print()
        print("=" * 80)
        best = results[0]
        print(f"🎯 RECOMMENDED SHUNT RESISTOR VALUE: {best['shunt_r']} Ω")
        print(f"   → Measured Avg Voltage: {best['avg_voltage_mv']:.6f} mV")
        print(f"   → Calculated Current: {best['avg_current_ma']:.3f} mA")
        print(f"   → Match Ratio: {best['avg_ratio']:.3f}x")
        print(f"   → Total Error: {best['total_error']:.3f}")
        print("=" * 80)
    else:
        print("❌ No successful measurements")
    
    # Disconnect
    daq_service.disconnect()
    print()
    print("✅ Test completed")

if __name__ == "__main__":
    test_shunt_values()
