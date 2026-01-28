import time
import psutil
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime


class MetricsCollector:
    """
    A class for collecting system and application metrics.

    This class provides methods for collecting CPU usage, memory usage,
    disk usage, network I/O, and custom application-specific metrics.
    It supports exporting metrics to a JSON file.
    """

    def __init__(self, app_name: str = "default_app", log_dir: str = "logs") -> None:
        """
        Initializes the MetricsCollector with the application name and log directory.

        Args:
            app_name: The name of the application.
            log_dir: The directory to store log files.
        """
        self.app_name = app_name
        self.log_dir = log_dir
        self._ensure_log_directory_exists()

    def _ensure_log_directory_exists(self) -> None:
        """
        Ensures that the log directory exists. If it doesn't, it creates it.
        """
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except OSError as e:
                print(f"Error creating log directory: {e}")

    def collect_system_metrics(self) -> Dict[str, Any]:
        """
        Collects system-level metrics such as CPU usage, memory usage,
        disk usage, and network I/O.

        Returns:
            A dictionary containing the collected system metrics.
        """
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)  # Short interval for more accurate reading
            memory_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent
            net_io = psutil.net_io_counters()
            bytes_sent = net_io.bytes_sent
            bytes_recv = net_io.bytes_recv

            system_metrics = {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": disk_usage,
                "bytes_sent": bytes_sent,
                "bytes_recv": bytes_recv,
            }
            return system_metrics
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
            return {}

    def collect_custom_metrics(self, custom_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collects custom application-specific metrics.

        Args:
            custom_metrics: A dictionary containing the custom metrics to collect.

        Returns:
            A dictionary containing the collected custom metrics.
        """
        try:
            # Validate that custom_metrics is a dictionary
            if not isinstance(custom_metrics, dict):
                raise TypeError("custom_metrics must be a dictionary")

            return custom_metrics
        except TypeError as e:
            print(f"Error collecting custom metrics: {e}")
            return {}
        except Exception as e:
            print(f"Error collecting custom metrics: {e}")
            return {}

    def export_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Exports the collected metrics to a JSON file.

        Args:
            metrics: A dictionary containing the metrics to export.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file_path = os.path.join(self.log_dir, f"{self.app_name}_metrics_{timestamp}.json")

            # Add timestamp to metrics
            metrics["timestamp"] = timestamp

            with open(log_file_path, "w") as f:
                json.dump(metrics, f, indent=4)

            print(f"Metrics exported to {log_file_path}")

        except Exception as e:
            print(f"Error exporting metrics: {e}")

    def collect_and_export(self, custom_metrics: Optional[Dict[str, Any]] = None) -> None:
        """
        Collects both system and custom metrics (if provided) and exports them to a JSON file.

        Args:
            custom_metrics: An optional dictionary containing custom metrics.
        """
        try:
            system_metrics = self.collect_system_metrics()
            all_metrics: Dict[str, Any] = system_metrics

            if custom_metrics:
                custom_metrics_data = self.collect_custom_metrics(custom_metrics)
                all_metrics.update(custom_metrics_data)  # Merge dictionaries

            self.export_metrics(all_metrics)
        except Exception as e:
            print(f"Error collecting and exporting metrics: {e}")


if __name__ == '__main__':
    # Example usage:
    collector = MetricsCollector(app_name="my_app", log_dir="app_logs")

    # Simulate some custom metrics
    my_custom_metrics = {
        "requests_processed": 100,
        "errors_encountered": 5,
        "average_response_time": 0.25
    }

    collector.collect_and_export(my_custom_metrics)

    time.sleep(2) # Allow time for metrics to change

    collector.collect_and_export() # Collect and export system metrics only