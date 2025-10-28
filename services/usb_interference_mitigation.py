#!/usr/bin/env python3
"""
USB Interference Mitigation Service
USB 연결로 인한 배터리 전압 측정 간섭을 완화하는 서비스

주요 기능:
1. USB 전원 간섭 감지 및 보정
2. 측정 모드별 USB 연결 관리
3. 배터리 전압 정확도 향상
4. ADB 연결 상태 모니터링
"""

import time
import logging
from typing import Optional, Dict, List, Tuple
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import subprocess


class MeasurementMode(Enum):
    """측정 모드 정의"""
    NORMAL = "normal"           # 일반 측정 (USB 연결 상태)
    BATTERY_ONLY = "battery_only"  # 배터리 전용 측정 (USB 간섭 최소화)
    COMPENSATED = "compensated"    # 보정된 측정 (USB 간섭 소프트웨어 보정)


class USBConnectionState(Enum):
    """USB 연결 상태"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DATA_ONLY = "data_only"     # 데이터 전용 연결 (전원 차단)
    UNKNOWN = "unknown"


class USBInterferenceMitigation(QObject):
    """USB 간섭 완화 서비스"""
    
    # 시그널 정의
    measurement_mode_changed = pyqtSignal(str)  # 측정 모드 변경
    usb_state_changed = pyqtSignal(str)         # USB 상태 변경
    interference_detected = pyqtSignal(float)    # 간섭 감지 (간섭 레벨)
    compensation_applied = pyqtSignal(float, float)  # 보정 적용 (원본값, 보정값)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # 현재 상태
        self.current_mode = MeasurementMode.NORMAL
        self.usb_state = USBConnectionState.UNKNOWN
        self.adb_connected = False
        
        # 간섭 보정 파라미터
        self.usb_voltage_offset = 0.0      # USB 전압 오프셋 (V)
        self.interference_threshold = 0.05  # 간섭 감지 임계값 (V)
        self.compensation_factor = 1.0      # 보정 계수
        
        # 측정 히스토리 (간섭 패턴 학습용)
        self.voltage_history = []
        self.usb_connected_measurements = []
        self.usb_disconnected_measurements = []
        
        # 모니터링 타이머
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_usb_state)
        self.monitor_timer.setInterval(2000)  # 2초마다 체크
        
        # 자동 보정 설정
        self.auto_compensation_enabled = True
        self.learning_mode_enabled = True
        
    def start_monitoring(self):
        """USB 상태 모니터링 시작"""
        self.monitor_timer.start()
        self.logger.info("USB interference monitoring started")
        
    def stop_monitoring(self):
        """USB 상태 모니터링 중지"""
        self.monitor_timer.stop()
        self.logger.info("USB interference monitoring stopped")
        
    def _monitor_usb_state(self):
        """USB 연결 상태 모니터링"""
        try:
            # ADB 디바이스 상태 확인
            previous_adb_state = self.adb_connected
            self.adb_connected = self._check_adb_connection()
            
            # USB 전원 상태 감지 (간접적 방법)
            usb_power_detected = self._detect_usb_power()
            
            # USB 상태 업데이트
            new_usb_state = self._determine_usb_state(self.adb_connected, usb_power_detected)
            
            if new_usb_state != self.usb_state:
                self.usb_state = new_usb_state
                self.usb_state_changed.emit(new_usb_state.value)
                self.logger.info(f"USB state changed to: {new_usb_state.value}")
                
                # 측정 모드 자동 조정
                if self.auto_compensation_enabled:
                    self._auto_adjust_measurement_mode()
                    
        except Exception as e:
            self.logger.error(f"Error monitoring USB state: {e}")
    
    def _check_adb_connection(self) -> bool:
        """ADB 연결 상태 확인"""
        try:
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # 헤더 제외
                connected_devices = [line for line in lines if '\tdevice' in line]
                return len(connected_devices) > 0
        except Exception as e:
            self.logger.debug(f"ADB check failed: {e}")
        return False
    
    def _detect_usb_power(self) -> bool:
        """USB 전원 공급 감지 (간접적 방법)"""
        # 실제 구현에서는 하드웨어 센서나 전압 측정을 통해 감지
        # 여기서는 시뮬레이션
        return self.adb_connected  # ADB 연결 시 USB 전원도 연결된 것으로 가정
    
    def _determine_usb_state(self, adb_connected: bool, usb_power: bool) -> USBConnectionState:
        """USB 연결 상태 결정"""
        if adb_connected and usb_power:
            return USBConnectionState.CONNECTED
        elif adb_connected and not usb_power:
            return USBConnectionState.DATA_ONLY
        elif not adb_connected:
            return USBConnectionState.DISCONNECTED
        else:
            return USBConnectionState.UNKNOWN
    
    def _auto_adjust_measurement_mode(self):
        """USB 상태에 따른 측정 모드 자동 조정"""
        if self.usb_state == USBConnectionState.CONNECTED:
            # USB 전원 연결 시 보정 모드 사용
            self.set_measurement_mode(MeasurementMode.COMPENSATED)
        elif self.usb_state == USBConnectionState.DATA_ONLY:
            # 데이터 전용 연결 시 일반 모드 사용
            self.set_measurement_mode(MeasurementMode.NORMAL)
        elif self.usb_state == USBConnectionState.DISCONNECTED:
            # USB 연결 해제 시 배터리 전용 모드 사용
            self.set_measurement_mode(MeasurementMode.BATTERY_ONLY)
    
    def set_measurement_mode(self, mode: MeasurementMode):
        """측정 모드 설정"""
        if mode != self.current_mode:
            self.current_mode = mode
            self.measurement_mode_changed.emit(mode.value)
            self.logger.info(f"Measurement mode changed to: {mode.value}")
    
    def compensate_voltage_measurement(self, raw_voltage: float) -> float:
        """전압 측정값 보정"""
        if self.current_mode == MeasurementMode.NORMAL:
            return raw_voltage
        elif self.current_mode == MeasurementMode.BATTERY_ONLY:
            return raw_voltage  # 배터리 전용 모드에서는 보정 불필요
        elif self.current_mode == MeasurementMode.COMPENSATED:
            # USB 간섭 보정 적용
            compensated = self._apply_usb_compensation(raw_voltage)
            self.compensation_applied.emit(raw_voltage, compensated)
            return compensated
        else:
            return raw_voltage
    
    def _apply_usb_compensation(self, raw_voltage: float) -> float:
        """USB 간섭 보정 알고리즘"""
        # 간섭 레벨 계산
        interference_level = self._calculate_interference_level(raw_voltage)
        
        if interference_level > self.interference_threshold:
            self.interference_detected.emit(interference_level)
            
            # 보정값 계산
            compensation = self.usb_voltage_offset * self.compensation_factor
            compensated_voltage = raw_voltage - compensation
            
            self.logger.debug(f"USB compensation applied: {raw_voltage:.3f}V -> {compensated_voltage:.3f}V")
            return compensated_voltage
        else:
            return raw_voltage
    
    def _calculate_interference_level(self, voltage: float) -> float:
        """간섭 레벨 계산"""
        if not self.voltage_history:
            return 0.0
        
        # 최근 측정값과의 차이로 간섭 레벨 추정
        recent_avg = sum(self.voltage_history[-5:]) / min(5, len(self.voltage_history))
        interference = abs(voltage - recent_avg)
        
        return interference
    
    def learn_interference_pattern(self, voltage: float, usb_connected: bool):
        """간섭 패턴 학습"""
        if not self.learning_mode_enabled:
            return
        
        # 측정값 히스토리 업데이트
        self.voltage_history.append(voltage)
        if len(self.voltage_history) > 100:  # 최근 100개만 유지
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
        if (len(self.usb_connected_measurements) >= 10 and 
            len(self.usb_disconnected_measurements) >= 10):
            
            # USB 연결/해제 시 평균 전압 차이 계산
            usb_on_avg = sum(self.usb_connected_measurements) / len(self.usb_connected_measurements)
            usb_off_avg = sum(self.usb_disconnected_measurements) / len(self.usb_disconnected_measurements)
            
            # USB 전압 오프셋 업데이트
            new_offset = usb_on_avg - usb_off_avg
            
            # 급격한 변화 방지 (스무딩)
            alpha = 0.1  # 학습률
            self.usb_voltage_offset = (1 - alpha) * self.usb_voltage_offset + alpha * new_offset
            
            self.logger.debug(f"USB voltage offset updated: {self.usb_voltage_offset:.4f}V")
    
    def calibrate_compensation(self, usb_on_voltage: float, usb_off_voltage: float):
        """수동 보정 캘리브레이션"""
        self.usb_voltage_offset = usb_on_voltage - usb_off_voltage
        self.logger.info(f"Manual calibration: USB offset = {self.usb_voltage_offset:.4f}V")
    
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
    
    def set_compensation_parameters(self, **kwargs):
        """보정 파라미터 설정"""
        if 'usb_voltage_offset' in kwargs:
            self.usb_voltage_offset = float(kwargs['usb_voltage_offset'])
        if 'compensation_factor' in kwargs:
            self.compensation_factor = float(kwargs['compensation_factor'])
        if 'interference_threshold' in kwargs:
            self.interference_threshold = float(kwargs['interference_threshold'])
        if 'auto_compensation_enabled' in kwargs:
            self.auto_compensation_enabled = bool(kwargs['auto_compensation_enabled'])
        if 'learning_mode_enabled' in kwargs:
            self.learning_mode_enabled = bool(kwargs['learning_mode_enabled'])
        
        self.logger.info("Compensation parameters updated")
    
    def reset_learning_data(self):
        """학습 데이터 초기화"""
        self.voltage_history.clear()
        self.usb_connected_measurements.clear()
        self.usb_disconnected_measurements.clear()
        self.usb_voltage_offset = 0.0
        self.logger.info("Learning data reset")
    
    def export_learning_data(self) -> Dict:
        """학습 데이터 내보내기"""
        return {
            'voltage_history': self.voltage_history.copy(),
            'usb_connected_measurements': self.usb_connected_measurements.copy(),
            'usb_disconnected_measurements': self.usb_disconnected_measurements.copy(),
            'usb_voltage_offset': self.usb_voltage_offset,
            'compensation_factor': self.compensation_factor,
            'timestamp': time.time()
        }
    
    def import_learning_data(self, data: Dict):
        """학습 데이터 가져오기"""
        try:
            self.voltage_history = data.get('voltage_history', [])
            self.usb_connected_measurements = data.get('usb_connected_measurements', [])
            self.usb_disconnected_measurements = data.get('usb_disconnected_measurements', [])
            self.usb_voltage_offset = data.get('usb_voltage_offset', 0.0)
            self.compensation_factor = data.get('compensation_factor', 1.0)
            self.logger.info("Learning data imported successfully")
        except Exception as e:
            self.logger.error(f"Failed to import learning data: {e}")


# 편의 함수들
def create_usb_mitigation_service() -> USBInterferenceMitigation:
    """USB 간섭 완화 서비스 생성"""
    return USBInterferenceMitigation()


def suggest_usb_cable_solution() -> str:
    """USB 케이블 솔루션 제안"""
    return """
    USB 전압 간섭 완화를 위한 하드웨어 솔루션:
    
    1. USB 데이터 전용 케이블 사용
       - USB Type-A to Micro-USB/USB-C 데이터 전용 케이블
       - 5V, GND 핀이 연결되지 않은 케이블
       - 또는 기존 케이블의 5V 라인을 물리적으로 차단
    
    2. USB 아이솔레이터 사용
       - USB 신호 아이솔레이터 (예: ADUM4160)
       - 전기적 격리를 통한 간섭 차단
       - 데이터 신호는 유지하면서 전원 분리
    
    3. 외부 전원 공급
       - 디바이스에 별도의 안정화된 전원 공급
       - USB는 순수 통신 목적으로만 사용
       - 배터리 시뮬레이터나 정밀 전원 공급장치 사용
    """


if __name__ == "__main__":
    # 테스트 코드
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # USB 간섭 완화 서비스 생성 및 테스트
    mitigation = create_usb_mitigation_service()
    
    def on_mode_changed(mode):
        print(f"Measurement mode changed: {mode}")
    
    def on_usb_state_changed(state):
        print(f"USB state changed: {state}")
    
    def on_interference_detected(level):
        print(f"Interference detected: {level:.4f}V")
    
    def on_compensation_applied(raw, compensated):
        print(f"Compensation applied: {raw:.4f}V -> {compensated:.4f}V")
    
    # 시그널 연결
    mitigation.measurement_mode_changed.connect(on_mode_changed)
    mitigation.usb_state_changed.connect(on_usb_state_changed)
    mitigation.interference_detected.connect(on_interference_detected)
    mitigation.compensation_applied.connect(on_compensation_applied)
    
    # 모니터링 시작
    mitigation.start_monitoring()
    
    # 테스트 측정값들
    test_voltages = [4.15, 4.18, 4.12, 4.20, 4.16, 4.14, 4.17, 4.13]
    
    print("Testing USB interference mitigation...")
    print(suggest_usb_cable_solution())
    
    for i, voltage in enumerate(test_voltages):
        usb_connected = (i % 2 == 0)  # 교대로 USB 연결/해제 시뮬레이션
        
        # 간섭 패턴 학습
        mitigation.learn_interference_pattern(voltage, usb_connected)
        
        # 전압 보정
        compensated = mitigation.compensate_voltage_measurement(voltage)
        
        print(f"Measurement {i+1}: {voltage:.3f}V -> {compensated:.3f}V (USB: {'ON' if usb_connected else 'OFF'})")
        
        time.sleep(0.5)
    
    # 보정 정보 출력
    info = mitigation.get_compensation_info()
    print(f"\nCompensation Info: {info}")
    
    sys.exit(0)