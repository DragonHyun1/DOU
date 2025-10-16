# SYNC_BASE: 10/14 A
# FILE: services/hvpm.py
# FUNCS: __init__, _set_status, _update_volt_label, _safe_close, _try_call,
#        _set_limits_max, refresh_ports, _median, _floats_tail,
#        _enable_voltage_minimal, read_voltage_once_channel_major,
#        read_voltage, set_voltage

import time
from PyQt6 import QtWidgets
from Monsoon import HVPM, sampleEngine

class HvpmService:
    def __init__(self, combo, status_label, volt_label, volt_entry):
        self.combo = combo
        self.status_label = status_label
        self.volt_label = volt_label
        self.volt_entry = volt_entry
        self.dev = None
        self.se = None

    def _set_status(self, txt: str):
        try:
            if self.status_label: self.status_label.setText(txt)
        except Exception: pass

    def _update_volt_label(self, v: float):
        try:
            if self.volt_label: self.volt_label.setText(f"{float(v):.3f} V")
        except Exception: pass

    def _safe_close(self):
        if self.dev:
            try: self.dev.closeDevice()
            except Exception: pass
        self.dev = None; self.se = None
        self._set_status("disconnected")

    def _try_call(self, fn, *a, **k):
        try: return fn(*a, **k)
        except Exception: return None

    def _set_limits_max(self):
        self._try_call(getattr(self.dev, "setPowerUpCurrentLimit", lambda *_: None), 0)
        self._try_call(getattr(self.dev, "setMaxAdcRate", lambda *_: None), 5000)

    def refresh_ports(self) -> list[str]:
        ports = []
        try:
            for n in ("listDevices","ListDevices","EnumerateDevices","enumerateDevices",
                      "findDevices","FindDevices","getConnectedDevices","GetConnectedDevices"):
                fn = getattr(HVPM, n, None)
                if callable(fn):
                    res = fn() or []
                    if isinstance(res, (list, tuple)) and res:
                        ports = [str(x) for x in res]; break
        except Exception:
            ports = []
        try:
            if self.combo:
                self.combo.clear()
                if ports: self.combo.addItems(ports)
        except Exception: pass
        self._safe_close()
        if ports:
            try:
                self.dev = HVPM.Monsoon()
                sn = int(ports[0]) if ports[0].isdigit() else None
                self.dev.setup_usb(sn); self._set_limits_max()
                self.se = self._try_call(sampleEngine.SampleEngine, self.dev)
                if self.se: self._try_call(self.se.ConsoleOutput, False)
                self._set_status("connected")
            except Exception:
                self._set_status("ready")
        else:
            self._set_status("no device")
        return ports

    def _median(self, arr):
        if not arr: return float("nan")
        s = sorted(arr); n = len(s); m = n // 2
        return s[m] if n % 2 else 0.5 * (s[m - 1] + s[m])

    def _floats_tail(self, seq, take=1):
        try: return [float(x) for x in (seq[-take:] if len(seq) >= take else seq)]
        except Exception: return []

    def _enable_voltage_minimal(self):
        self._try_call(getattr(self.dev, "setPowerOn", lambda *_: None))

    def read_voltage_once_channel_major(self) -> float:
        if not self.dev: raise RuntimeError("HVPM not connected")
        if not self.se: return float(self._try_call(self.dev.getVout) or float("nan"))
        s = self._try_call(self.se.getSamples) or {}
        for k in ("voltage", "MainVoltage", "USBVoltage"):
            if isinstance(s, dict) and k in s and s[k]:
                return float(s[k][-1])
        if isinstance(s, (list, tuple)) and s:
            try:
                cand = s[4] if len(s) > 4 and s[4] else s[0]
                return float(cand[-1]) if cand else float("nan")
            except Exception: pass
        return float("nan")

    def read_voltage(self) -> float:
        v = self.read_voltage_once_channel_major()
        if not (v == v):
            v = float(self._try_call(self.dev.getVout) or float("nan"))
        return float(v)

    def set_voltage(self, vout: float):
        if not self.dev: raise RuntimeError("HVPM not connected")
        v = float(vout)
        if v <= 0.0:
            self._try_call(self.dev.setPowerOff)
            self._try_call(getattr(self.dev, "usbPassthroughEnable", lambda *_: None), False)
            self._update_volt_label(0.0); return
        v = max(0.8, min(5.5, v))
        self._enable_voltage_minimal()
        self._try_call(self.dev.setVout, v)
        self._update_volt_label(v)
