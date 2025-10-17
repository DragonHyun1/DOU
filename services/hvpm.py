# DOU/services/hvpm.py
import time
from PyQt6 import QtWidgets
from Monsoon import HVPM, sampleEngine

class HvpmService:
    def __init__(self, combo: QtWidgets.QComboBox,
                 status_label: QtWidgets.QLabel,
                 volt_label: QtWidgets.QLabel,
                 volt_entry: QtWidgets.QLineEdit):
        self.combo = combo
        self.status_label = status_label
        self.volt_label = volt_label
        self.volt_entry = volt_entry
        self.pm = None
        self.engine = None
        self.serialno = None

        self.enabled = False
        self.last_set_vout = None
        self.last_read_voltage = None
        self.last_read_current = None

    def is_connected(self):
        """Check if HVPM device is connected and ready"""
        return bool(self.pm and self.engine)

    # -------- UI helpers --------
    def _set_status(self, text: str, ok: bool):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color:{'lightgreen' if ok else 'red'};font-weight:bold;"
        )

    def _update_volt_label(self):
        self.volt_label.setText(
            "-" if self.last_set_vout is None else f"{self.last_set_vout:.2f} V"
        )

    # -------- lifecycle --------
    def _safe_close(self):
        try:
            if self.engine and hasattr(self.engine, "stopSampling"):
                self.engine.stopSampling()
        except Exception:
            pass
        try:
            if self.pm and hasattr(self.pm, "closeDevice"):self.pm.closeDevice()
        except Exception:
            pass
        self.engine = None
        self.pm = None
        time.sleep(0.2)

    # === PATCH: max-limit helpers ===
    def _try_call(self, obj, name, *args, **kw):
        fn = getattr(obj, name, None)
        if not callable(fn):
            return False, f"{name}:notfound"
        try:
            fn(*args, **kw)
            return True, name
        except Exception as e:
            return False, f"{name}:{e}"

    def _set_limits_max(self, log_callback=None):
        """
        초기 부팅/전압 올릴 때 보호동작 방지용 '최대값' 적용.
        - time: 255 ms
        - power-up current limit: 15.625 A
        - run-time current limit: 16.625 A
        SDK 0.1.88에서 함수명이 다를 수 있어 여러 이름을 순차 시도.
        단위도 ms / µs, A / mA / µA 모두 대응.
        """
        if not self.pm:
            if log_callback: log_callback("[HVPM] no device for _set_limits_max", "warn")
            return False

        t_ms  = 255
        pu_A  = 16.625
        rt_A  = 16.625

        # Power-up time
        for name, val in [
            ("setPowerUpTime", t_ms),                 # ms
            ("setPowerUpTimeInMs", t_ms),
            ("setPowerUpTime_us", int(t_ms * 1000)), # µs
        ]:
            ok, tag = self._try_call(self.pm, name, val)
            if log_callback:
                lvl = "info" if ok else "warn"
                log_callback(f"[HVPM] {name}({val}) -> {('OK' if ok else tag)}", lvl)
            if ok: break

        # Power-up current limit
        for name, val in [
            ("setPowerUpCurrentLimit",      int(pu_A * 1000)),     # mA
            ("setPowerUpCurrentLimit_mA",   int(pu_A * 1000)),
            ("setPowerUpCurrentLimit_uA",   int(pu_A * 1_000_000)),
            ("setPowerUpCurrentLimitA",     float(pu_A)),          # A
        ]:
            ok, tag = self._try_call(self.pm, name, val)
            if log_callback:
                lvl = "info" if ok else "warn"
                log_callback(f"[HVPM] {name}({val}) -> {('OK' if ok else tag)}", lvl)
            if ok: break

        # Run-time current limit
        for name, val in [
            ("setRunTimeCurrentLimit",      int(rt_A * 1000)),     # mA
            ("setRunTimeCurrentLimit_mA",   int(rt_A * 1000)),
            ("setRunTimeCurrentLimit_uA",   int(rt_A * 1_000_000)),
            ("setRunTimeCurrentLimitA",     float(rt_A)),          # A
        ]:
            ok, tag = self._try_call(self.pm, name, val)
            if log_callback:
                lvl = "info" if ok else "warn"
                log_callback(f"[HVPM] {name}({val}) -> {('OK' if ok else tag)}", lvl)
            if ok: break

        return True
    # === END PATCH ===

    def refresh_ports(self, log_callback=None):
        """장비 재탐색 + UI 갱신. 장비가 꺼져있으면 즉시 Not Connected 처리."""
        # 콤보 클리어 & 안전 종료
        try:
            self.combo.clear()
        except Exception:
            pass
        self._safe_close()

        # 재연결 시도
        try:
            self.pm = HVPM.Monsoon()
            # 장비가 꺼져있으면 여기서 예외가 나거나 내부 USB 에러가 납니다.
            self.pm.setup_usb()

            self.engine = sampleEngine.SampleEngine(self.pm)
            # 노이즈 차단
            try:
                if hasattr(self.engine, "ConsoleOutput"):
                    self.engine.ConsoleOutput(False)
            except Exception:
                pass
            try:
                if hasattr(self.engine, "disableCSVOutput"):
                    self.engine.disableCSVOutput()
            except Exception:
                pass

            # 필수 채널만 활성
            ch = sampleEngine.channels
            for c in (ch.MainCurrent, ch.MainVoltage):
                try: self.engine.enableChannel(c)
                except Exception: pass

            # 짧은 프로브(장치가 실제로 응답하는지 확인)
            probe_ok = False
            try:
                self.engine.startSampling(20)
                data = self.engine.getSamples() or []
                probe_ok = bool(data)
            except Exception:
                probe_ok = False

            if not probe_ok:
                # 프로브 실패 → 연결 실패로 간주
                raise RuntimeError("probe failed (no samples)")

            # 시리얼 표시
            self.serialno = (self.pm.getSerialNumber()
                            if hasattr(self.pm, "getSerialNumber")
                            else getattr(self.pm, "serialno", None))
            shown = str(self.serialno) if self.serialno else "-"
            try:
                self.combo.addItem(shown)
            except Exception:
                pass

            self._set_status("Connected ✅", True)
            if log_callback:
                self._log = log_callback  # 선택: 내부 저장
                log_callback(f"[HVPM] Connected, serial={shown}", "info")

        except Exception as e:
            # 연결 실패 경로: UI를 바로 Not Connected로
            try:
                self.combo.addItem("-")
            except Exception:
                pass
            self._set_status("Not Connected ❌", False)
            self.engine = None
            self.pm = None
            if log_callback:
                log_callback(f"[HVPM] refresh error: {e}", "error")


