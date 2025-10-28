#!/usr/bin/env python3
"""
USB Interference Mitigation Test Script
USB 간섭 완화 기능 테스트 및 검증 스크립트
"""

import sys
import time
import random
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QTextEdit
from PyQt6.QtCore import QTimer
from services.usb_interference_mitigation import create_usb_mitigation_service, MeasurementMode
from ui.usb_interference_dialog import USBInterferenceDialog


class USBInterferenceTestWindow(QMainWindow):
    """USB 간섭 완화 테스트 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB Interference Mitigation Test")
        self.setGeometry(100, 100, 800, 600)
        
        # USB 간섭 완화 서비스 생성
        self.mitigation_service = create_usb_mitigation_service()
        
        # UI 설정
        self._setup_ui()
        self._connect_signals()
        
        # 테스트 타이머
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self._run_test_cycle)
        self.test_timer.setInterval(2000)  # 2초마다 테스트
        
        # 테스트 데이터
        self.test_cycle = 0
        self.base_voltage = 4.15  # 기준 배터리 전압
        self.usb_interference = 0.08  # USB 간섭 전압 (80mV)
        
        # 간섭 완화 서비스 시작
        self.mitigation_service.start_monitoring()
        
        self.log("USB Interference Mitigation Test Started")
        self.log("=" * 50)
    
    def _setup_ui(self):
        """UI 구성"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 상태 표시
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        # 현재 측정값 표시
        self.measurement_label = QLabel("Current Measurement: --")
        self.measurement_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.measurement_label)
        
        # 보정 정보 표시
        self.compensation_label = QLabel("Compensation Info: --")
        self.compensation_label.setStyleSheet("font-size: 12px; color: blue;")
        layout.addWidget(self.compensation_label)
        
        # 제어 버튼들
        self.start_test_btn = QPushButton("Start Automatic Test")
        self.start_test_btn.clicked.connect(self.start_automatic_test)
        layout.addWidget(self.start_test_btn)
        
        self.stop_test_btn = QPushButton("Stop Test")
        self.stop_test_btn.clicked.connect(self.stop_test)
        self.stop_test_btn.setEnabled(False)
        layout.addWidget(self.stop_test_btn)
        
        self.manual_test_btn = QPushButton("Manual Test Cycle")
        self.manual_test_btn.clicked.connect(self._run_test_cycle)
        layout.addWidget(self.manual_test_btn)
        
        self.open_settings_btn = QPushButton("Open USB Interference Settings")
        self.open_settings_btn.clicked.connect(self.open_settings_dialog)
        layout.addWidget(self.open_settings_btn)
        
        self.reset_learning_btn = QPushButton("Reset Learning Data")
        self.reset_learning_btn.clicked.connect(self.reset_learning_data)
        layout.addWidget(self.reset_learning_btn)
        
        # 로그 영역
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(300)
        layout.addWidget(self.log_text)
    
    def _connect_signals(self):
        """시그널 연결"""
        self.mitigation_service.measurement_mode_changed.connect(self._on_mode_changed)
        self.mitigation_service.usb_state_changed.connect(self._on_usb_state_changed)
        self.mitigation_service.interference_detected.connect(self._on_interference_detected)
        self.mitigation_service.compensation_applied.connect(self._on_compensation_applied)
    
    def start_automatic_test(self):
        """자동 테스트 시작"""
        self.test_timer.start()
        self.start_test_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(True)
        self.status_label.setText("Status: Running Automatic Test")
        self.log("Automatic test started")
    
    def stop_test(self):
        """테스트 중지"""
        self.test_timer.stop()
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
        self.status_label.setText("Status: Test Stopped")
        self.log("Automatic test stopped")
    
    def _run_test_cycle(self):
        """테스트 사이클 실행"""
        self.test_cycle += 1
        
        # USB 연결 상태 시뮬레이션 (교대로 연결/해제)
        usb_connected = (self.test_cycle % 2 == 1)
        
        # 전압 측정값 시뮬레이션
        if usb_connected:
            # USB 연결 시: 기준 전압 + 간섭 + 노이즈
            simulated_voltage = self.base_voltage + self.usb_interference + random.uniform(-0.01, 0.01)
        else:
            # USB 해제 시: 기준 전압 + 노이즈만
            simulated_voltage = self.base_voltage + random.uniform(-0.01, 0.01)
        
        # 간섭 패턴 학습
        self.mitigation_service.learn_interference_pattern(simulated_voltage, usb_connected)
        
        # 전압 보정 적용
        compensated_voltage = self.mitigation_service.compensate_voltage_measurement(simulated_voltage)
        
        # UI 업데이트
        self.measurement_label.setText(
            f"Raw: {simulated_voltage:.4f}V → Compensated: {compensated_voltage:.4f}V "
            f"(USB: {'ON' if usb_connected else 'OFF'})"
        )
        
        # 보정 정보 업데이트
        info = self.mitigation_service.get_compensation_info()
        self.compensation_label.setText(
            f"Mode: {info['measurement_mode']}, "
            f"USB Offset: {info['usb_voltage_offset']:.4f}V, "
            f"Samples: {info['usb_connected_samples']}/{info['usb_disconnected_samples']}"
        )
        
        # 로그 출력
        compensation_applied = abs(compensated_voltage - simulated_voltage) > 0.001
        self.log(
            f"Cycle {self.test_cycle}: {simulated_voltage:.4f}V → {compensated_voltage:.4f}V "
            f"(USB: {'ON' if usb_connected else 'OFF'}, "
            f"Compensation: {'YES' if compensation_applied else 'NO'})"
        )
        
        # 테스트 결과 검증
        if self.test_cycle >= 10:  # 10 사이클 후 검증
            self._verify_test_results()
    
    def _verify_test_results(self):
        """테스트 결과 검증"""
        info = self.mitigation_service.get_compensation_info()
        
        self.log("=" * 50)
        self.log("Test Results Verification:")
        self.log(f"- Total measurements: {info['voltage_history_count']}")
        self.log(f"- USB connected samples: {info['usb_connected_samples']}")
        self.log(f"- USB disconnected samples: {info['usb_disconnected_samples']}")
        self.log(f"- Learned USB offset: {info['usb_voltage_offset']:.4f}V")
        self.log(f"- Expected USB interference: {self.usb_interference:.4f}V")
        
        # 학습된 오프셋이 실제 간섭과 유사한지 확인
        offset_error = abs(info['usb_voltage_offset'] - self.usb_interference)
        if offset_error < 0.02:  # 20mV 이내 오차
            self.log("✅ PASS: Learned offset matches expected interference")
        else:
            self.log("❌ FAIL: Learned offset differs from expected interference")
        
        self.log("=" * 50)
    
    def open_settings_dialog(self):
        """USB 간섭 설정 다이얼로그 열기"""
        try:
            dialog = USBInterferenceDialog(self, self.mitigation_service)
            dialog.show()
            self.log("USB interference settings dialog opened")
        except Exception as e:
            self.log(f"Error opening settings dialog: {e}")
    
    def reset_learning_data(self):
        """학습 데이터 재설정"""
        self.mitigation_service.reset_learning_data()
        self.test_cycle = 0
        self.compensation_label.setText("Compensation Info: Reset")
        self.log("Learning data reset")
    
    def log(self, message: str):
        """로그 메시지 추가"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    # 시그널 핸들러들
    def _on_mode_changed(self, mode: str):
        self.log(f"Measurement mode changed: {mode}")
    
    def _on_usb_state_changed(self, state: str):
        self.log(f"USB state changed: {state}")
    
    def _on_interference_detected(self, level: float):
        self.log(f"Interference detected: {level:.4f}V")
    
    def _on_compensation_applied(self, raw: float, compensated: float):
        compensation = raw - compensated
        self.log(f"Compensation applied: {compensation:.4f}V ({raw:.4f}V → {compensated:.4f}V)")


def run_console_test():
    """콘솔 기반 간단 테스트"""
    print("USB Interference Mitigation Console Test")
    print("=" * 50)
    
    # 서비스 생성
    mitigation = create_usb_mitigation_service()
    
    # 테스트 데이터
    base_voltage = 4.15
    usb_interference = 0.08
    
    print(f"Base voltage: {base_voltage}V")
    print(f"USB interference: {usb_interference}V")
    print()
    
    # 테스트 사이클 실행
    for i in range(20):
        usb_connected = (i % 2 == 0)
        
        # 전압 시뮬레이션
        if usb_connected:
            voltage = base_voltage + usb_interference + random.uniform(-0.005, 0.005)
        else:
            voltage = base_voltage + random.uniform(-0.005, 0.005)
        
        # 학습 및 보정
        mitigation.learn_interference_pattern(voltage, usb_connected)
        compensated = mitigation.compensate_voltage_measurement(voltage)
        
        print(f"Cycle {i+1:2d}: {voltage:.4f}V → {compensated:.4f}V "
              f"(USB: {'ON ' if usb_connected else 'OFF'}, "
              f"Δ: {voltage-compensated:+.4f}V)")
        
        time.sleep(0.1)
    
    # 결과 출력
    info = mitigation.get_compensation_info()
    print()
    print("Test Results:")
    print(f"- Learned USB offset: {info['usb_voltage_offset']:.4f}V")
    print(f"- Expected interference: {usb_interference:.4f}V")
    print(f"- Offset error: {abs(info['usb_voltage_offset'] - usb_interference):.4f}V")
    print(f"- USB connected samples: {info['usb_connected_samples']}")
    print(f"- USB disconnected samples: {info['usb_disconnected_samples']}")


def main():
    """메인 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == '--console':
        # 콘솔 테스트 실행
        run_console_test()
    else:
        # GUI 테스트 실행
        app = QApplication(sys.argv)
        
        window = USBInterferenceTestWindow()
        window.show()
        
        print("USB Interference Mitigation Test Window opened")
        print("Use the GUI to test various features:")
        print("1. Start automatic test to simulate USB connect/disconnect cycles")
        print("2. Open settings dialog to configure compensation parameters")
        print("3. Monitor real-time compensation in the log")
        
        sys.exit(app.exec())


if __name__ == "__main__":
    main()