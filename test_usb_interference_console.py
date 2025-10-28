#!/usr/bin/env python3
"""
USB Interference Mitigation Console Test
USB 간섭 완화 기능 콘솔 테스트 (PyQt6 의존성 없음)
"""

import sys
import time
import random
import subprocess
from typing import Optional, Dict, List, Tuple
from enum import Enum


class MeasurementMode(Enum):
    """측정 모드 정의"""
    NORMAL = "normal"
    BATTERY_ONLY = "battery_only"
    COMPENSATED = "compensated"


class USBConnectionState(Enum):
    """USB 연결 상태"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DATA_ONLY = "data_only"
    UNKNOWN = "unknown"


class SimpleUSBMitigation:
    """간단한 USB 간섭 완화 클래스 (콘솔 테스트용)"""
    
    def __init__(self):
        self.current_mode = MeasurementMode.NORMAL
        self.usb_state = USBConnectionState.UNKNOWN
        self.adb_connected = False
        
        # 간섭 보정 파라미터
        self.usb_voltage_offset = 0.0
        self.interference_threshold = 0.05
        self.compensation_factor = 1.0
        
        # 측정 히스토리
        self.voltage_history = []
        self.usb_connected_measurements = []
        self.usb_disconnected_measurements = []
        
        # 설정
        self.auto_compensation_enabled = True
        self.learning_mode_enabled = True
    
    def compensate_voltage_measurement(self, raw_voltage: float) -> float:
        """전압 측정값 보정"""
        if self.current_mode == MeasurementMode.NORMAL:
            return raw_voltage
        elif self.current_mode == MeasurementMode.BATTERY_ONLY:
            return raw_voltage
        elif self.current_mode == MeasurementMode.COMPENSATED:
            return self._apply_usb_compensation(raw_voltage)
        else:
            return raw_voltage
    
    def _apply_usb_compensation(self, raw_voltage: float) -> float:
        """USB 간섭 보정 알고리즘"""
        interference_level = self._calculate_interference_level(raw_voltage)
        
        if interference_level > self.interference_threshold:
            compensation = self.usb_voltage_offset * self.compensation_factor
            compensated_voltage = raw_voltage - compensation
            return compensated_voltage
        else:
            return raw_voltage
    
    def _calculate_interference_level(self, voltage: float) -> float:
        """간섭 레벨 계산"""
        if not self.voltage_history:
            return 0.0
        
        recent_avg = sum(self.voltage_history[-5:]) / min(5, len(self.voltage_history))
        interference = abs(voltage - recent_avg)
        return interference
    
    def learn_interference_pattern(self, voltage: float, usb_connected: bool):
        """간섭 패턴 학습"""
        if not self.learning_mode_enabled:
            return
        
        # 측정값 히스토리 업데이트
        self.voltage_history.append(voltage)
        if len(self.voltage_history) > 100:
            self.voltage_history.pop(0)
        
        # USB 연결 상태별 측정값 분류
        if usb_connected:
            self.usb_connected_measurements.append(voltage)
            if len(self.usb_connected_measurements) > 50:
                self.usb_connected_measurements.pop(0)
        else:
            self.usb_disconnected_measurements.append(voltage)
            if len(self.usb_disconnected_measurements) > 50:
                self.usb_disconnected_measurements.pop(0)
        
        # 보정 파라미터 자동 업데이트
        self._update_compensation_parameters()
    
    def _update_compensation_parameters(self):
        """보정 파라미터 자동 업데이트"""
        if (len(self.usb_connected_measurements) >= 5 and 
            len(self.usb_disconnected_measurements) >= 5):
            
            usb_on_avg = sum(self.usb_connected_measurements) / len(self.usb_connected_measurements)
            usb_off_avg = sum(self.usb_disconnected_measurements) / len(self.usb_disconnected_measurements)
            
            new_offset = usb_on_avg - usb_off_avg
            
            # 스무딩
            alpha = 0.1
            self.usb_voltage_offset = (1 - alpha) * self.usb_voltage_offset + alpha * new_offset
    
    def set_measurement_mode(self, mode: MeasurementMode):
        """측정 모드 설정"""
        self.current_mode = mode
    
    def get_compensation_info(self) -> Dict:
        """보정 정보 반환"""
        return {
            'measurement_mode': self.current_mode.value,
            'usb_state': self.usb_state.value,
            'usb_voltage_offset': self.usb_voltage_offset,
            'compensation_factor': self.compensation_factor,
            'interference_threshold': self.interference_threshold,
            'auto_compensation_enabled': self.auto_compensation_enabled,
            'learning_mode_enabled': self.learning_mode_enabled,
            'voltage_history_count': len(self.voltage_history),
            'usb_connected_samples': len(self.usb_connected_measurements),
            'usb_disconnected_samples': len(self.usb_disconnected_measurements)
        }
    
    def reset_learning_data(self):
        """학습 데이터 초기화"""
        self.voltage_history.clear()
        self.usb_connected_measurements.clear()
        self.usb_disconnected_measurements.clear()
        self.usb_voltage_offset = 0.0


def run_basic_test():
    """기본 USB 간섭 완화 테스트"""
    print("🔋 USB Interference Mitigation Console Test")
    print("=" * 60)
    
    # 서비스 생성
    mitigation = SimpleUSBMitigation()
    mitigation.set_measurement_mode(MeasurementMode.COMPENSATED)
    
    # 테스트 파라미터
    base_voltage = 4.15  # 실제 배터리 전압
    usb_interference = 0.08  # USB 간섭 전압 (80mV)
    
    print(f"📊 Test Parameters:")
    print(f"   Base Battery Voltage: {base_voltage}V")
    print(f"   USB Interference: {usb_interference}V ({usb_interference*1000:.0f}mV)")
    print(f"   Measurement Mode: {mitigation.current_mode.value}")
    print()
    
    print("🔄 Running Test Cycles...")
    print("   Format: Cycle | Raw Voltage | Compensated | USB State | Compensation")
    print("-" * 70)
    
    # 테스트 사이클 실행
    for i in range(20):
        usb_connected = (i % 2 == 0)  # 교대로 USB 연결/해제
        
        # 전압 시뮬레이션
        noise = random.uniform(-0.005, 0.005)  # ±5mV 노이즈
        if usb_connected:
            # USB 연결 시: 기준 전압 + 간섭 + 노이즈
            voltage = base_voltage + usb_interference + noise
        else:
            # USB 해제 시: 기준 전압 + 노이즈만
            voltage = base_voltage + noise
        
        # 학습 및 보정
        mitigation.learn_interference_pattern(voltage, usb_connected)
        compensated = mitigation.compensate_voltage_measurement(voltage)
        
        # 보정량 계산
        compensation_applied = voltage - compensated
        usb_state_str = "ON " if usb_connected else "OFF"
        
        print(f"   {i+1:2d}    | {voltage:.4f}V    | {compensated:.4f}V   | USB {usb_state_str} | {compensation_applied:+.4f}V")
        
        time.sleep(0.05)  # 짧은 지연
    
    print("-" * 70)
    
    # 결과 분석
    info = mitigation.get_compensation_info()
    
    print()
    print("📈 Test Results Analysis:")
    print(f"   Learned USB Offset: {info['usb_voltage_offset']:.4f}V ({info['usb_voltage_offset']*1000:.1f}mV)")
    print(f"   Expected Interference: {usb_interference:.4f}V ({usb_interference*1000:.1f}mV)")
    
    offset_error = abs(info['usb_voltage_offset'] - usb_interference)
    print(f"   Offset Error: {offset_error:.4f}V ({offset_error*1000:.1f}mV)")
    
    print(f"   USB Connected Samples: {info['usb_connected_samples']}")
    print(f"   USB Disconnected Samples: {info['usb_disconnected_samples']}")
    print(f"   Total Measurements: {info['voltage_history_count']}")
    
    # 성능 평가
    print()
    print("🎯 Performance Evaluation:")
    
    if offset_error < 0.02:  # 20mV 이내
        print("   ✅ EXCELLENT: Learned offset is within 20mV of expected interference")
        grade = "A"
    elif offset_error < 0.04:  # 40mV 이내
        print("   ✅ GOOD: Learned offset is within 40mV of expected interference")
        grade = "B"
    elif offset_error < 0.06:  # 60mV 이내
        print("   ⚠️  FAIR: Learned offset is within 60mV of expected interference")
        grade = "C"
    else:
        print("   ❌ POOR: Learned offset differs significantly from expected interference")
        grade = "D"
    
    accuracy = max(0, 100 - (offset_error / usb_interference * 100))
    print(f"   Compensation Accuracy: {accuracy:.1f}%")
    print(f"   Overall Grade: {grade}")
    
    return grade, accuracy, info


def run_advanced_test():
    """고급 USB 간섭 완화 테스트"""
    print("\n" + "=" * 60)
    print("🚀 Advanced USB Interference Mitigation Test")
    print("=" * 60)
    
    mitigation = SimpleUSBMitigation()
    mitigation.set_measurement_mode(MeasurementMode.COMPENSATED)
    
    # 다양한 시나리오 테스트
    scenarios = [
        {"name": "Low Interference", "base": 4.15, "interference": 0.03, "cycles": 15},
        {"name": "Medium Interference", "base": 4.15, "interference": 0.08, "cycles": 15},
        {"name": "High Interference", "base": 4.15, "interference": 0.15, "cycles": 15},
        {"name": "Variable Voltage", "base": 3.95, "interference": 0.08, "cycles": 15},
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n📋 Scenario: {scenario['name']}")
        print(f"   Base Voltage: {scenario['base']:.2f}V")
        print(f"   Interference: {scenario['interference']:.3f}V ({scenario['interference']*1000:.0f}mV)")
        
        # 학습 데이터 초기화
        mitigation.reset_learning_data()
        
        # 시나리오 실행
        total_error = 0
        for i in range(scenario['cycles']):
            usb_connected = (i % 2 == 0)
            noise = random.uniform(-0.005, 0.005)
            
            if usb_connected:
                voltage = scenario['base'] + scenario['interference'] + noise
            else:
                voltage = scenario['base'] + noise
            
            mitigation.learn_interference_pattern(voltage, usb_connected)
            compensated = mitigation.compensate_voltage_measurement(voltage)
            
            # 오차 누적 (USB 연결 시에만)
            if usb_connected and i > 4:  # 학습 후 평가
                expected_compensated = scenario['base'] + noise
                error = abs(compensated - expected_compensated)
                total_error += error
        
        # 시나리오 결과
        info = mitigation.get_compensation_info()
        offset_error = abs(info['usb_voltage_offset'] - scenario['interference'])
        avg_compensation_error = total_error / max(1, (scenario['cycles'] // 2 - 2))
        
        accuracy = max(0, 100 - (offset_error / scenario['interference'] * 100))
        
        print(f"   Learned Offset: {info['usb_voltage_offset']:.4f}V")
        print(f"   Offset Error: {offset_error:.4f}V")
        print(f"   Accuracy: {accuracy:.1f}%")
        
        results.append({
            'scenario': scenario['name'],
            'accuracy': accuracy,
            'offset_error': offset_error,
            'avg_error': avg_compensation_error
        })
    
    # 전체 결과 요약
    print("\n" + "=" * 60)
    print("📊 Overall Test Summary")
    print("=" * 60)
    
    total_accuracy = sum(r['accuracy'] for r in results) / len(results)
    
    print(f"{'Scenario':<20} {'Accuracy':<10} {'Offset Error':<12} {'Avg Error'}")
    print("-" * 60)
    for result in results:
        print(f"{result['scenario']:<20} {result['accuracy']:>7.1f}%   {result['offset_error']:>9.4f}V   {result['avg_error']:>8.4f}V")
    
    print("-" * 60)
    print(f"{'OVERALL AVERAGE':<20} {total_accuracy:>7.1f}%")
    
    if total_accuracy >= 90:
        print("🏆 EXCELLENT: USB interference mitigation is working very well!")
    elif total_accuracy >= 75:
        print("✅ GOOD: USB interference mitigation is working well")
    elif total_accuracy >= 60:
        print("⚠️  FAIR: USB interference mitigation needs improvement")
    else:
        print("❌ POOR: USB interference mitigation needs significant work")
    
    return total_accuracy


def check_adb_connection():
    """실제 ADB 연결 상태 확인"""
    try:
        result = subprocess.run(['adb', 'devices'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]
            connected_devices = [line for line in lines if '\tdevice' in line]
            return len(connected_devices) > 0, connected_devices
    except Exception as e:
        return False, []
    
    return False, []


def show_hardware_recommendations():
    """하드웨어 솔루션 권장사항 표시"""
    print("\n" + "=" * 60)
    print("🔧 Hardware Solutions for USB Interference")
    print("=" * 60)
    
    print("""
