# File: src/database/worker_monitor.py
# Author: Gabriel Moraes
# Date: October 5, 2025

import time
import psutil
from multiprocessing import Queue
from utils.metrics_manager import MetricsManager

class WorkerMonitor:
    """
    Responsibility: Monitor process-level hardware metrics (CPU, RAM, Queues)
    for background workers and expose them via prometheus/metrics endpoints.
    """
    def __init__(self, process_name: str, port: int, monitered_queues: dict):
        self.metrics_manager = MetricsManager(process_name=process_name, port=port)
        self.metrics_manager.register_metric('process_cpu_usage_percent', 'Uso de CPU do processo (%)')
        self.metrics_manager.register_metric('process_memory_usage_percent', 'Uso de Memória do processo (%)')
        self.metrics_manager.register_metric('db_data_queue_size', 'Tamanho da fila de dados para o DB Worker')
        
        self.current_process = psutil.Process()
        self.monitored_queues = monitered_queues
        self._running = False

    def start_loop(self, interval: int = 5):
        """Blocking loop to record values periodically."""
        self._running = True
        while self._running:
            try:
                self.metrics_manager.update_metric('process_cpu_usage_percent', self.current_process.cpu_percent())
                self.metrics_manager.update_metric('process_memory_usage_percent', self.current_process.memory_percent())
                
                # Dynamic queue tracking
                if 'db_data' in self.monitored_queues:
                    self.metrics_manager.update_metric('db_data_queue_size', self.monitored_queues['db_data'].qsize())
                    
                time.sleep(interval)
            except Exception:
                pass 
                
    def stop(self):
        self._running = False
