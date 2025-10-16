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

        # ----- Graph UI (Voltage & Current) -----
        # Voltage plot
        self._plot_v = pg.PlotWidget(title="HVPM Voltage (V)")
        self._plot_v.showGrid(x=True, y=True, alpha=0.3)
        self._plot_v.setLabel("bottom", "Time", units="s")
        self._plot_v.setLabel("left", "Voltage", units="V")
        self._curve_v = self._plot_v.plot(pen=pg.mkPen(width=2))

        # Current plot
        self._plot_i = pg.PlotWidget(title="HVPM Current (A)")
        self._plot_i.showGrid(x=True, y=True, alpha=0.3)
        self._plot_i.setLabel("bottom", "Time", units="s")
        self._plot_i.setLabel("left", "Current", units="A")
        self._curve_i = self._plot_i.plot(pen=pg.mkPen(width=2, color='y'))

        # Add both plots to layout
        self.ui.graphLayout.addWidget(self._plot_v)
        self.ui.graphLayout.addWidget(self._plot_i)

        # 버퍼/타이머
        self._t0 = None
        self._tbuf = deque(maxlen=600)   # 10Hz*60s = 최근 1분
        self._vbuf = deque(maxlen=600)
        self._ibuf = deque(maxlen=600)
        self._graphActive = False
        self._graphTimer = QTimer(self)
        self._graphTimer.setInterval(100)        # 10 Hz UI 업데이트
        self._graphTimer.timeout.connect(self._on_graph_tick)

        self._plot_v.enableAutoRange('y', True)
        self._plot_i.enableAutoRange('y', True)

        # 버튼 결선 (이미 연결돼 있다면 이 부분 생략해도 OK)
        if hasattr(self.ui, "startGraph_PB"):
            self.ui.startGraph_PB.clicked.connect(self.start_graph)
        if hasattr(self.ui, "stopGraph_PB"):
            self.ui.stopGraph_PB.clicked.connect(self.stop_graph)

        # ADB 상태
        self.selected_device = None
        self._refreshing_adb = False

        # === 추가: Refresh 시 전압 동시 읽기 여부(기본 False → 읽지 않음)
        self._cfg_refresh_reads_voltage = False

        # 시그널
        self.ui.port_PB.clicked.connect(self.on_refresh_clicked)
        self.ui.readVolt_PB.clicked.connect(self.handle_read_voltage)
        self.ui.setVolt_PB.clicked.connect(self.handle_set_voltage)
        self.ui.comport_CB.currentIndexChanged.connect(self._on_device_selected)

        # 시작: ADB/HVPM 연결 + (연결된 경우에만) 초기 전압 읽기
        self.refresh_adb_ports()
        self.hvpm_service.refresh_ports(log_callback=self._log)

        if getattr(self.hvpm_service, "dev", None):  # ← 연결된 경우에만 읽기
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

        # 3) 상태 반영: 전압 읽기는 요청대로 Refresh에서 실행하지 않음
        #    (필요하면 self._cfg_refresh_reads_voltage = True 로 복구 가능)
        if getattr(self, "_cfg_refresh_reads_voltage", False):
            v = self.hvpm_service.read_voltage(log_callback=self._log)
            if v is not None:
                self.hvpm_service.last_set_vout = v
                self.hvpm_service.enabled = v > 0
                self.hvpm_service._update_volt_label()
                self._log(f"[HVPM] Current voltage: {v:.2f} V", "info")
            else:
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
            # 연결 안돼 있으면 패스
            if not getattr(self.hvpm_service, "dev", None):
                return

            # Read voltage and current together
            v, i = self.hvpm_service.read_vi(log_callback=self._log)

            # None/NaN/비수치 방어
            try:
                v = float(v) if v is not None else float("nan")
            except Exception:
                v = float("nan")
            try:
                i = float(i) if i is not None else float("nan")
            except Exception:
                i = float("nan")

            if not math.isfinite(v) and not math.isfinite(i):
                if not hasattr(self, "_graphWarnedNaN") or not self._graphWarnedNaN:
                    self._graphWarnedNaN = True
                    self._log("그래프: V/I가 NaN으로 들어와서 스킵(한번만 알림)")
                return

            t = time.perf_counter() - (self._t0 or time.perf_counter())
            self._tbuf.append(t)
            if math.isfinite(v):
                self._vbuf.append(v)
            if math.isfinite(i):
                self._ibuf.append(i)

            # Update plots
            self._curve_v.setData(list(self._tbuf), list(self._vbuf))
            self._curve_i.setData(list(self._tbuf), list(self._ibuf))

            # Y축 범위 강제(평평하면 보정)
            if len(self._vbuf) > 0:
                vmin = min(self._vbuf); vmax = max(self._vbuf)
                if vmin == vmax:
                    pad = max(0.05, abs(vmax) * 0.05)
                    vmin -= pad; vmax += pad
                self._plot_v.setYRange(vmin, vmax, padding=0.05)

            if len(self._ibuf) > 0:
                imin = min(self._ibuf); imax = max(self._ibuf)
                if imin == imax:
                    pad_i = max(0.01, abs(imax) * 0.1)
                    imin -= pad_i; imax += pad_i
                self._plot_i.setYRange(imin, imax, padding=0.05)

            # X축 최근 30초
            tmax = self._tbuf[-1] if self._tbuf else 30.0
            self._plot_v.setXRange(max(0.0, tmax - 30.0), tmax, padding=0.01)
            self._plot_i.setXRange(max(0.0, tmax - 30.0), tmax, padding=0.01)

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