#!/usr/bin/env python3
"""
Test different ways to enable DIFFERENTIAL mode

Tests:
1. Check available TerminalConfiguration enum values
2. Try different methods to use DIFFERENTIAL
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nidaqmx
from nidaqmx.constants import TerminalConfiguration

print("=" * 80)
print("🔍 Checking TerminalConfiguration Enum Values")
print("=" * 80)
print()

# List all available enum values
print("Available TerminalConfiguration values:")
for attr in dir(TerminalConfiguration):
    if not attr.startswith('_'):
        try:
            value = getattr(TerminalConfiguration, attr)
            print(f"  → {attr}: {value}")
        except:
            pass

print()
print("=" * 80)
print("🧪 Testing DIFFERENTIAL Mode Methods")
print("=" * 80)
print()

device_name = "Dev1"
channel = "ai3"

# Method 1: Try creating task with available enum values
methods_to_try = []

# Check if DIFFERENTIAL exists
if hasattr(TerminalConfiguration, 'DIFFERENTIAL'):
    methods_to_try.append(("DIFFERENTIAL", TerminalConfiguration.DIFFERENTIAL))
elif hasattr(TerminalConfiguration, 'Diff'):
    methods_to_try.append(("Diff", TerminalConfiguration.Diff))
elif hasattr(TerminalConfiguration, 'DIFF'):
    methods_to_try.append(("DIFF", TerminalConfiguration.DIFF))

# Add DEFAULT as reference
if hasattr(TerminalConfiguration, 'DEFAULT'):
    methods_to_try.append(("DEFAULT", TerminalConfiguration.DEFAULT))

# Add RSE as reference
if hasattr(TerminalConfiguration, 'RSE'):
    methods_to_try.append(("RSE", TerminalConfiguration.RSE))

print(f"Methods to test: {len(methods_to_try)}")
for name, value in methods_to_try:
    print(f"  → {name}: {value} (type: {type(value).__name__})")

print()

# Test each method
for method_name, method_value in methods_to_try:
    print(f"{'=' * 80}")
    print(f"Testing: {method_name}")
    print(f"{'=' * 80}")
    
    try:
        with nidaqmx.Task() as task:
            print(f"Creating channel with {method_name}...")
            task.ai_channels.add_ai_voltage_chan(
                f"{device_name}/{channel}",
                terminal_config=method_value,
                min_val=-5.0,
                max_val=5.0,
                units=nidaqmx.constants.VoltageUnits.VOLTS
            )
            
            task.timing.cfg_samp_clk_timing(
                rate=1000.0,
                sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                samps_per_chan=100
            )
            
            print(f"Reading samples...")
            data = task.read(number_of_samples_per_channel=100)
            
            avg = sum(data) / len(data)
            print(f"✅ {method_name} works!")
            print(f"   → Average voltage: {avg*1000:.3f} mV")
            print()
            
    except Exception as e:
        print(f"❌ {method_name} failed: {e}")
        print()

print("=" * 80)
print("✅ Test completed")
print("=" * 80)
