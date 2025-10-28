import subprocess


def list_devices():
    """
    Return list of connected ADB devices.
    Extract only properly connected devices.
    """
    try:
        result = subprocess.check_output(["adb", "devices"], text=True)
        lines = result.strip().splitlines()[1:]  # First line is 'List of devices attached'
        devices = [line.split()[0] for line in lines if "\tdevice" in line]
        return devices if devices else []
    except Exception as e:
        print("ADB Error in list_devices:", e)
        return []


def run_command(device: str, command: str) -> str:
    """
    Execute ADB command on specific device and return result string.
    """
    if not device or device == "-":
        return "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device] + command.split(),
            text=True
        )
        return result.strip()
    except subprocess.CalledProcessError as e:
        return f"ADB command failed: {e}"
    except Exception as e:
        return f"ADB error: {e}"


def install_apk(device: str, apk_path: str) -> str:
    """Install APK on specific device"""
    if not device or device == "-":
        return "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "install", "-r", apk_path],
            text=True
        )
        return result.strip()
    except Exception as e:
        return f"ADB install error: {e}"


def reboot_device(device: str, mode: str = None) -> str:
    """Reboot device (normal/bootloader/recovery)"""
    if not device or device == "-":
        return "No device selected"
    try:
        cmd = ["adb", "-s", device, "reboot"]
        if mode:
            cmd.append(mode)
        result = subprocess.check_output(cmd, text=True)
        return result.strip() if result else f"Rebooting {device}..."
    except Exception as e:
        return f"ADB reboot error: {e}"


def push_file(device: str, local_path: str, remote_path: str) -> str:
    """Transfer file from local to device"""
    if not device or device == "-":
        return "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "push", local_path, remote_path],
            text=True
        )
        return result.strip()
    except Exception as e:
        return f"ADB push error: {e}"


def pull_file(device: str, remote_path: str, local_path: str) -> str:
    """Pull file from device to local"""
    if not device or device == "-":
        return "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "pull", remote_path, local_path],
            text=True
        )
        return result.strip()
    except Exception as e:
        return f"ADB pull error: {e}"


def execute_command(device: str, command: str) -> bool:
    """
    Execute ADB shell command on specific device (return success/failure)
    Used in automated tests
    """
    if not device or device == "-":
        return False
    try:
        subprocess.check_output(
            ["adb", "-s", device, "shell", command],
            text=True,
            stderr=subprocess.STDOUT
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False


def execute_command_with_output(device: str, command: str) -> tuple[bool, str]:
    """
    Execute ADB shell command on specific device and return result and output
    """
    if not device or device == "-":
        return False, "No device selected"
    try:
        result = subprocess.check_output(
            ["adb", "-s", device, "shell", command],
            text=True,
            stderr=subprocess.STDOUT
        )
        return True, result.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Command failed: {e.output if e.output else str(e)}"
    except Exception as e:
        return False, f"ADB error: {e}"


def get_screen_state(device: str) -> tuple[bool, bool]:
    """
    Check screen state (success status, screen on status)
    """
    success, output = execute_command_with_output(device, "dumpsys power | grep 'Display Power'")
    if success:
        # Display Power: appears as state=ON or state=OFF format
        screen_on = "state=ON" in output
        return True, screen_on
    return False, False


def wake_device(device: str) -> bool:
    """Turn on device screen"""
    return execute_command(device, "input keyevent KEYCODE_WAKEUP")


def sleep_device(device: str) -> bool:
    """Turn off device screen"""
    return execute_command(device, "input keyevent KEYCODE_POWER")


def unlock_device(device: str) -> bool:
    """Unlock device (simple swipe up)"""
    return execute_command(device, "input swipe 500 1000 500 500")


def tap_screen(device: str, x: int, y: int) -> bool:
    """Touch specific position on screen"""
    return execute_command(device, f"input tap {x} {y}")


def swipe_screen(device: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
    """Swipe screen"""
    return execute_command(device, f"input swipe {x1} {y1} {x2} {y2} {duration}")


def start_activity(device: str, package: str, activity: str = None) -> bool:
    """Launch app"""
    if activity:
        cmd = f"am start -n {package}/{activity}"
    else:
        cmd = f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
    return execute_command(device, cmd)


def force_stop_app(device: str, package: str) -> bool:
    """Force stop app"""
    return execute_command(device, f"am force-stop {package}")


def get_battery_level(device: str) -> tuple[bool, int]:
    """Check battery level"""
    success, output = execute_command_with_output(device, "dumpsys battery | grep level")
    if success:
        try:
            # Appears as level: 85 format
            level = int(output.split(':')[1].strip())
            return True, level
        except (IndexError, ValueError):
            return False, 0
    return False, 0


def set_brightness(device: str, brightness: int) -> bool:
    """Set screen brightness (0-255)"""
    brightness = max(0, min(255, brightness))  # Range limitation
    return execute_command(device, f"settings put system screen_brightness {brightness}")


def get_cpu_usage(device: str) -> tuple[bool, float]:
    """Check CPU usage"""
    success, output = execute_command_with_output(device, "top -n 1 | head -3 | tail -1")
    if success:
        try:
            # Parse CPU usage (format may vary by device)
            parts = output.split()
            for part in parts:
                if '%' in part and 'cpu' in part.lower():
                    cpu_usage = float(part.replace('%', ''))
                    return True, cpu_usage
        except (IndexError, ValueError):
            pass
    return False, 0.0