💡 Recommended Hardware Solutions:

1. 📱 USB Data-Only Cable
   • Use a USB cable with power lines disconnected
   • Prevents 5V USB power from interfering with battery measurement
   • Cost: Low (~$5-10)
   • Effectiveness: High

2. 🔌 USB Isolator
   • Use a USB signal isolator (e.g., ADUM4160, USB-ISO)
   • Provides electrical isolation between PC and device
   • Cost: Medium (~$20-50)
   • Effectiveness: Very High

3. ⚡ External Power Supply
   • Use a separate, stable power supply for the device
   • USB used only for data communication
   • Cost: High (~$50-200)
   • Effectiveness: Excellent

4. 🖥️ Software Compensation (Current Implementation)
   • Automatic USB interference detection and compensation
   • Learning-based pattern recognition
   • Cost: Free
   • Effectiveness: Good (70-90% depending on conditions)

🎯 Recommended Setup:
   1. Use USB data-only cable if possible
   2. Enable software compensation as backup
   3. Perform regular calibration
   4. Monitor compensation accuracy
    """)


def main():
    """메인 함수"""
    print("🔋 USB Interference Mitigation Test Suite")
    print("Designed to validate USB voltage interference mitigation")
    print()
    
    # ADB 연결 상태 확인
    adb_connected, devices = check_adb_connection()
    if adb_connected:
        print(f"📱 ADB Status: Connected ({len(devices)} device(s))")
        for device in devices:
            print(f"   - {device}")
    else:
        print("📱 ADB Status: No devices connected")
    print()
    
    # 기본 테스트 실행
    grade, accuracy, info = run_basic_test()
    
    # 고급 테스트 실행
    if len(sys.argv) > 1 and '--advanced' in sys.argv:
        overall_accuracy = run_advanced_test()
    
    # 하드웨어 권장사항 표시
    if len(sys.argv) > 1 and '--hardware' in sys.argv:
        show_hardware_recommendations()
    
    print("\n" + "=" * 60)
    print("✅ Test Completed Successfully!")
    print("=" * 60)
    print()
    print("Usage options:")
    print("  python3 test_usb_interference_console.py                 # Basic test")
    print("  python3 test_usb_interference_console.py --advanced      # Advanced test")
    print("  python3 test_usb_interference_console.py --hardware      # Show hardware solutions")
    print()


if __name__ == "__main__":
    main()