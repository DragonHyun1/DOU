#!/usr/bin/env python3
"""
USB Interference Mitigation Dialog
USB 간섭 완화 설정 및 모니터링 다이얼로그
"""

import time
import json
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QProgressBar, QTextEdit, QTabWidget, QWidget, QSpinBox,
    QDoubleSpinBox, QMessageBox, QFileDialog, QFrame
)
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette
from services.usb_interference_mitigation import USBInterferenceMitigation, MeasurementMode, USBConnectionState


class USBInterferenceDialog(QDialog):
    """USB 간섭 완화 설정 다이얼로그"""
    
    # 시그널 정의
    compensation_settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None, mitigation_service: USBInterferenceMitigation = None):
        super().__init__(parent)
        self.mitigation_service = mitigation_service
        self.setWindowTitle("USB Interference Mitigation Settings")
        self.setModal(False)
        self.resize(600, 500)
        
        # UI 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status_display)
        self.update_timer.setInterval(1000)  # 1초마다 업데이트
        
        self._setup_ui()
        self._connect_signals()
        self._load_current_settings()
        
        # 상태 업데이트 시작
        self.update_timer.start()
    
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        
        # 탭 위젯 생성
        tab_widget = QTabWidget()
        
        # 탭 1: 상태 모니터링
        tab_widget.addTab(self._create_status_tab(), "Status Monitor")
        
        # 탭 2: 보정 설정
        tab_widget.addTab(self._create_compensation_tab(), "Compensation Settings")
        
        # 탭 3: 학습 데이터
        tab_widget.addTab(self._create_learning_tab(), "Learning Data")
        
        # 탭 4: 하드웨어 솔루션
        tab_widget.addTab(self._create_hardware_tab(), "Hardware Solutions")
        
        layout.addWidget(tab_widget)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("Apply Settings")
        self.reset_button = QPushButton("Reset to Defaults")
        self.close_button = QPushButton("Close")
        
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def _create_status_tab(self) -> QWidget:
        """상태 모니터링 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # USB 연결 상태 그룹
        usb_group = QGroupBox("USB Connection Status")
        usb_layout = QGridLayout(usb_group)
        
        usb_layout.addWidget(QLabel("USB State:"), 0, 0)
        self.usb_state_label = QLabel("Unknown")
        self.usb_state_label.setStyleSheet("font-weight: bold; color: orange;")
        usb_layout.addWidget(self.usb_state_label, 0, 1)
        
        usb_layout.addWidget(QLabel("ADB Connected:"), 1, 0)
        self.adb_status_label = QLabel("Unknown")
        usb_layout.addWidget(self.adb_status_label, 1, 1)
        
        usb_layout.addWidget(QLabel("Measurement Mode:"), 2, 0)
        self.measurement_mode_label = QLabel("Normal")
        self.measurement_mode_label.setStyleSheet("font-weight: bold;")
        usb_layout.addWidget(self.measurement_mode_label, 2, 1)
        
        layout.addWidget(usb_group)
        
        # 간섭 감지 상태 그룹
        interference_group = QGroupBox("Interference Detection")
        interference_layout = QGridLayout(interference_group)
        
        interference_layout.addWidget(QLabel("Interference Level:"), 0, 0)
        self.interference_level_bar = QProgressBar()
        self.interference_level_bar.setRange(0, 100)
        self.interference_level_bar.setValue(0)
        interference_layout.addWidget(self.interference_level_bar, 0, 1)
        
        interference_layout.addWidget(QLabel("Last Compensation:"), 1, 0)
        self.last_compensation_label = QLabel("None")
        interference_layout.addWidget(self.last_compensation_label, 1, 1)
        
        interference_layout.addWidget(QLabel("Compensation Count:"), 2, 0)
        self.compensation_count_label = QLabel("0")
        interference_layout.addWidget(self.compensation_count_label, 2, 1)
        
        layout.addWidget(interference_group)
        
        # 실시간 로그
        log_group = QGroupBox("Real-time Log")
        log_layout = QVBoxLayout(log_group)
        
        self.status_log = QTextEdit()
        self.status_log.setMaximumHeight(150)
        self.status_log.setReadOnly(True)
        log_layout.addWidget(self.status_log)
        
        clear_log_button = QPushButton("Clear Log")
        clear_log_button.clicked.connect(self.status_log.clear)
        log_layout.addWidget(clear_log_button)
        
        layout.addWidget(log_group)
        
        layout.addStretch()
        return widget
    
    def _create_compensation_tab(self) -> QWidget:
        """보정 설정 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 자동 보정 설정
        auto_group = QGroupBox("Automatic Compensation")
        auto_layout = QGridLayout(auto_group)
        
        self.auto_compensation_cb = QCheckBox("Enable Auto Compensation")
        auto_layout.addWidget(self.auto_compensation_cb, 0, 0, 1, 2)
        
        self.learning_mode_cb = QCheckBox("Enable Learning Mode")
        auto_layout.addWidget(self.learning_mode_cb, 1, 0, 1, 2)
        
        auto_layout.addWidget(QLabel("Interference Threshold (V):"), 2, 0)
        self.interference_threshold_spin = QDoubleSpinBox()
        self.interference_threshold_spin.setRange(0.001, 1.0)
        self.interference_threshold_spin.setDecimals(3)
        self.interference_threshold_spin.setSingleStep(0.001)
        self.interference_threshold_spin.setValue(0.050)
        auto_layout.addWidget(self.interference_threshold_spin, 2, 1)
        
        layout.addWidget(auto_group)
        
        # 수동 보정 설정
        manual_group = QGroupBox("Manual Compensation")
        manual_layout = QGridLayout(manual_group)
        
        manual_layout.addWidget(QLabel("USB Voltage Offset (V):"), 0, 0)
        self.usb_offset_spin = QDoubleSpinBox()
        self.usb_offset_spin.setRange(-1.0, 1.0)
        self.usb_offset_spin.setDecimals(4)
        self.usb_offset_spin.setSingleStep(0.0001)
        self.usb_offset_spin.setValue(0.0)
        manual_layout.addWidget(self.usb_offset_spin, 0, 1)
        
        manual_layout.addWidget(QLabel("Compensation Factor:"), 1, 0)
        self.compensation_factor_spin = QDoubleSpinBox()
        self.compensation_factor_spin.setRange(0.1, 10.0)
        self.compensation_factor_spin.setDecimals(2)
        self.compensation_factor_spin.setSingleStep(0.01)
        self.compensation_factor_spin.setValue(1.0)
        manual_layout.addWidget(self.compensation_factor_spin, 1, 1)
        
        # 캘리브레이션 버튼들
        calibration_layout = QHBoxLayout()
        
        self.calibrate_button = QPushButton("Start Calibration")
        self.calibrate_button.clicked.connect(self._start_calibration)
        calibration_layout.addWidget(self.calibrate_button)
        
        self.reset_calibration_button = QPushButton("Reset Calibration")
        self.reset_calibration_button.clicked.connect(self._reset_calibration)
        calibration_layout.addWidget(self.reset_calibration_button)
        
        manual_layout.addLayout(calibration_layout, 2, 0, 1, 2)
        
        layout.addWidget(manual_group)
        
        # 측정 모드 설정
        mode_group = QGroupBox("Measurement Mode")
        mode_layout = QGridLayout(mode_group)
        
        mode_layout.addWidget(QLabel("Preferred Mode:"), 0, 0)
        self.measurement_mode_combo = QComboBox()
        self.measurement_mode_combo.addItems([
            "Normal", "Battery Only", "Compensated"
        ])
        mode_layout.addWidget(self.measurement_mode_combo, 0, 1)
        
        self.force_mode_cb = QCheckBox("Force Manual Mode (Disable Auto-switching)")
        mode_layout.addWidget(self.force_mode_cb, 1, 0, 1, 2)
        
        layout.addWidget(mode_group)
        
        layout.addStretch()
        return widget
    
    def _create_learning_tab(self) -> QWidget:
        """학습 데이터 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 학습 통계
        stats_group = QGroupBox("Learning Statistics")
        stats_layout = QGridLayout(stats_group)
        
        stats_layout.addWidget(QLabel("Total Measurements:"), 0, 0)
        self.total_measurements_label = QLabel("0")
        stats_layout.addWidget(self.total_measurements_label, 0, 1)
        
        stats_layout.addWidget(QLabel("USB Connected Samples:"), 1, 0)
        self.usb_connected_samples_label = QLabel("0")
        stats_layout.addWidget(self.usb_connected_samples_label, 1, 1)
        
        stats_layout.addWidget(QLabel("USB Disconnected Samples:"), 2, 0)
        self.usb_disconnected_samples_label = QLabel("0")
        stats_layout.addWidget(self.usb_disconnected_samples_label, 2, 1)
        
        stats_layout.addWidget(QLabel("Learned USB Offset:"), 3, 0)
        self.learned_offset_label = QLabel("0.0000 V")
        self.learned_offset_label.setStyleSheet("font-weight: bold; color: blue;")
        stats_layout.addWidget(self.learned_offset_label, 3, 1)
        
        layout.addWidget(stats_group)
        
        # 학습 데이터 관리
        data_group = QGroupBox("Learning Data Management")
        data_layout = QVBoxLayout(data_group)
        
        button_layout = QHBoxLayout()
        
        self.export_data_button = QPushButton("Export Learning Data")
        self.export_data_button.clicked.connect(self._export_learning_data)
        button_layout.addWidget(self.export_data_button)
        
        self.import_data_button = QPushButton("Import Learning Data")
        self.import_data_button.clicked.connect(self._import_learning_data)
        button_layout.addWidget(self.import_data_button)
        
        self.reset_data_button = QPushButton("Reset Learning Data")
        self.reset_data_button.clicked.connect(self._reset_learning_data)
        button_layout.addWidget(self.reset_data_button)
        
        data_layout.addLayout(button_layout)
        
        # 학습 데이터 미리보기
        preview_label = QLabel("Recent Measurements Preview:")
        data_layout.addWidget(preview_label)
        
        self.data_preview = QTextEdit()
        self.data_preview.setMaximumHeight(100)
        self.data_preview.setReadOnly(True)
        data_layout.addWidget(self.data_preview)
        
        layout.addWidget(data_group)
        
        layout.addStretch()
        return widget
    
    def _create_hardware_tab(self) -> QWidget:
        """하드웨어 솔루션 탭 생성"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 하드웨어 솔루션 안내
        info_group = QGroupBox("Hardware Solutions for USB Interference")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml("""
        <h3>USB 전압 간섭 완화를 위한 하드웨어 솔루션</h3>
        
        <h4>1. USB 데이터 전용 케이블 사용</h4>
        <ul>
            <li>USB Type-A to Micro-USB/USB-C 데이터 전용 케이블</li>
            <li>5V, GND 핀이 연결되지 않은 케이블</li>
            <li>또는 기존 케이블의 5V 라인을 물리적으로 차단</li>
            <li><b>장점:</b> 간단하고 저렴한 해결책</li>
            <li><b>단점:</b> 디바이스가 외부 전원을 필요로 함</li>
        </ul>
        
        <h4>2. USB 아이솔레이터 사용</h4>
        <ul>
            <li>USB 신호 아이솔레이터 (예: ADUM4160, USB-ISO)</li>
            <li>전기적 격리를 통한 간섭 차단</li>
            <li>데이터 신호는 유지하면서 전원 분리</li>
            <li><b>장점:</b> 완전한 전기적 격리</li>
            <li><b>단점:</b> 추가 비용 및 복잡성</li>
        </ul>
        
        <h4>3. 외부 전원 공급</h4>
        <ul>
            <li>디바이스에 별도의 안정화된 전원 공급</li>
            <li>USB는 순수 통신 목적으로만 사용</li>
            <li>배터리 시뮬레이터나 정밀 전원 공급장치 사용</li>
            <li><b>장점:</b> 가장 정확한 측정 가능</li>
            <li><b>단점:</b> 복잡한 설정 및 높은 비용</li>
        </ul>
        
        <h4>4. 소프트웨어 보정 (현재 구현)</h4>
        <ul>
            <li>USB 연결 상태 감지 및 자동 보정</li>
            <li>학습 기반 간섭 패턴 인식</li>
            <li>실시간 보정값 적용</li>
            <li><b>장점:</b> 추가 하드웨어 불필요</li>
            <li><b>단점:</b> 완벽하지 않은 보정</li>
        </ul>
        """)
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        
        # 권장 설정
        recommendation_group = QGroupBox("Recommended Setup")
        recommendation_layout = QVBoxLayout(recommendation_group)
        
        recommendation_text = QLabel("""
        <b>권장 설정:</b><br>
        1. 가능하면 USB 데이터 전용 케이블 사용<br>
        2. 소프트웨어 자동 보정 활성화<br>
        3. 학습 모드를 통한 간섭 패턴 학습<br>
        4. 정기적인 캘리브레이션 수행
        """)
        recommendation_text.setWordWrap(True)
        recommendation_text.setStyleSheet("background-color: #e8f4f8; padding: 10px; border-radius: 5px;")
        recommendation_layout.addWidget(recommendation_text)
        
        layout.addWidget(recommendation_group)
        
        layout.addStretch()
        return widget
    
    def _connect_signals(self):
        """시그널 연결"""
        # 버튼 시그널
        self.apply_button.clicked.connect(self._apply_settings)
        self.reset_button.clicked.connect(self._reset_to_defaults)
        self.close_button.clicked.connect(self.close)
        
        # 간섭 완화 서비스 시그널 연결
        if self.mitigation_service:
            self.mitigation_service.measurement_mode_changed.connect(self._on_mode_changed)
            self.mitigation_service.usb_state_changed.connect(self._on_usb_state_changed)
            self.mitigation_service.interference_detected.connect(self._on_interference_detected)
            self.mitigation_service.compensation_applied.connect(self._on_compensation_applied)
    
    def _load_current_settings(self):
        """현재 설정 로드"""
        if not self.mitigation_service:
            return
        
        info = self.mitigation_service.get_compensation_info()
        
        # 보정 설정 로드
        self.auto_compensation_cb.setChecked(info.get('auto_compensation_enabled', True))
        self.learning_mode_cb.setChecked(info.get('learning_mode_enabled', True))
        self.interference_threshold_spin.setValue(info.get('interference_threshold', 0.050))
        self.usb_offset_spin.setValue(info.get('usb_voltage_offset', 0.0))
        self.compensation_factor_spin.setValue(info.get('compensation_factor', 1.0))
        
        # 측정 모드 설정
        mode_map = {
            'normal': 0,
            'battery_only': 1,
            'compensated': 2
        }
        current_mode = info.get('measurement_mode', 'normal')
        self.measurement_mode_combo.setCurrentIndex(mode_map.get(current_mode, 0))
    
    def _apply_settings(self):
        """설정 적용"""
        if not self.mitigation_service:
            return
        
        settings = {
            'auto_compensation_enabled': self.auto_compensation_cb.isChecked(),
            'learning_mode_enabled': self.learning_mode_cb.isChecked(),
            'interference_threshold': self.interference_threshold_spin.value(),
            'usb_voltage_offset': self.usb_offset_spin.value(),
            'compensation_factor': self.compensation_factor_spin.value()
        }
        
        self.mitigation_service.set_compensation_parameters(**settings)
        
        # 측정 모드 설정
        mode_map = ['normal', 'battery_only', 'compensated']
        selected_mode = mode_map[self.measurement_mode_combo.currentIndex()]
        mode_enum = MeasurementMode(selected_mode)
        self.mitigation_service.set_measurement_mode(mode_enum)
        
        self.compensation_settings_changed.emit(settings)
        
        QMessageBox.information(self, "Settings Applied", "USB interference mitigation settings have been applied.")
    
    def _reset_to_defaults(self):
        """기본값으로 재설정"""
        self.auto_compensation_cb.setChecked(True)
        self.learning_mode_cb.setChecked(True)
        self.interference_threshold_spin.setValue(0.050)
        self.usb_offset_spin.setValue(0.0)
        self.compensation_factor_spin.setValue(1.0)
        self.measurement_mode_combo.setCurrentIndex(0)
        
        if self.mitigation_service:
            self.mitigation_service.reset_learning_data()
    
    def _start_calibration(self):
        """캘리브레이션 시작"""
        QMessageBox.information(
            self, 
            "Calibration Process",
            "캘리브레이션을 시작합니다.\n\n"
            "1. USB를 연결한 상태에서 전압을 측정하세요.\n"
            "2. USB를 해제한 상태에서 동일한 전압을 측정하세요.\n"
            "3. 시스템이 자동으로 오프셋을 계산합니다."
        )
        
        # 캘리브레이션 모드 활성화 (실제 구현에서는 더 복잡한 로직 필요)
        if self.mitigation_service:
            self.mitigation_service.reset_learning_data()
            self._log_status("Calibration started - collecting data...")
    
    def _reset_calibration(self):
        """캘리브레이션 재설정"""
        if self.mitigation_service:
            self.mitigation_service.reset_learning_data()
            self.usb_offset_spin.setValue(0.0)
            self._log_status("Calibration data reset")
    
    def _export_learning_data(self):
        """학습 데이터 내보내기"""
        if not self.mitigation_service:
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Learning Data", 
            f"usb_interference_data_{int(time.time())}.json",
            "JSON Files (*.json)"
        )
        
        if filename:
            try:
                data = self.mitigation_service.export_learning_data()
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                QMessageBox.information(self, "Export Complete", f"Learning data exported to:\n{filename}")
                self._log_status(f"Learning data exported to {filename}")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Failed to export data:\n{e}")
    
    def _import_learning_data(self):
        """학습 데이터 가져오기"""
        if not self.mitigation_service:
            return
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Learning Data",
            "",
            "JSON Files (*.json)"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                self.mitigation_service.import_learning_data(data)
                self._load_current_settings()  # 설정 다시 로드
                
                QMessageBox.information(self, "Import Complete", f"Learning data imported from:\n{filename}")
                self._log_status(f"Learning data imported from {filename}")
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to import data:\n{e}")
    
    def _reset_learning_data(self):
        """학습 데이터 재설정"""
        reply = QMessageBox.question(
            self,
            "Reset Learning Data",
            "Are you sure you want to reset all learning data?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.mitigation_service:
                self.mitigation_service.reset_learning_data()
                self._log_status("Learning data reset")
    
    def _update_status_display(self):
        """상태 표시 업데이트"""
        if not self.mitigation_service:
            return
        
        info = self.mitigation_service.get_compensation_info()
        
        # USB 상태 업데이트
        usb_state = info.get('usb_state', 'unknown')
        self.usb_state_label.setText(usb_state.title())
        
        # 상태에 따른 색상 변경
        color_map = {
            'connected': 'red',
            'data_only': 'orange', 
            'disconnected': 'green',
            'unknown': 'gray'
        }
        color = color_map.get(usb_state, 'gray')
        self.usb_state_label.setStyleSheet(f"font-weight: bold; color: {color};")
        
        # ADB 상태
        adb_connected = self.mitigation_service.adb_connected
        self.adb_status_label.setText("Connected" if adb_connected else "Disconnected")
        self.adb_status_label.setStyleSheet(f"color: {'green' if adb_connected else 'red'};")
        
        # 측정 모드
        mode = info.get('measurement_mode', 'normal')
        self.measurement_mode_label.setText(mode.replace('_', ' ').title())
        
        # 학습 통계 업데이트
        self.total_measurements_label.setText(str(info.get('voltage_history_count', 0)))
        self.usb_connected_samples_label.setText(str(info.get('usb_connected_samples', 0)))
        self.usb_disconnected_samples_label.setText(str(info.get('usb_disconnected_samples', 0)))
        self.learned_offset_label.setText(f"{info.get('usb_voltage_offset', 0.0):.4f} V")
    
    def _log_status(self, message: str):
        """상태 로그에 메시지 추가"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_log.append(f"[{timestamp}] {message}")
        
        # 로그 크기 제한
        if self.status_log.document().blockCount() > 100:
            cursor = self.status_log.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.removeSelectedText()
    
    # 시그널 핸들러들
    def _on_mode_changed(self, mode: str):
        """측정 모드 변경 시그널 핸들러"""
        self._log_status(f"Measurement mode changed to: {mode}")
    
    def _on_usb_state_changed(self, state: str):
        """USB 상태 변경 시그널 핸들러"""
        self._log_status(f"USB state changed to: {state}")
    
    def _on_interference_detected(self, level: float):
        """간섭 감지 시그널 핸들러"""
        self.interference_level_bar.setValue(int(level * 1000))  # mV 단위로 표시
        self._log_status(f"Interference detected: {level:.4f}V")
    
    def _on_compensation_applied(self, raw: float, compensated: float):
        """보정 적용 시그널 핸들러"""
        compensation = raw - compensated
        self.last_compensation_label.setText(f"{compensation:.4f}V")
        self._log_status(f"Compensation applied: {raw:.4f}V -> {compensated:.4f}V")
        
        # 보정 횟수 업데이트
        current_count = int(self.compensation_count_label.text())
        self.compensation_count_label.setText(str(current_count + 1))
    
    def closeEvent(self, event):
        """다이얼로그 닫기 이벤트"""
        self.update_timer.stop()
        event.accept()


# 테스트 코드
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from services.usb_interference_mitigation import create_usb_mitigation_service
    
    app = QApplication(sys.argv)
    
    # 테스트용 간섭 완화 서비스 생성
    mitigation_service = create_usb_mitigation_service()
    
    # 다이얼로그 생성 및 표시
    dialog = USBInterferenceDialog(mitigation_service=mitigation_service)
    dialog.show()
    
    sys.exit(app.exec())