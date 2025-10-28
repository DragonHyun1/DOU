# lib/precond_library.py
from .device import Device
from .utils import EvalContext


class PrecondLibrary:
    """
    Convert flows defined in Precondition_Library.txt to functional form.
    Mostly write values to files so that subsequent scripts can reuse them.
    """

    def __init__(self):
        pass

    # -------------------------------------------------
    # Brightness preset - create indoor.txt according to model and OS.
    # -------------------------------------------------
    def brightness_preprocess(self, ctx: EvalContext, dev: Device):
        ctx.set_var(
            "model",
            "[doshell getprop ro.product.model | head -c 6]",
            dev,
        )
        ctx.set_var("check_26", '"SM-S94"', dev)
        ctx.set_var("check_25", '"SM-S93"', dev)
        ctx.set_var("OS_ver", "[doshell getprop ro.build.version.sem]", dev)

        # Generate indoor values by model
        if ctx.vars["check_26"] == ctx.vars["model"]:
            ctx.vars["indoor_txt"] = "105"
            dev.shell(f'echo {ctx.vars["indoor_txt"]} > /sdcard/indoor.txt')
            ctx.vars["indoor_500"] = ctx._func(
                "brightness_create", "500", "6"
            )
            dev.shell(f'echo {ctx.vars["indoor_500"]} > /sdcard/indoor_500.txt')
        elif ctx.vars["check_25"] == ctx.vars["model"] and ctx.vars[
            "OS_ver"
        ] == "3501":
            ctx.vars["indoor_txt"] = "105"
            dev.shell(f'echo {ctx.vars["indoor_txt"]} > /sdcard/indoor.txt')
            ctx.vars["indoor_500"] = ctx._func(
                "brightness_create", "500", "6"
            )
            dev.shell(f'echo {ctx.vars["indoor_500"]} > /sdcard/indoor_500.txt')
        else:
            ctx.vars["indoor_txt"] = ctx._func("brightness_create", "500", "6")
            dev.shell(f'echo {ctx.vars["indoor_txt"]} > /sdcard/indoor.txt')
            dev.shell(f'echo {ctx.vars["indoor_txt"]} > /sdcard/indoor_500.txt')

        # Create all outdoor / hbm values in advance
        ctx.vars["outdoor_txt"] = ctx._func("brightness_create", "2300", "5")
        dev.shell(f'echo {ctx.vars["outdoor_txt"]} > /sdcard/outdoor.txt')

        ctx.vars["hbm_mid_txt"] = ctx._func("brightness_create", "5000", "5")
        dev.shell(f'echo {ctx.vars["hbm_mid_txt"]} > /sdcard/hbm_mid.txt')

        ctx.vars["hbm_txt"] = ctx._func("brightness_create", "20000", "5")
        dev.shell(f'echo {ctx.vars["hbm_txt"]} > /sdcard/hbm.txt')

    # -------------------------------------------------
    # Current Wi-Fi SSID discovery (wifi_set)
    # -------------------------------------------------
    def wifi_set(self, ctx: EvalContext, dev: Device):
        ctx.set_var("blank", '" "', dev)

        # 2.4 GHz SSID 추출
        find_2_4 = dev.shell('dumpsys wifi | grep "^SSID:.*2.4.*"')
        split_2_4 = ctx.resolve(f"[split {find_2_4} {ctx.vars['blank']}]", dev)
        ctx.vars["wifi_2_4"] = ctx.resolve("[get {split_2_4} 1]", dev)
        dev.shell(f'echo {ctx.vars["wifi_2_4"]} > /sdcard/wifi2.txt')

        # 5 GHz SSID 추출
        find_5 = dev.shell('dumpsys wifi | grep "^SSID:.*5.*"')
        split_5 = ctx.resolve(f"[split {find_5} {ctx.vars['blank']}]", dev)
        ctx.vars["wifi_5"] = ctx.resolve("[get {split_5} 1]", dev)
        dev.shell(f'echo {ctx.vars["wifi_5"]} > /sdcard/wifi5.txt')

    # -------------------------------------------------
    # TSP / ACL branching (tsp_acl)
    # -------------------------------------------------
    def tsp_acl(self, ctx: EvalContext, dev: Device):
        # model_check 를 먼저 실행해서 ctx.vars["result"] 를 만든다
        from .act_library import ActLibrary

        act = ActLibrary()
        act.model_check(ctx, dev)          # <-- 이 함수는 아래에 구현합니다.

        # result 에 따라 파일에 명령어를 남긴다
        result = ctx.vars["result"]
        if result == "fold_sub":
            ctx.vars["tsp_on"] = 'doshell echo fix_active_mode,1 > sys/class/sec/tsp2/cmd'
            ctx.vars["tsp_off"] = 'doshell echo fix_active_mode,0 > sys/class/sec/tsp2/cmd'
            ctx.vars["acl"] = 'doshell echo 1 > /sys/class/lcd/panel1/adaptive_control'
            ctx.vars["gallery_acl"] = 'doshell echo 0 > /sys/class/lcd/panel1/adaptive_control'
        elif result == "fold_main":
            ctx.vars["tsp_on"] = 'doshell echo fix_active_mode,1 > sys/class/sec/tsp1/cmd'
            ctx.vars["tsp_off"] = 'doshell echo fix_active_mode,0 > sys/class/sec/tsp1/cmd'
            ctx.vars["acl"] = 'doshell echo 1 > /sys/class/lcd/panel/adaptive_control'
            ctx.vars["gallery_acl"] = 'doshell echo 0 > /sys/class/lcd/panel/adaptive_control'
        elif result == "flip_sub":
            ctx.vars["tsp_on"] = 'doshell echo fix_active_mode,1 > sys/class/sec/tsp2/cmd'
            ctx.vars["tsp_off"] = 'doshell echo fix_active_mode,0 > sys/class/sec/tsp2/cmd'
            ctx.vars["acl"] = 'doshell echo 1 > /sys/class/lcd/panel/adaptive_control'
            ctx.vars["gallery_acl"] = 'doshell echo 0 > /sys/class/lcd/panel/adaptive_control'
        elif result == "flip_main":
            ctx.vars["tsp_on"] = 'doshell echo fix_active_mode,1 > sys/class/sec/tsp1/cmd'
            ctx.vars["tsp_off"] = 'doshell echo fix_active_mode,0 > sys/class/sec/tsp1/cmd'
            ctx.vars["acl"] = 'doshell echo 1 > /sys/class/lcd/panel/adaptive_control'
            ctx.vars["gallery_acl"] = 'doshell echo 0 > /sys/class/lcd/panel/adaptive_control'
        elif result == "main":
            ctx.vars["tsp_on"] = 'doshell echo fix_active_mode,1 > sys/class/sec/tsp/cmd'
            ctx.vars["tsp_off"] = 'doshell echo fix_active_mode,0 > sys/class/sec/tsp/cmd'
            ctx.vars["acl"] = 'doshell echo 1 > /sys/class/lcd/panel/adaptive_control'
            ctx.vars["gallery_acl"] = 'doshell echo 0 > /sys/class/lcd/panel/adaptive_control'

        # 최종 파일에 기록 (스크립트가 뒤에서 읽는다)
        dev.shell(f'echo "{ctx.vars["tsp_on"]}" > /sdcard/tsp_on.txt')
        dev.shell(f'echo "{ctx.vars["tsp_off"]}" > /sdcard/tsp_off.txt')
        dev.shell(f'echo "{ctx.vars["acl"]}" > /sdcard/acl.txt')
        dev.shell(f'echo "{ctx.vars["gallery_acl"]}" > /sdcard/gallery_acl.txt')
