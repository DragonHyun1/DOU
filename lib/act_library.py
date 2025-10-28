# lib/act_library.py
from .device import Device
from .utils import EvalContext


class ActLibrary:
    """
    Implement each @xxx defined in 00_ACT_Library.txt as methods.
    All methods receive (ctx:EvalContext, dev:Device) as parameters
    to access global variable and expression storage.
    """

    def __init__(self):
        # Global flags (DSL $xxxx) - unrelated to actual operation, use when needed
        self.flags = {
            "PointerLocation": False,
            "TopLayerScriptView": False,
            "IgnoreError": True,
            "TouchBoosterEnable": False,
            "FullcapUpload": False,
        }

    # -------------------------------------------------
    # Basic settings (default_setting)
    # -------------------------------------------------
    def default_setting(self, ctx: EvalContext, dev: Device):
        dev.shell("settings put system screen_off_timeout 600000")
        dev.shell("settings put system multi_control_enabled 0")
        dev.shell("settings put system quickshare 0")
        # Launch ShareLive screen (example)
        dev.shell(
            "am start -n com.samsung.android.app.sharelive/.presentation.settings.SettingsActivity"
        )
        dev.sleep(500)

        # “Show available devices on share panel” 체크 여부
        if dev.click({"textMatches": r"\QShow available devices on share panel\E"}):
            dev.log("share-panel option ON")
        dev.sleep(500)

        dev.shell("am start -n com.android.settings")
        dev.press("home")
        dev.shell("settings put system brightness_mode 0")
        # indoor_500 calls function below (brightness file reading)
        self.indoor_500(ctx, dev)

        dev.shell("settings put system debug_aod_brightness 95")
        dev.shell("settings put system volume 7")
        dev.shell("settings put global bluetooth_on 1")
        dev.shell("settings put global nfc_on 1")
        dev.shell("settings put system accelerometer_rotation 1")
        dev.shell("settings put system rotation 1")
        dev.shell("svc wifi disable")
        dev.shell("settings put global airplane_mode_on 0")
        dev.shell("settings put global location_providers_allowed +gps")
        dev.sleep(800)

        dev.click({"textMatches": "(?i)Agree"})
        dev.click({"textMatches": "(?i)Turn on location"})

    # -------------------------------------------------
    # Battery basic settings (battary_default_setting) - same as default_setting
    # -------------------------------------------------
    battary_default_setting = default_setting

    # -------------------------------------------------
    # Screen size calculation (screen_size_check)
    # -------------------------------------------------
    def screen_size_check(self, ctx: EvalContext, dev: Device):
        ctx.set_var("blank", '" "', dev)                # String blank space
        size_check = dev.shell("wm size | grep Override || wm size | grep Physical")
        ctx.set_var("size_Check", size_check, dev)

        # “1234x5678” 형태 → split → get
        split = ctx.resolve("[split {size_Check} {blank}]", dev)
        get_size = ctx.resolve("[get {split} 2]", dev)
        split_sz = ctx.resolve("[split {get_size} x]", dev)

        ctx.set_var("screen_x", "[get {split_sz} 0]", dev)
        ctx.set_var("screen_y", "[get {split_sz} 1]", dev)

        # Derived coordinates
        ctx.set_var("center_x", "{screen_x} * 0.5", dev)
        ctx.set_var("center_y", "{screen_y} * 0.5", dev)
        ctx.set_var("right_x", "{screen_x} * 0.75", dev)
        ctx.set_var("left_x", "{screen_x} * 0.25", dev)
        ctx.set_var("y_upper", "{screen_y} / 5", dev)
        ctx.set_var("y_lower", "{screen_y} - {screen_y} / 5", dev)
        ctx.set_var("x_landscape", "{screen_y}", dev)
        ctx.set_var("y_landscape", "{screen_x}", dev)
        ctx.set_var("y_lower_landscape", "{screen_x} - {screen_x} / 5", dev)
        ctx.set_var("x_right_landscape", "{screen_y} - {screen_y} / 6", dev)

    # -------------------------------------------------
    # Brightness file reading (indoor_500 / indoor_default / outdoor_2300 / hbm_5000 / hbm_20000)
    # -------------------------------------------------
    def _set_brightness_from_file(self, ctx: EvalContext, dev: Device, path: str):
        ctx.set_var("indoor", f"[doshell cat {path}]", dev)
        dev.shell(f"cmd display set-brightness {ctx.vars['indoor']}")

    def indoor_500(self, ctx: EvalContext, dev: Device):
        self._set_brightness_from_file(ctx, dev, "/sdcard/indoor.txt")

    def indoor_default(self, ctx: EvalContext, dev: Device):
        self._set_brightness_from_file(ctx, dev, "/sdcard/indoor_500.txt")

    def outdoor_2300(self, ctx: EvalContext, dev: Device):
        self._set_brightness_from_file(ctx, dev, "/sdcard/outdoor.txt")

    def hbm_5000(self, ctx: EvalContext, dev: Device):
        self._set_brightness_from_file(ctx, dev, "/sdcard/hbm_mid.txt")

    def hbm_20000(self, ctx: EvalContext, dev: Device):
        self._set_brightness_from_file(ctx, dev, "/sdcard/hbm.txt")

    # -------------------------------------------------
    # Wi-Fi settings (set_wifi_2_4, set_b_wifi_2_4, set_wifi_5, set_b_wifi_5)
    # -------------------------------------------------
    def set_wifi_2_4(self, ctx: EvalContext, dev: Device):
        ctx.set_var("wifi_2_4", "[doshell cat /sdcard/wifi2.txt]", dev)
        dev.shell("svc wifi disable")
        dev.sleep(1000)
        dev.shell(
            f"svc wifi connect {ctx.vars['wifi_2_4']} password hds11234**"
        )
        dev.sleep(15000)

    def set_b_wifi_2_4(self, ctx: EvalContext, dev: Device):
        dev.shell("svc wifi disable")
        dev.sleep(1000)
        dev.shell(
            f"svc wifi connect {ctx.vars['b_wifi_2_4']} password hds11234**"
        )
        dev.sleep(5000)
        self._log_current_wifi(ctx, dev)
        # unknown_ssid check
        if ctx.vars.get("get_now_wifi") == "<unknown_ssid>":
            dev.shell("svc wifi disable")
            dev.sleep(1000)
            dev.shell(
                f"svc wifi connect {ctx.vars['lab3_b_wifi_2_4']} password hds11234**"
            )
            dev.sleep(5000)

    def set_wifi_5(self, ctx: EvalContext, dev: Device):
        ctx.set_var("set_wifi_5", "[doshell cat /sdcard/wifi5.txt]", dev)
        dev.shell("svc wifi disable")
        dev.sleep(1000)
        dev.shell(
            f"svc wifi connect {ctx.vars['set_wifi_5']} password hds11234**"
        )
        dev.sleep(15000)

    def set_b_wifi_5(self, ctx: EvalContext, dev: Device):
        dev.shell("svc wifi disable")
        dev.sleep(1000)
        dev.shell(
            f"svc wifi connect {ctx.vars['b_wifi_5']} password hds11234**"
        )
        dev.sleep(5000)
        self._log_current_wifi(ctx, dev)
        if ctx.vars.get("get_now_wifi") == "<unknown_ssid>":
            dev.shell("svc wifi disable")
            dev.sleep(1000)
            dev.shell(
                f"svc wifi connect {ctx.vars['lab3_b_wifi_5']} password hds11234**"
            )
            dev.sleep(5000)

    # -------------------------------------------------
    # Current Wi-Fi information parsing (common method)
    # -------------------------------------------------
    def _log_current_wifi(self, ctx: EvalContext, dev: Device):
        raw = dev.shell("dumpsys wifi | grep mWifiInfo")
        # DSL can unfold the same logic as is.
        cleaned = raw.replace(" ", "_")
        parts = cleaned.split(",_")
        parts = [p.split(":_")[-1] for p in parts]
        ctx.vars["set_now_wifi"] = parts[1]  # SSID position example

    # -------------------------------------------------
    # Device model and screen rotation check (set_test_screen, set_rotation_screen_check_fold)
    # -------------------------------------------------
    def set_test_screen(self, ctx: EvalContext, dev: Device):
        ctx.set_var(
            "OPEN_OR_CLOSE", "[doshell cmd device_state state]", dev
        )
        ctx.set_var("model", "[doshell getprop ro.product.model]", dev)
        ctx.set_var("Q7M", '"SM-F968N"', dev)

        cond = (
            ctx.vars["model"] == ctx.vars["Q7M"]
            and "OPENED" in ctx.vars["OPEN_OR_CLOSE"]
        )
        if cond:
            dev.rotation("0")
            dev.rotation("on")
        else:
            dev.rotation("on")

    def set_rotation_screen_check_fold(self, ctx: EvalContext, dev: Device):
        # Same logic, but rotate to 1 in fold situation
        ctx.set_var("model", "[doshell getprop ro.product.model]", dev)
        ctx.set_var("Q7M", '"SM-F968N"', dev)
        cond = (
            ctx.vars["model"] == ctx.vars["Q7M"]
            and "OPENED" in ctx.vars["OPEN_OR_CLOSE"]
        )
        if cond:
            dev.rotation("0")
            dev.rotation("on")
        else:
            dev.rotation("1")
            dev.rotation("on")

    # -------------------------------------------------
    # TSP / ACL check (check_tsp_acl)
    # -------------------------------------------------
    def check_tsp_acl(self, ctx: EvalContext, dev: Device):
        ctx.set_var("tsp_on", "[{tsp_on_check}]", dev)
        ctx.set_var("tsp_off", "[{tsp_off_check}]", dev)
        ctx.set_var("acl", "[{acl_check}]", dev)
        ctx.set_var("gallery_acl", "[{gallery_acl_check}]", dev)

    # -------------------------------------------------
    # Recent notification and app cleanup (recent_noti_clear)
    # -------------------------------------------------
    def recent_noti_clear(self, ctx: EvalContext, dev: Device):
        dev.press("app_switch")
        dev.sleep(2000)
        dev.click({"textMatches": "(?i)Close All|(?i)Close All apps|(?i)Close all"})
        dev.sleep(1000)
        dev.press("statusbar")
        dev.sleep(1000)
        dev.click({"text": "Clear"})
        dev.sleep(1000)
        dev.press("home")

    # -------------------------------------------------
    # Other pointer, scroll, pattern, etc. (below are some examples)
    # -------------------------------------------------
    def home_point(self, ctx: EvalContext, dev: Device):
        dev.sleep(1000)
        ctx.set_var(
            "OPEN_OR_CLOSE", "[doshell cmd device_state state]", dev
        )
        dev.sleep(500)

        if "OPEN" in ctx.vars["OPEN_OR_CLOSE"]:
            # If Launcher exists, return UI coordinates, otherwise use screen_size_check
            if dev.click({"desc": "Home", "pkg": "com.sec.android.app.launcher"}):
                # Direct UI object coordinate retrieval (example)
                pass
            elif dev.click({"desc": "Home", "pkg": "com.android.systemui"}):
                pass
            else:
                self.screen_size_check(ctx, dev)
                ctx.vars["RESERVED_X"] = ctx.vars["center_x"]
                ctx.vars["RESERVED_Y"] = ctx.vars["screen_y"] - 70
        else:
            # CLOSE state also same logic
            ...

        ctx.vars["home_x"] = ctx.vars["RESERVED_X"]
        ctx.vars["home_y"] = ctx.vars["RESERVED_Y"]

    # (Other pointer, scroll, pattern functions implemented in the same way)
