"""
Test Configuration Settings
Global configuration for all test scenarios
"""

from typing import Dict, Any
import os
from datetime import datetime


class TestConfig:
    """Global test configuration"""
    
    # Test environment settings
    ENVIRONMENT = {
        'hvpm_voltage': 4.0,
        'daq_timeout': 25.0,  # seconds (reduced from 40s to 25s)
        'stabilization_time': 10.0,  # seconds
        'monitoring_interval': 1.0,  # seconds
        'max_test_duration': 300.0,  # 5 minutes max
    }
    
    # File paths
    PATHS = {
        'results_dir': os.path.join(os.getcwd(), 'test_results'),
        'logs_dir': os.path.join(os.getcwd(), 'test_logs'),
        'temp_dir': os.path.join(os.getcwd(), 'temp'),
        'brightness_files': {
            'indoor_500': '/sdcard/indoor_500.txt',
            'indoor': '/sdcard/indoor.txt',
            'outdoor': '/sdcard/outdoor.txt',
            'hbm_mid': '/sdcard/hbm_mid.txt',
            'hbm': '/sdcard/hbm.txt'
        }
    }
    
    # Logging configuration
    LOGGING = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_prefix': 'test_scenario',
        'max_log_files': 10
    }
    
    # Excel export settings
    EXCEL = {
        'filename_format': 'test_results_{scenario}_{timestamp}.xlsx',
        'timestamp_format': '%Y%m%d_%H%M%S',
        'sheets': {
            'summary': 'Test Summary',
            'daq_data': 'DAQ Data',
            'device_status': 'Device Status',
            'logs': 'Test Logs'
        }
    }
    
    @classmethod
    def get_environment(cls) -> Dict[str, Any]:
        """Get environment settings"""
        return cls.ENVIRONMENT.copy()
    
    @classmethod
    def get_paths(cls) -> Dict[str, Any]:
        """Get file paths"""
        return cls.PATHS.copy()
    
    @classmethod
    def get_logging_config(cls) -> Dict[str, Any]:
        """Get logging configuration"""
        return cls.LOGGING.copy()
    
    @classmethod
    def get_excel_config(cls) -> Dict[str, Any]:
        """Get Excel export configuration"""
        return cls.EXCEL.copy()
    
    @classmethod
    def get_result_filename(cls, scenario_name: str) -> str:
        """Generate result filename for scenario"""
        timestamp = datetime.now().strftime(cls.EXCEL['timestamp_format'])
        return cls.EXCEL['filename_format'].format(
            scenario=scenario_name.lower().replace(' ', '_'),
            timestamp=timestamp
        )
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        paths = cls.get_paths()
        for dir_path in [paths['results_dir'], paths['logs_dir'], paths['temp_dir']]:
            os.makedirs(dir_path, exist_ok=True)