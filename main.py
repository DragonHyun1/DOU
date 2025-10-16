import sys, time, math
from PyQt6 import QtWidgets
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
        theme.apply_theme(self)

        # HVPM Service
        self.hvpm = HvpmService(
            getattr(self.ui, "hvpm_CB", None),
            getattr(self.ui, "hvpmStatus_LB", None),
            getattr(self.ui, "hvpmVolt_LB", None),
            getattr(self.ui, "hvpmVolt_LE", None),
        )

        # 버튼 시그널 (DEV 유지)
        if hasattr(self.ui, "port_PB"):
            self.ui.port_PB.clicked.connect(self.on_refresh_clicked)
        if hasattr(self.ui, "hvpm_CB"):
            self.ui.hvpm_CB.currentTextChanged.connect(self._on_device_selected)
        if hasattr(self.ui, "readVolt_PB"):
            self.ui.readVolt_PB.clicked.connect(self.handle_read_voltage)
        if hasattr(self.ui, "setVolt_PB"):
            self.ui.setVolt_PB.clicked.connect(self.handle_set_voltage)

        # ===== 그래프 초기화 =====
        self._plot = pg.PlotWidget(title="HVPM Live Voltage (V)")
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._curve = self._plot.plot(pen=pg.mkPen(width=2))
        if hasattr(self.ui, "graphLayout"):
            self.ui.graphLayout.addWidget(self._plot)

        self._tbuf = deque(maxlen=600)   # 10 Hz * 60s
        self._vbuf = deque(maxlen=600)
        self._t0 = None

        self._timer = QTimer(self)       # 인스턴스 보유로 GC 방지
        self._timer.setInterval(100)     # 10 Hz
        self._timer.timeout.connect(self._on_graph_tick)

        # 그래프 버튼 연결(기존 슬롯 유지, disconnect 호출 없음)
        if hasattr(self.ui, "startGraph_PB"):
            self.ui.startGraph_PB.clicked.connect(self.start_graph)
        if hasattr(self.ui, "stopGraph_PB"):
            self.ui.stopGraph_PB.clicked.connect(self.stop_graph)

        # 상태 플래그
        self._is_streaming = False

        # 앱 시작 시: DEV 흐름 유지 + 연결돼 있으면 초기 전압 표시
        QTimer.singleShot(0, self._initial_probe)

    # DEV 로그 스타일: 단순 addItem
    def _log(self, msg: str):
        try:
            if hasattr(self.ui, "log_LW"):
                self.ui.log_LW.addItem(msg)
                self.ui.log_LW.scrollToBottom()
            else:
                print(msg)
        except Exception:
            print(msg)

    # 디바운스 유틸
    def _debounce(self, widget, ms=500):
        try:
            widget.setEnabled(False)
            QTimer.singleShot(ms, lambda: widget.setEnabled(True))
        except Exception:
            pass

    # 시작 프로브: 장비/ADB 스캔 + 초기 전압
    def _initial_probe(self):
        self._log("Initial probe: scanning HVPM & test device...")
        try:
            ports = self.hvpm.refresh_ports()
            self._log(f"HVPM ports: {ports if ports else 'none'}")
        except Exception as e:
            self._log(f"HVPM refresh 실패: {e}")
        try:
            if hasattr(adb, "refresh_ports"):
                adb.refresh_ports(self.ui)
        except Exception:
            pass
        # 연결돼 있으면 약간 지연 후 초기 전압 표시 (타이밍 여유)
        if getattr(self.hvpm, "dev", None):
            QTimer.singleShot(150, self._initial_voltage_read)

    def _initial_voltage_read(self):
        try:
            v = float(self.hvpm.read_voltage())
            self._log(f"Initial Vout: {v:.3f} V")
            if hasattr(self.ui, "hvpmVolt_LB"):
                self.ui.hvpmVolt_LB.setText(f"{v:.3f} V")
        except Exception as e:
            self._log(f"Initial voltage read 실패: {e}")

    def on_refresh_clicked(self):
        # 버튼 스팸 방지
        if hasattr(self.ui, "port_PB"):
            self._debounce(self.ui.port_PB, 500)
        # 스트리밍 중에는 포트 스캔 금지
        if self._is_streaming:
            self._log("skip refresh: streaming in progress")
            return
        try:
            self.hvpm._safe_close()
        except Exception:
            pass
        try:
            ports = self.hvpm.refresh_ports()
            self._log(f"HVPM ports: {ports if ports else 'none'}")
        except Exception as e:
            self._log(f"HVPM refresh 실패: {e}")
        try:
            if hasattr(adb, "refresh_ports"):
                adb.refresh_ports(self.ui)
        except Exception:
            pass

    # ===== 그래프 동작 =====
    def start_graph(self):
        if self._timer.isActive() or self._is_streaming:
            return
        self._is_streaming = True

        # 충돌 위험 제어: 스트리밍 중 UI 조작 잠금
        for name in ("readVolt_PB", "setVolt_PB", "port_PB", "hvpm_CB"):
            w = getattr(self.ui, name, None)
            if hasattr(w, "setEnabled"): w.setEnabled(False)

        self._tbuf.clear(); self._vbuf.clear()
        self._t0 = time.perf_counter()

        # 첫 포인트 즉시 갱신(빈 화면 방지)
        self._on_graph_tick()
        self._plot.enableAutoRange(x=True, y=True)

        self._timer.start()
        self._log("Graph start (10 Hz)")

    def stop_graph(self):
        if not self._timer.isActive():
            return
        self._timer.stop()
        self._is_streaming = False

        # UI 잠금 해제
        for name in ("readVolt_PB", "setVolt_PB", "port_PB", "hvpm_CB"):
            w = getattr(self.ui, name, None)
            if hasattr(w, "setEnabled"): w.setEnabled(True)

        self._log("Graph stop")

    def _on_graph_tick(self):
        # 스트리밍 중 아닌 경우 방어
        if not self._is_streaming:
            return
        try:
            v = float(self.hvpm.read_voltage())
        except Exception:
            return
        if not math.isfinite(v):
            return

        t = time.perf_counter() - (self._t0 or time.perf_counter())
        self._tbuf.append(t); self._vbuf.append(v)
        self._curve.setData(list(self._tbuf), list(self._vbuf))

        # 최근 30초 창 유지
        tmax = self._tbuf[-1]
        self._plot.setXRange(max(0.0, tmax - 30.0), tmax, padding=0.01)

    # ===== 나머지 핸들러 (DEV 유지) =====
    def refresh_adb_ports(self):
        try:
            if hasattr(adb, "refresh_ports"):
                adb.refresh_ports(self.ui)
        except Exception as e:
            self._log(f"ADB refresh 실패: {e}")

    def _on_device_selected(self, text: str):
        self._log(f"device selected: {text}")

    def handle_read_voltage(self):
        if self._is_streaming:
            self._log("skip read: streaming in progress")
            return
        try:
            v = float(self.hvpm.read_voltage())
            self._log(f"Vout: {v:.3f} V")
            if hasattr(self.ui, "hvpmVolt_LB"):
                self.ui.hvpmVolt_LB.setText(f"{v:.3f} V")
        except Exception as e:
            self._log(f"전압 읽기 실패: {e}")

    def handle_set_voltage(self):
        if self._is_streaming:
            self._log("skip set: streaming in progress")
            return
        try:
            txt = self.ui.hvpmVolt_LE.text().strip() if hasattr(self.ui, "hvpmVolt_LE") else ""
            v = float(txt) if txt else 0.0
            self.hvpm.set_voltage(v)
            self._log(f"Vout set → {v:.3f} V")
        except Exception as e:
            self._log(f"전압 설정 실패: {e}")

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()