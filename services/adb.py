import subprocess
import sys

# Windows에서 cmd 창 안 뜨게 하는 설정
if sys.platform == 'win32':
    SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    SUBPROCESS_FLAGS = 0


def list_devices():
    """
    연결된 ADB 디바이스 리스트 반환.
    정상적으로 연결된 디바이스만 추출.
    """
    try:
        result = subprocess.check_output(["adb", "devices"], text=True, creationflags=SUBPROCESS_FLAGS)
        lines = result.strip().splitlines()[1:]  # 첫 줄은 'List of devices attached'
        devices = [line.split()[0] for line in lines if "\tdevice" in line]
        return devices if devices else []
    except Exception as e:
        print("ADB Error in list_devices:", e)
        return []


def run_command(device: str, command: str) -> str:
    """
    특정 디바이스에서 ADB 명령 실행 후 결과 문자열 반환.
    """
    if not device or device == "-":
        return "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device] + command.split(),
            text=True,
            creationflags=SUBPROCESS_FLAGS
        )
        return result.strip()
    except subprocess.CalledProcessError as e:
        return f"ADB command failed: {e}"
    except Exception as e:
        return f"ADB error: {e}"


def install_apk(device: str, apk_path: str) -> str:
    """특정 디바이스에 APK 설치"""
    if not device or device == "-":
        return "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "install", "-r", apk_path],
            text=True,
            creationflags=SUBPROCESS_FLAGS
        )
        return result.strip()
    except Exception as e:
        return f"ADB install error: {e}"


def reboot_device(device: str, mode: str = None) -> str:
    """디바이스 재부팅 (일반/bootloader/recovery)"""
    if not device or device == "-":
        return "No device selected"
    try:
        cmd = ["adb", "-s", device, "reboot"]
        if mode:
            cmd.append(mode)
        result = subprocess.check_output(cmd, text=True, creationflags=SUBPROCESS_FLAGS)
        return result.strip() if result else f"Rebooting {device}..."
    except Exception as e:
        return f"ADB reboot error: {e}"


def push_file(device: str, local_path: str, remote_path: str) -> str:
    """로컬 → 디바이스 파일 전송"""
    if not device or device == "-":
        return "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "push", local_path, remote_path],
            text=True,
            creationflags=SUBPROCESS_FLAGS
        )
        return result.strip()
    except Exception as e:
        return f"ADB push error: {e}"


def pull_file(device: str, remote_path: str, local_path: str) -> str:
    """디바이스 → 로컬 파일 가져오기"""
    if not device or device == "-":
        return "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "pull", remote_path, local_path],
            text=True,
            creationflags=SUBPROCESS_FLAGS
        )
        return result.strip()
    except Exception as e:
        return f"ADB pull error: {e}"


def execute_command(device: str, command: str) -> bool:
    """
    특정 디바이스에서 ADB shell 명령 실행 (성공/실패 반환)
    자동 테스트에서 사용
    """
    if not device or device == "-":
        return False
    try:
        subprocess.check_output(
            ["adb", "-s", device, "shell", command],
            text=True,
            stderr=subprocess.STDOUT,
            creationflags=SUBPROCESS_FLAGS
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False


def execute_command_with_output(device: str, command: str) -> tuple[bool, str]:
    """
    특정 디바이스에서 ADB shell 명령 실행 후 결과와 출력 반환
    """
    if not device or device == "-":
        return False, "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "shell", command],
            text=True,
            stderr=subprocess.STDOUT,
            creationflags=SUBPROCESS_FLAGS
        )
        return True, result.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Command failed: {e.output if e.output else str(e)}"
    except Exception as e:
        return False, f"ADB error: {e}"


def get_screen_state(device: str) -> tuple[bool, bool]:
    """
    화면 상태 확인 (성공여부, 화면켜짐여부)
    """
    success, output = execute_command_with_output(device, "dumpsys power | grep 'Display Power'")
    if success:
        # Display Power: state=ON 또는 state=OFF 형태로 나옴
        screen_on = "state=ON" in output
        return True, screen_on
    return False, False


def wake_device(device: str) -> bool:
    """디바이스 화면 켜기"""
    return execute_command(device, "input keyevent KEYCODE_WAKEUP")


def sleep_device(device: str) -> bool:
    """디바이스 화면 끄기"""
    return execute_command(device, "input keyevent KEYCODE_POWER")


def unlock_device(device: str) -> bool:
    """디바이스 잠금해제 (간단한 swipe up)"""
    return execute_command(device, "input swipe 500 1000 500 500")


def tap_screen(device: str, x: int, y: int) -> bool:
    """화면 특정 위치 터치"""
    return execute_command(device, f"input tap {x} {y}")


def swipe_screen(device: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
    """화면 스와이프"""
    return execute_command(device, f"input swipe {x1} {y1} {x2} {y2} {duration}")


def start_activity(device: str, package: str, activity: str = None) -> bool:
    """앱 실행"""
    if activity:
        cmd = f"am start -n {package}/{activity}"
    else:
        cmd = f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
    return execute_command(device, cmd)


def force_stop_app(device: str, package: str) -> bool:
    """앱 강제 종료"""
    return execute_command(device, f"am force-stop {package}")


def get_battery_level(device: str) -> tuple[bool, int]:
    """배터리 레벨 확인"""
    success, output = execute_command_with_output(device, "dumpsys battery | grep level")
    if success:
        try:
            # level: 85 형태로 나옴
            level = int(output.split(':')[1].strip())
            return True, level
        except (IndexError, ValueError):
            return False, 0
    return False, 0


def set_brightness(device: str, brightness: int) -> bool:
    """화면 밝기 설정 (0-255)"""
    brightness = max(0, min(255, brightness))  # 범위 제한
    return execute_command(device, f"settings put system screen_brightness {brightness}")


def get_cpu_usage(device: str) -> tuple[bool, float]:
    """CPU 사용률 확인"""
    success, output = execute_command_with_output(device, "top -n 1 | head -3 | tail -1")
    if success:
        try:
            # CPU 사용률 파싱 (기기마다 형태가 다를 수 있음)
            parts = output.split()
            for part in parts:
                if '%' in part and 'cpu' in part.lower():
                    cpu_usage = float(part.replace('%', ''))
                    return True, cpu_usage
        except (IndexError, ValueError):
            pass
    return False, 0.0
