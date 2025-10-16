
import sys, time, math
from PyQt6 import QtWidgets
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QTimer
from generated import main_ui
from services.hvpm import HvpmService
from services import theme, adb
from collections import deque
import pyqtgraph as pg

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = main_ui.Ui_MainWindow()
        self.ui.setupUi(self)

        # 다크 테마
        theme.apply_theme(self)

        # HVPM 서비스
        self.hvpm_service = HvpmService(
            combo=self.ui.hvpm_CB,
            status_label=self.ui.hvpmStatus_LB,
            volt_label=self.ui.hvpmVolt_LB,
            volt_entry=self.ui.hvpmVolt_LE
        )

        # ----- Graph UI -----
        self._plot = pg.PlotWidget(title="HVPM Live Voltage (V)")
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.setLabel("bottom", "Time", units="s")
        self._plot.setLabel("left", "Voltage", units="V")
        self._curve_v = self._plot.plot()  # 전압 곡선

        # graphContainer 안의 graphLayout에 삽입
        self.ui.graphLayout.addWidget(self._plot)

        # 버퍼/타이머
        self._t0 = None
        self._tbuf = deque(maxlen=600)   # 10Hz*60s = 최근 1분
        self._vbuf = deque(maxlen=600)
        self._graphActive = False
        self._graphTimer = QTimer(self)
        self._graphTimer.setInterval(100)        # 10 Hz UI 업데이트
        self._graphTimer.timeout.connect(self._on_graph_tick)

        # __init__ 내 그래프 위젯 만들 때 곡선 생성 라인 교체
        self._curve_v = self._plot.plot(pen=pg.mkPen(width=2))  # 전압 곡선 두껍게
        self._plot.enableAutoRange('y', True)

        # 버튼 결선 (이미 연결돼 있다면 이 부분 생략해도 OK)
        if hasattr(self.ui, "startGraph_PB"):
            self.ui.startGraph_PB.clicked.connect(self.start_graph)
        if hasattr(self.ui, "stopGraph_PB"):
            self.ui.stopGraph_PB.clicked.connect(self.stop_graph)

        # ADB 상태
        self.selected_device = None
        self._refreshing_adb = False

        # 시그널
        self.ui.port_PB.clicked.connect(self.on_refresh_clicked)
        self.ui.readVolt_PB.clicked.connect(self.handle_read_voltage)
        self.ui.setVolt_PB.clicked.connect(self.handle_set_voltage)
        self.ui.comport_CB.currentIndexChanged.connect(self._on_device_selected)

        # 시작: ADB/HVPM 연결 + 초기 전압 읽기
        self.refresh_adb_ports()
        self.hvpm_service.refresh_ports(log_callback=self._log)

        v0 = self.hvpm_service.read_voltage(log_callback=self._log)
        if v0 is not None:
            self.hvpm_service.last_set_vout = v0
            self.hvpm_service.enabled = v0 > 0
            self.hvpm_service._update_volt_label()
            self._log(f"[HVPM] Initial voltage: {v0:.2f} V", "info")
        else:
            self.hvpm_service.last_set_vout = None
            self.hvpm_service.enabled = False
            self.hvpm_service._update_volt_label()
            self._log("[HVPM] Read failed on startup (DERR1)", "warn")

    # ---------- 로그 ----------
    def _log(self, msg: str, level: str = "info"):
        item = QtWidgets.QListWidgetItem(msg)
        if level == "error":
            item.setForeground(QColor("red"))
        elif level == "warn":
            item.setForeground(QColor("orange"))
        elif level == "info":
            item.setForeground(QColor("lightgreen"))
        self.ui.log_LW.addItem(item)
        self.ui.log_LW.scrollToBottom()

    def on_refresh_clicked(self):
        # 1) ADB 새로고침
        self.refresh_adb_ports()
        # 2) HVPM 새로고침
        self.hvpm_service.refresh_ports(log_callback=self._log)

        # 3) 상태 반영: 전압 1회 읽기(성공 시 라벨·상태 갱신)
        v = self.hvpm_service.read_voltage(log_callback=self._log)
        if v is not None:
            self.hvpm_service.last_set_vout = v
            self.hvpm_service.enabled = v > 0
            self.hvpm_service._update_volt_label()
            self._log(f"[HVPM] Current voltage: {v:.2f} V", "info")
        else:
            # 연결이 끊겼거나 샘플 없음
            self.hvpm_service.last_set_vout = None
            self.hvpm_service.enabled = False
            self.hvpm_service._update_volt_label()
            self._log("[HVPM] Read failed after refresh (DERR1)", "warn")

