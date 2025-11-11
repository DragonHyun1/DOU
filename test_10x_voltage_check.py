#!/usr/bin/env python3
"""
10배 차이 원인 확인 스크립트
- Raw voltage 값 확인
- 계산 과정 상세 출력
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nidaqmx
from nidaqmx.constants import AcquisitionType

def test_raw_voltage_measurement():
    """Raw voltage 측정하여 10배 문제 확인"""
    
    print("=" * 80)
    print("🔬 10배 차이 원인 확인 테스트")
    print("=" * 80)
    print()
    
    device_name = "Dev1"
    channel = "ai3"  # VDD_WIFI_1P0
    shunt_r = 0.005  # 5mΩ (사용자가 정확하게 입력했다고 함)
    
    print(f"📌 설정:")
    print(f"  - Channel: {channel}")
    print(f"  - Shunt Resistor: {shunt_r}Ω ({shunt_r*1000}mΩ)")
    print()
    
    # 다양한 voltage range로 테스트
    test_configs = [
        ("±0.1V (현재 설정)", -0.1, 0.1),
        ("±5V (Manual tool)", -5.0, 5.0),
    ]
    
    for config_name, min_val, max_val in test_configs:
        print("=" * 80)
        print(f"🧪 테스트: {config_name}")
        print("=" * 80)
        
        try:
            with nidaqmx.Task() as task:
                # DIFF 모드로 채널 추가 (현재 우리 툴)
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
                
                print(f"✅ Terminal mode: {terminal_mode}")
                
                # CONTINUOUS 모드로 샘플링 (현재 우리 툴)
                sample_rate = 30000.0
                samples = 1000
                
                task.timing.cfg_samp_clk_timing(
                    rate=sample_rate,
                    sample_mode=AcquisitionType.CONTINUOUS,
                    samps_per_chan=samples
                )
                
                # 데이터 읽기
                print(f"📊 Reading {samples} samples...")
                data = task.read(number_of_samples_per_channel=samples, timeout=5.0)
                
                # Raw voltage 통계
                avg_voltage_V = sum(data) / len(data)
                max_voltage_V = max(data)
                min_voltage_V = min(data)
                
                avg_voltage_mV = avg_voltage_V * 1000.0
                
                print(f"\n📊 Raw Voltage 측정:")
                print(f"  → Average: {avg_voltage_V:.9f} V ({avg_voltage_mV:.6f} mV)")
                print(f"  → Max: {max_voltage_V:.9f} V ({max_voltage_V*1000:.6f} mV)")
                print(f"  → Min: {min_voltage_V:.9f} V ({min_voltage_V*1000:.6f} mV)")
                
                # 전류 계산 (현재 방식)
                current_A = avg_voltage_V / shunt_r
                current_mA = current_A * 1000.0
                
                print(f"\n⚡ 전류 계산 (현재 방식):")
                print(f"  → I = V / R")
                print(f"  → I = {avg_voltage_V:.9f}V / {shunt_r}Ω")
                print(f"  → I = {current_A:.9f}A")
                print(f"  → I = {current_mA:.6f} mA")
                
                # 10으로 나눈 값
                current_mA_div10 = current_mA / 10.0
                print(f"\n🔟 10으로 나눈 값 (Manual과 비교):")
                print(f"  → I = {current_mA_div10:.6f} mA")
                print(f"  → 이 값이 Manual과 일치하나요?")
                
                # Voltage가 너무 크면 경고
                if abs(avg_voltage_mV) > 100:
                    print(f"\n⚠️  경고: Voltage가 너무 큽니다! ({avg_voltage_mV:.3f}mV)")
                    print(f"  → 예상 shunt drop: < 100mV")
                    print(f"  → Rail voltage를 측정하고 있을 수 있습니다!")
                
                print()
                
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 80)
    print("📝 추가 확인 사항:")
    print("=" * 80)
    print()
    print("1. Manual tool이 측정한 전류 값은? (mA)")
    print("2. Manual tool의 Voltage Range 설정은?")
    print("3. Manual tool의 Terminal Config는? (RSE/DIFF/DEFAULT)")
    print("4. 하드웨어 연결 방식:")
    print("   - Shunt 양쪽에 어떻게 연결되어 있나요?")
    print("   - (A)+ai0과 (B)-ai0 연결 확인")
    print()
    print("✅ 테스트 완료")

if __name__ == "__main__":
    test_raw_voltage_measurement()
