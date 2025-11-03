"""
DAQ Collection Thread
Dedicated thread for DAQ data collection during tests
"""

import time
import threading
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime


class DAQCollectionThread:
    """Dedicated thread for DAQ data collection"""
    
    def __init__(self, daq_service, log_callback: Callable = None):
        self.daq_service = daq_service
        self.log_callback = log_callback or self._default_log
        
        # Thread control
        self.collection_thread: Optional[threading.Thread] = None
        self.is_collecting = False
        self.should_stop = False
        
        # Data collection
        self.collected_data = []
        self.collection_start_time = None
        self.collection_end_time = None
        
        # Configuration
        self.collection_interval = 0.001  # 1ms (1000 samples per second)
        self.enabled_channels = []
        
    def _default_log(self, message: str, level: str = "info"):
        """Default logging function"""
        print(f"[DAQ-{level.upper()}] {message}")
    
    def configure(self, enabled_channels: List[str], interval: float = 0.001):
        """Configure DAQ collection parameters"""
        self.enabled_channels = enabled_channels
        self.collection_interval = interval
        self.log_callback(f"DAQ collection configured: {len(enabled_channels)} channels, {interval}s interval", "info")
    
    def start_collection(self) -> bool:
        """Start DAQ data collection in separate thread"""
        try:
            if self.is_collecting:
                self.log_callback("DAQ collection already running", "warn")
                return True
            
            if not self.daq_service:
                self.log_callback("DAQ service not available", "warn")
                return False
            
            if not self.enabled_channels:
                self.log_callback("No DAQ channels configured", "warn")
                return False
            
            # Reset state
            self.collected_data = []
            self.should_stop = False
            self.collection_start_time = time.time()
            
            # Start collection thread
            self.collection_thread = threading.Thread(
                target=self._collection_loop,
                name="DAQ-Collection-Thread",
                daemon=True
            )
            self.collection_thread.start()
            
            self.is_collecting = True
            self.log_callback(f"✅ DAQ collection started with {len(self.enabled_channels)} channels", "info")
            return True
            
        except Exception as e:
            self.log_callback(f"❌ Error starting DAQ collection: {e}", "error")
            return False
    
    def stop_collection(self) -> Dict[str, Any]:
        """Stop DAQ data collection and return results"""
        try:
            if not self.is_collecting:
                self.log_callback("DAQ collection not running", "warn")
                return {"success": False, "data": [], "message": "Not collecting"}
            
            # Signal thread to stop
            self.should_stop = True
            self.collection_end_time = time.time()
            
            # Wait for thread to finish (with timeout)
            if self.collection_thread and self.collection_thread.is_alive():
                self.collection_thread.join(timeout=5.0)
                
                if self.collection_thread.is_alive():
                    self.log_callback("⚠️ DAQ collection thread did not stop gracefully", "warn")
            
            self.is_collecting = False
            
            # Prepare results
            collection_duration = self.collection_end_time - self.collection_start_time if self.collection_start_time else 0
            data_count = len(self.collected_data)
            
            result = {
                "success": True,
                "data": self.collected_data.copy(),
                "data_count": data_count,
                "duration": collection_duration,
                "start_time": self.collection_start_time,
                "end_time": self.collection_end_time,
                "channels": self.enabled_channels.copy()
            }
            
            self.log_callback(f"✅ DAQ collection stopped: {data_count} data points in {collection_duration:.1f}s", "info")
            return result
            
        except Exception as e:
            self.log_callback(f"❌ Error stopping DAQ collection: {e}", "error")
            return {"success": False, "data": [], "message": str(e)}
    
    def _collection_loop(self):
        """Main DAQ data collection loop (runs in separate thread)"""
        try:
            self.log_callback("DAQ collection loop started", "info")
            loop_count = 0
            successful_reads = 0
            
            while not self.should_stop:
                loop_start = time.time()
                loop_count += 1
                
                try:
                    # Read DAQ data
                    if self.daq_service and hasattr(self.daq_service, 'read_single_shot'):
                        readings = self.daq_service.read_single_shot()
                        
                        if readings:
                            # Add timestamp to readings
                            data_point = {
                                'timestamp': time.time(),
                                'elapsed_time': time.time() - self.collection_start_time,
                                'readings': readings,
                                'loop_count': loop_count
                            }
                            
                            self.collected_data.append(data_point)
                            successful_reads += 1
                            
                            # Log progress every 10 readings
                            if loop_count % 10 == 0:
                                self.log_callback(f"DAQ collection: {len(self.collected_data)} points, {successful_reads}/{loop_count} success rate", "info")
                        else:
                            self.log_callback(f"DAQ read returned no data (attempt {loop_count})", "warn")
                    
                    else:
                        # Mock data for testing without real DAQ
                        data_point = {
                            'timestamp': time.time(),
                            'elapsed_time': time.time() - self.collection_start_time,
                            'readings': {f'ai{i}': {'voltage': 0.1 + i * 0.01, 'current': 0.001 + i * 0.0001} for i in range(len(self.enabled_channels))},
                            'loop_count': loop_count
                        }
                        self.collected_data.append(data_point)
                        successful_reads += 1
                
                except Exception as e:
                    self.log_callback(f"DAQ read error (loop {loop_count}): {e}", "error")
                
                # Sleep for remaining interval time
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.collection_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            self.log_callback(f"DAQ collection loop ended: {successful_reads}/{loop_count} successful reads", "info")
            
        except Exception as e:
            self.log_callback(f"Critical error in DAQ collection loop: {e}", "error")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current collection status"""
        return {
            'is_collecting': self.is_collecting,
            'data_count': len(self.collected_data),
            'enabled_channels': self.enabled_channels.copy(),
            'collection_interval': self.collection_interval,
            'thread_alive': self.collection_thread.is_alive() if self.collection_thread else False
        }
    
    def get_latest_data(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get latest N data points"""
        return self.collected_data[-count:] if self.collected_data else []