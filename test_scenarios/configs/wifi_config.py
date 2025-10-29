"""
WiFi Configuration for Test Scenarios
Centralized WiFi network settings
"""

from typing import Dict, Any


class WiFiConfig:
    """WiFi network configuration"""
    
    # WiFi network configurations
    NETWORKS = {
        '2g_primary': {
            'ssid': '0_WIFIFW_RAX40_2nd_2G',
            'password': 'cppower12',
            'frequency': '2.4GHz',
            'description': 'Primary 2.4GHz network for testing'
        },
        '5g_primary': {
            'ssid': '0_WIFIFW_RAX40_2nd_5G',
            'password': 'cppower12',
            'frequency': '5GHz',
            'description': 'Primary 5GHz network for testing'
        },
        '2g_backup': {
            'ssid': 'lab3_b_wifi_2_4',
            'password': 'hds11234**',
            'frequency': '2.4GHz',
            'description': 'Backup 2.4GHz network'
        },
        '5g_backup': {
            'ssid': 'lab3_b_wifi_5',
            'password': 'hds11234**',
            'frequency': '5GHz',
            'description': 'Backup 5GHz network'
        }
    }
    
    @classmethod
    def get_network(cls, network_key: str) -> Dict[str, Any]:
        """Get network configuration by key"""
        return cls.NETWORKS.get(network_key, {})
    
    @classmethod
    def get_2g_primary(cls) -> Dict[str, Any]:
        """Get primary 2.4GHz network configuration"""
        return cls.get_network('2g_primary')
    
    @classmethod
    def get_5g_primary(cls) -> Dict[str, Any]:
        """Get primary 5GHz network configuration"""
        return cls.get_network('5g_primary')
    
    @classmethod
    def get_all_networks(cls) -> Dict[str, Dict[str, Any]]:
        """Get all network configurations"""
        return cls.NETWORKS.copy()