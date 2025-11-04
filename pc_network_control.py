"""
PC Network Control Module
PC의 Wi-Fi 네트워크를 자동으로 제어
"""

import subprocess
import platform
import time
from typing import Optional, Tuple


class PCNetworkController:
    """PC Wi-Fi 네트워크 자동 제어"""
    
    def __init__(self):
        self.os_type = platform.system()
        self.original_network = None
        
    def get_current_network(self) -> Optional[str]:
        """현재 연결된 Wi-Fi 네트워크 이름 반환"""
        try:
            if self.os_type == "Windows":
                result = subprocess.run(
                    ['netsh', 'wlan', 'show', 'interfaces'],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if 'SSID' in line and 'BSSID' not in line:
                        return line.split(':')[1].strip()
                        
            elif self.os_type == "Linux":
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if line.startswith('yes:'):
                        return line.split(':')[1]
                        
            return None
            
        except Exception as e:
            print(f"❌ Error getting current network: {e}")
            return None
    
    def connect_wifi(self, ssid: str, password: Optional[str] = None) -> bool:
        """지정된 Wi-Fi 네트워크에 연결
        
        Args:
            ssid: Wi-Fi SSID
            password: Wi-Fi 비밀번호 (저장된 네트워크면 None 가능)
            
        Returns:
            bool: 성공 여부
        """
        try:
            print(f"🔄 Connecting to Wi-Fi: {ssid}")
            
            # 원래 네트워크 저장 (처음 한 번만)
            if self.original_network is None:
                self.original_network = self.get_current_network()
                print(f"📝 Original network saved: {self.original_network}")
            
            if self.os_type == "Windows":
                # Windows: netsh 사용
                cmd = ['netsh', 'wlan', 'connect', f'name={ssid}']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"⚠️ Connection may have failed: {result.stderr}")
                    return False
                    
            elif self.os_type == "Linux":
                # Linux: nmcli 사용
                if password:
                    cmd = ['nmcli', 'device', 'wifi', 'connect', ssid, 
                           'password', password]
                else:
                    cmd = ['nmcli', 'connection', 'up', ssid]
                    
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"⚠️ Connection failed: {result.stderr}")
                    return False
            else:
                print(f"❌ Unsupported OS: {self.os_type}")
                return False
            
            # 연결 확인 (최대 10초 대기)
            print("⏳ Waiting for connection...")
            for i in range(10):
                time.sleep(1)
                current = self.get_current_network()
                if current == ssid:
                    print(f"✅ Connected to {ssid}")
                    return True
                    
            print(f"⚠️ Connection timeout")
            return False
            
        except Exception as e:
            print(f"❌ Error connecting to Wi-Fi: {e}")
            return False
    
    def restore_original_network(self) -> bool:
        """원래 네트워크로 복구"""
        if self.original_network is None:
            print("ℹ️ No original network to restore")
            return True
            
        print(f"🔄 Restoring original network: {self.original_network}")
        return self.connect_wifi(self.original_network)
    
    def check_admin_privileges(self) -> bool:
        """관리자 권한 확인"""
        try:
            if self.os_type == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            elif self.os_type == "Linux":
                return subprocess.run(['id', '-u'], 
                                     capture_output=True, 
                                     text=True).stdout.strip() == '0'
            return False
        except:
            return False


# 사용 예시
if __name__ == "__main__":
    controller = PCNetworkController()
    
    # 관리자 권한 확인
    if not controller.check_admin_privileges():
        print("⚠️ WARNING: This script may require administrator privileges!")
        print("   Windows: Run as Administrator")
        print("   Linux: Run with sudo")
        print()
    
    # 현재 네트워크 확인
    current = controller.get_current_network()
    print(f"📡 Current network: {current}")
    print()
    
    # 테스트 시나리오
    test_ssid = "0_WIFIFW_RAX40_2nd_2G"
    test_password = "cppower12"
    
    # 확인 메시지
    print("=" * 60)
    print("⚠️  WARNING: This will change your PC's Wi-Fi connection!")
    print("=" * 60)
    print(f"Current network: {current}")
    print(f"Target network:  {test_ssid}")
    print()
    print("This will:")
    print("  1. Disconnect from current network")
    print("  2. Connect to target network")
    print("  3. Your internet/network access will change")
    print()
    
    response = input("Continue? (yes/no): ")
    
    if response.lower() == 'yes':
        # 네트워크 변경
        if controller.connect_wifi(test_ssid, test_password):
            print()
            print("✅ Network changed successfully!")
            print()
            
            # 10초 대기
            print("⏳ Testing for 10 seconds...")
            time.sleep(10)
            
            # 원래 네트워크로 복구
            print()
            print("🔄 Restoring original network...")
            if controller.restore_original_network():
                print("✅ Network restored!")
            else:
                print("⚠️ Failed to restore network")
                print(f"   Please manually reconnect to: {controller.original_network}")
        else:
            print("❌ Failed to change network")
    else:
        print("❌ Operation cancelled")