# ---------- Graph ----------
    def start_graph(self):
        if self._graphActive:
            return
        self._tbuf.clear(); self._vbuf.clear()
        self._t0 = time.perf_counter()
        # 동시 접근 충돌 방지: 수동 읽기 버튼이 있으면 잠시 비활성화
        if hasattr(self.ui, "readVolt_PB"):
            self.ui.readVolt_PB.setEnabled(False)
        self._graphActive = True
        self._graphTimer.start()
        self._log("Graph: start (10 Hz)")

    def stop_graph(self):
        if not self._graphActive:
            return
        self._graphTimer.stop()
        self._graphActive = False
        if hasattr(self.ui, "readVolt_PB"):
            self.ui.readVolt_PB.setEnabled(True)
        self._log("Graph: stop")

    def _on_graph_tick(self):
        try:
            # 연결 안돼 있으면 패스 (필요하면 주석처리)
            if not hasattr(self, "hvpm") or not self.hvpm.is_connected():
                return

            v = self.hvpm.read_voltage_quick()
            # None/NaN/비수치 방어
            try:
                v = float(v)
            except Exception:
                v = float("nan")
            if not math.isfinite(v):
                if not hasattr(self, "_graphWarnedNaN") or not self._graphWarnedNaN:
                    self._graphWarnedNaN = True
                    self._log("그래프: 전압이 NaN으로 들어와서 스킵(한번만 알림)")
                return

            t = time.perf_counter() - (self._t0 or time.perf_counter())
            self._tbuf.append(t); self._vbuf.append(v)

            # ★ 핵심: deque → list로 변환해서 setData
            self._curve_v.setData(list(self._tbuf), list(self._vbuf))

            # Y축 범위 강제(평평하면 보정)
            vmin = min(self._vbuf); vmax = max(self._vbuf)
            if vmin == vmax:
                pad = max(0.05, abs(vmax) * 0.05)
                vmin -= pad; vmax += pad
            self._plot.setYRange(vmin, vmax, padding=0.05)

            # X축 최근 30초
            tmax = self._tbuf[-1] if self._tbuf else 30.0
            self._plot.setXRange(max(0.0, tmax - 30.0), tmax, padding=0.01)

        except Exception as e:
            self._log(f"그래프 업데이트 실패: {e}")

# ---------- ADB ----------
    def refresh_adb_ports(self):
        self._refreshing_adb = True
        self.ui.comport_CB.clear()
        try:
            devices = adb.list_devices()
        except Exception as e:
            devices = []
            self._log(f"[ADB ERROR] {e}", "error")

        if devices:
            self.ui.comport_CB.addItems(devices)
            self.ui.comport_CB.setCurrentIndex(0)
            self.selected_device = devices[0]
            self._log(f"[ADB] Selected device: {self.selected_device}", "info")
        else:
            self.ui.comport_CB.addItem("-")
            self.selected_device = None
            self._log("[ADB] No device selected", "warn")
        self._refreshing_adb = False

    def _on_device_selected(self):
        if getattr(self, "_refreshing_adb", False):
            return
        self.selected_device = self.ui.comport_CB.currentText().strip()
        if self.selected_device and self.selected_device != "-":
            self._log(f"[ADB] Selected device: {self.selected_device}", "info")
        else:
            self._log("[ADB] No device selected", "warn")

    # ---------- HVPM ----------
    def handle_read_voltage(self):
        v = self.hvpm_service.read_voltage(log_callback=self._log)
        if v is not None:
            self.hvpm_service.last_set_vout = v
            self.hvpm_service.enabled = v > 0
            self.hvpm_service._update_volt_label()
            self._log(f"[HVPM] Current voltage: {v:.2f} V", "info")
        else:
            self._log("[HVPM DERR1] no volt samples", "warn")

    def handle_set_voltage(self):
        try:
            volts = float(self.ui.hvpmVolt_LE.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Voltage must be a number.")
            return
        ok = self.hvpm_service.set_voltage(volts, log_callback=self._log)
        if not ok:
            QtWidgets.QMessageBox.warning(self, "HVPM Error", "Failed to set/disable")
            return
        # 간단 리드백
        rb = self.hvpm_service.read_voltage(log_callback=self._log)
        if rb is not None:
            self.hvpm_service.last_set_vout = rb
            self.hvpm_service.enabled = rb > 0
            self.hvpm_service._update_volt_label()
            self._log(f"[HVPM] Readback: {rb:.2f} V", "info")

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
