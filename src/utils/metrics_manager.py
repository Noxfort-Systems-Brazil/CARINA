# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Defines the MetricsManager, a reusable component to manage the exposure
of metrics to Prometheus.
"""

import logging
import threading

from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server


class MetricsManager:
    """
    A toolbox to create, manage and expose Prometheus metrics
    for a specific process.
    """

    def __init__(self, process_name: str, port: int, locale_manager=None):
        """
        Initializes the metrics manager for a process.

        Args:
            process_name (str): The process name (e.g., 'AI_Process', 'SDS_Worker').
                                Will be used as a label in metrics.
            port (int): TCP port where the metrics server will listen.
            locale_manager: Optional instance of LocaleManagerBackend.
        """
        self.process_name = process_name
        self.port = port
        self.locale_manager = locale_manager
        self.metrics = {}

        # Start the HTTP server in a daemon thread so as not to block the process
        self.start_server()

    def _get_string(self, key: str, default: str = None, **kwargs) -> str:
        if self.locale_manager and hasattr(self.locale_manager, "get_string"):
            return self.locale_manager.get_string(key, default=default, **kwargs)
        return default.format(**kwargs) if default and kwargs else (default or key)

    def start_server(self):
        """Starts the Prometheus HTTP server in a separate thread with error handling."""

        def run_server():
            max_attempts = 5
            last_error = None
            for attempt in range(max_attempts):
                port_to_try = self.port if attempt == 0 else self.port + (attempt * 100)
                try:
                    if attempt > 0:
                        logging.info(
                            self._get_string(
                                "metrics_manager.trying_fallback",
                                default="[{process}-METRICS] Trying alternative port {port}...",
                                process=self.process_name,
                                port=port_to_try,
                            )
                        )
                    start_http_server(port_to_try)
                    if attempt == 0:
                        logging.info(
                            self._get_string(
                                "metrics_manager.server_started",
                                default="[{process}-METRICS] Prometheus server started on port {port}",
                                process=self.process_name,
                                port=port_to_try,
                            )
                        )
                    else:
                        logging.info(
                            self._get_string(
                                "metrics_manager.fallback_started",
                                default="[{process}-METRICS] Prometheus server started on port {port} (Fallback)",
                                process=self.process_name,
                                port=port_to_try,
                            )
                        )
                    self.port = port_to_try  # Updates to reflect reality
                    return
                except OSError as e:
                    last_error = e
                    if e.errno == 98:  # Address already in use
                        logging.warning(
                            self._get_string(
                                "metrics_manager.port_in_use",
                                default="[{process}-METRICS] Port {port} in use (zombie process?).",
                                process=self.process_name,
                                port=port_to_try,
                            )
                        )
                    else:
                        logging.error(
                            self._get_string(
                                "metrics_manager.port_error",
                                default="[{process}-METRICS] Error starting on port {port}: {error}",
                                process=self.process_name,
                                port=port_to_try,
                                error=e,
                            )
                        )
                except Exception as e:
                    last_error = e
                    logging.error(
                        self._get_string(
                            "metrics_manager.generic_error",
                            default="[{process}-METRICS] Generic error on port {port}: {error}",
                            process=self.process_name,
                            port=port_to_try,
                            error=e,
                        )
                    , exc_info=True)

            logging.error(
                self._get_string(
                    "metrics_manager.server_disabled",
                    default="[{process}-METRICS] Unable to start metrics server (Metrics disabled): {error}",
                    process=self.process_name,
                    error=last_error,
                )
            )

        try:
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
        except Exception as e:
            logging.error(
                self._get_string(
                    "metrics_manager.thread_critical_error",
                    default="[{process}-METRICS] Critical failure creating server thread: {error}",
                    process=self.process_name,
                    error=e,
                )
            , exc_info=True)

    def register_metric(self, name: str, description: str, metric_type: str = "gauge", buckets: list = None):
        """
        Creates and registers a new metric.

        Args:
            name (str): Metric name (e.g., 'queue_size').
            description (str): Description of what the metric represents.
            metric_type (str): Metric type ('gauge', 'counter', 'histogram', or 'summary').
            buckets (list): Optional list of bucket thresholds for Histogram.
        """
        if name in self.metrics:
            return

        label_names = ["process_name"]

        try:
            if metric_type == "gauge":
                metric = Gauge(name, description, labelnames=label_names)
            elif metric_type == "counter":
                metric = Counter(name, description, labelnames=label_names)
            elif metric_type == "histogram":
                kwargs = {"labelnames": label_names}
                if buckets:
                    kwargs["buckets"] = buckets
                metric = Histogram(name, description, **kwargs)
            elif metric_type == "summary":
                metric = Summary(name, description, labelnames=label_names)
            else:
                logging.warning(
                    self._get_string(
                        "metrics_manager.unknown_type",
                        default="[{process}-METRICS] Unknown metric type: {type}",
                        process=self.process_name,
                        type=metric_type,
                    )
                )
                return

            self.metrics[name] = metric
            logging.debug(
                self._get_string(
                    "metrics_manager.registered",
                    default="[{process}-METRICS] Metric '{name}' registered.",
                    process=self.process_name,
                    name=name,
                )
            )
        except Exception as e:
            # Common error if the metric already exists in the Prometheus Client global registry
            logging.warning(
                self._get_string(
                    "metrics_manager.already_registered",
                    default="[{process}-METRICS] Metric '{name}' already registered or error: {error}",
                    process=self.process_name,
                    name=name,
                    error=e,
                )
            , exc_info=True)

    def update_metric(self, name: str, value: float):
        """
        Updates the value of a registered metric.

        Args:
            name (str): Name of the metric to update.
            value (float): New value for the metric or observation.
        """
        if name not in self.metrics:
            return

        try:
            metric = self.metrics[name]

            # The update method depends on the metric type
            if isinstance(metric, Gauge):
                metric.labels(process_name=self.process_name).set(value)
            elif isinstance(metric, Counter):
                metric.labels(process_name=self.process_name).inc(value)
            elif isinstance(metric, (Histogram, Summary)):
                metric.labels(process_name=self.process_name).observe(value)
        except Exception:
            # Avoid crashing the main loop if there is an error in the metric
            pass
