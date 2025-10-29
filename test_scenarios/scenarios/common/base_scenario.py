"""
Base Scenario Class
Common functionality for all test scenarios
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
from enum import Enum


class TestStatus(Enum):
    """Test execution status"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TestStep:
    """Individual test step"""
    name: str
    duration: float  # seconds
    action: str
    parameters: Dict[str, Any] = None


@dataclass
class TestConfig:
    """Test configuration"""
    name: str
    description: str
    hvpm_voltage: float = 4.0
    stabilization_time: float = 20.0
    monitoring_interval: float = 1.0
    test_duration: float = 20.0
    steps: List[TestStep] = None


class BaseScenario(ABC):
    """Base class for all test scenarios"""
    
    def __init__(self, hvpm_service=None, daq_service=None, adb_service=None, log_callback: Callable = None):
        self.hvpm_service = hvpm_service
        self.daq_service = daq_service
        self.adb_service = adb_service
        self.log_callback = log_callback or self._default_log
        
        self.status = TestStatus.IDLE
        self.current_step = 0
        self.total_steps = 0
        
    def _default_log(self, message: str, level: str = "info"):
        """Default logging function"""
        print(f"[{level.upper()}] {message}")
    
    @abstractmethod
    def get_config(self) -> TestConfig:
        """Get test configuration"""
        pass
    
    @abstractmethod
    def execute_step(self, step: TestStep) -> bool:
        """Execute a single test step"""
        pass
    
    def run(self) -> bool:
        """Run the complete test scenario"""
        try:
            config = self.get_config()
            self.total_steps = len(config.steps) if config.steps else 0
            
            self.log_callback(f"Starting scenario: {config.name}", "info")
            self.log_callback(f"Description: {config.description}", "info")
            self.log_callback(f"Total steps: {self.total_steps}", "info")
            
            self.status = TestStatus.RUNNING
            
            for i, step in enumerate(config.steps):
                self.current_step = i + 1
                
                self.log_callback(f"Step {self.current_step}/{self.total_steps}: {step.name}", "info")
                
                success = self.execute_step(step)
                
                if not success:
                    self.log_callback(f"Step {self.current_step} failed: {step.name}", "error")
                    self.status = TestStatus.FAILED
                    return False
                
                self.log_callback(f"Step {self.current_step} completed: {step.name}", "info")
            
            self.status = TestStatus.COMPLETED
            self.log_callback(f"Scenario completed successfully: {config.name}", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"Scenario execution error: {e}", "error")
            self.status = TestStatus.FAILED
            return False
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information"""
        return {
            'status': self.status.value,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'progress_percent': int((self.current_step / self.total_steps) * 100) if self.total_steps > 0 else 0
        }