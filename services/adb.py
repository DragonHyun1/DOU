import subprocess


def list_devices():
    """
    연결된 ADB 디바이스 리스트 반환.
    정상적으로 연결된 디바이스만 추출.
    """
    try:
        result = subprocess.check_output(["adb", "devices"], text=True)
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
            text=True
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
            text=True
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
        result = subprocess.check_output(cmd, text=True)
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
            text=True
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
            text=True
        )
        return result.strip()
    except Exception as e:
        return f"ADB pull error: {e}"