# -------- voltage read (channel-major) --------
    def _median(self, arr):
        if not arr: return None
        s = sorted(arr); n = len(s)
        return s[n//2] if n % 2 else 0.5 * (s[n//2-1] + s[n//2])

    def _floats_tail(self, seq, tail=120):
        out = []
        if not seq: return out
        seq = seq[-tail:] if len(seq) > tail else seq
        for x in seq:
            try: out.append(float(x))
            except Exception: pass
        return out

    def _enable_voltage_minimal(self):
        if not self.engine: return
        ch = sampleEngine.channels
        for c in (ch.USBCurrent, ch.AuxCurrent, ch.USBVoltage):
            try: self.engine.disableChannel(c)
            except Exception: pass
        for c in (ch.MainCurrent, ch.MainVoltage):
            try: self.engine.enableChannel(c)
            except Exception: pass

    def read_voltage_once_channel_major(self, nsamp=700, tail=140, warmup_ms=180, log_callback=None):
        if not (self.pm and self.engine):
            if log_callback: log_callback("[HVPM] engine/pm not ready", "warn")
            return None
        ch = sampleEngine.channels

        # 스트림 미사용: 1회 캡처
        self._enable_voltage_minimal()
        try:
            if warmup_ms and warmup_ms > 0:
                time.sleep(warmup_ms/1000.0)
            self.engine.startSampling(int(nsamp))
            data = self.engine.getSamples() or []
            mv = data[ch.MainVoltage] if len(data) > ch.MainVoltage else []
            vals = self._floats_tail(mv, tail=tail)
            v = self._median(vals)
            if v is None and log_callback:
                log_callback("[HVPM DERR1] no volt samples", "warn")
            return None if v is None else round(v, 2)
        except Exception as e:
            if log_callback: log_callback(f"[HVPM] capture failed: {e}", "error")
            return None

    def read_voltage(self, log_callback=None):
        v = self.read_voltage_once_channel_major(nsamp=700, tail=140, warmup_ms=180, log_callback=log_callback)
        if v is not None:
            return v
        return self.read_voltage_once_channel_major(nsamp=1200, tail=200, warmup_ms=300, log_callback=log_callback)

    # -------- dual-channel VI read --------
    def read_vi_once_channel_major(self, nsamp=700, tail=140, warmup_ms=180, log_callback=None):
        """
        Capture once and return (voltage[V], current[A]) using channel-major access.
        Both channels are enabled to ensure synchronous sampling.
        """
        if not (self.pm and self.engine):
            if log_callback: log_callback("[HVPM] engine/pm not ready", "warn")
            return None, None
        ch = sampleEngine.channels

        # Ensure only required channels are enabled
        self._enable_voltage_minimal()
        try:
            if warmup_ms and warmup_ms > 0:
                time.sleep(warmup_ms/1000.0)
            self.engine.startSampling(int(nsamp))
            data = self.engine.getSamples() or []
            mv = data[ch.MainVoltage] if len(data) > ch.MainVoltage else []
            mi = data[ch.MainCurrent] if len(data) > ch.MainCurrent else []
            vals_v = self._floats_tail(mv, tail=tail)
            vals_i = self._floats_tail(mi, tail=tail)
            v = self._median(vals_v)
            i = self._median(vals_i)
            if v is None and log_callback:
                log_callback("[HVPM DERR1] no volt samples", "warn")
            if i is None and log_callback:
                log_callback("[HVPM DERR2] no current samples", "warn")
            if v is not None:
                self.last_read_voltage = float(v)
            if i is not None:
                self.last_read_current = float(i)
            v_out = None if v is None else round(v, 2)
            i_out = None if i is None else round(i, 4)
            return v_out, i_out
        except Exception as e:
            if log_callback: log_callback(f"[HVPM] capture failed: {e}", "error")
            return None, None

    def read_vi(self, log_callback=None):
        v, i = self.read_vi_once_channel_major(nsamp=700, tail=140, warmup_ms=180, log_callback=log_callback)
        if v is not None and i is not None:
            return v, i
        return self.read_vi_once_channel_major(nsamp=1200, tail=200, warmup_ms=300, log_callback=log_callback)

    # -------- set voltage --------
    def set_voltage(self, volts: float, log_callback=None) -> bool:
        if not self.pm:
            if log_callback: log_callback("[HVPM ERROR] Device not connected", "error")
            return False
        try:
            v = float(volts)
        except Exception:
            if log_callback: log_callback("[HVPM ERROR] invalid input", "error")
            return False
        v = max(0.0, min(5.5, v))

        # 0V → 출력 끄기
        if v <= 0.0:
            try:
                if hasattr(self.pm, "setVout"):
                    self.pm.setVout(0.0)
                self.last_set_vout = 0.0
                self.enabled = False
                self._update_volt_label()
                if log_callback: log_callback("[HVPM] Vout set 0.00 V (OFF)", "info")
                return True
            except Exception as e:
                if log_callback: log_callback(f"[HVPM ERR34] setVout(0) failed: {e}", "error")
                return False

        # ★ 핵심: 전압을 올리기 전에 리밋을 '최대치'로
        self._set_limits_max(log_callback=log_callback)

        # (선택) 필요 시 USB 역급전 차단/램핑 로직을 여기 추가 가능
        try:
            if hasattr(self.pm, "setVout"):
                self.pm.setVout(v)
            else:
                raise RuntimeError("setVout not available in SDK")
            self.last_set_vout = v
            self.enabled = True
            self._update_volt_label()
            if log_callback: log_callback(f"[HVPM] Vout set {v:.2f} V", "info")
            return True
        except Exception as e:
            if log_callback: log_callback(f"[HVPM ERR34] setVout-failed: {e}", "error")
            return False
