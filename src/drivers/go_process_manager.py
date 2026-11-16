# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Manages the lifecycle, subprocess execution, and standard error streams of the carina-go binary.
Isolated responsibility according to the Single Responsibility Principle (SRP).
"""

import atexit
import logging
import os
import subprocess
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

GATEWAY_SECURITY_ENV_MAP: Dict[str, str] = {
    "evp_auth_token": "CARINA_EVP_AUTH_TOKEN",
    "cco_auth_token": "CARINA_CCO_AUTH_TOKEN",
    "cco_allowed_origin": "CARINA_CCO_ALLOWED_ORIGIN",
    "gateway_tls_cert": "CARINA_GATEWAY_TLS_CERT",
    "gateway_tls_key": "CARINA_GATEWAY_TLS_KEY",
    "gateway_tls_ca": "CARINA_GATEWAY_TLS_CA",
    "gateway_tls_server_name": "CARINA_GATEWAY_TLS_SERVER_NAME",
    "gateway_web_port": "CARINA_GATEWAY_PORT",
    "gateway_trap_port": "CARINA_TRAP_PORT",
}


def resolve_gateway_security_settings() -> Dict[str, str]:
    """Resolves gateway security settings prioritizing environment variables over SettingsManager."""
    resolved: Dict[str, str] = {}
    cfg: Dict[str, Any] = {}
    try:
        from src.utils.settings_manager import SettingsManager

        loaded = SettingsManager().load_settings()
        if isinstance(loaded, dict):
            cfg = loaded
    except Exception as exc:
        logger.debug("[GoProcessManager] Settings lookup skipped for Go security config: %s", exc)

    for setting_key, env_key in GATEWAY_SECURITY_ENV_MAP.items():
        env_val = os.getenv(env_key, "").strip()
        resolved[setting_key] = env_val or str(cfg.get(setting_key, "") or "").strip()
    return resolved


def sync_gateway_security_tokens(client: Any) -> None:
    """Pushes resolved EVP/CCO auth tokens and CORS origin to a running GoGatewayClient."""
    sec = resolve_gateway_security_settings()
    client.send_command(
        "gateway_set_auth_tokens",
        timeout=5.0,
        evp_auth_token=sec["evp_auth_token"],
        cco_auth_token=sec["cco_auth_token"],
        allowed_origin=sec["cco_allowed_origin"],
    )


def _build_gateway_child_env() -> Dict[str, str]:
    """Builds subprocess environment forwarding configured security tokens/TLS paths."""
    env = dict(os.environ)
    resolved = resolve_gateway_security_settings()
    for setting_key, env_key in GATEWAY_SECURITY_ENV_MAP.items():
        if not env.get(env_key) and resolved.get(setting_key):
            env[env_key] = resolved[setting_key]
    return env


class GoProcessManager:
    """
    Supervises the Go hardware gateway subprocess execution, shutdown and logging.
    """

    def __init__(self, binary_path: str) -> None:
        self.binary_path = binary_path
        self.process: Optional[subprocess.Popen] = None
        self._running = False
        self._lock = threading.Lock()
        self._stderr_thread: Optional[threading.Thread] = None
        atexit.register(self.stop)

    def is_running(self) -> bool:
        """Checks if subprocess is alive."""
        return self._running and self.process is not None and self.process.poll() is None

    def start(self) -> bool:
        """Spawns the Go binary and starts the stderr logger thread."""
        with self._lock:
            if self.is_running():
                return True

        if not os.path.exists(self.binary_path):
            logger.error(f"[GoProcessManager] Gateway binary not found at: {self.binary_path}")
            return False

        try:
            logger.info(f"[GoProcessManager] Spawning Go Hardware Gateway: {self.binary_path}")
            child_env = _build_gateway_child_env()
            self.process = subprocess.Popen(
                [self.binary_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line-buffered
                close_fds=True,
                env=child_env,
            )
            self._running = True

            self._stderr_thread = threading.Thread(
                target=self._read_stderr_loop,
                daemon=True,
                name="GoGatewayStderrReader",
            )
            self._stderr_thread.start()
            return True

        except Exception as e:
            logger.error(f"[GoProcessManager] Failed to start Go binary: {e}", exc_info=True)
            self.stop()
            return False

    def stop(self, pre_stop_hook: Optional[Callable[[], None]] = None) -> None:
        """Performs graceful shutdown of the Go gateway process and cleans up resources."""
        if not self._running:
            return

        self._running = False
        logger.info("[GoProcessManager] Stopping Go Hardware Gateway process...")

        try:
            if pre_stop_hook:
                try:
                    pre_stop_hook()
                except Exception as hook_err:
                    logger.debug(f"[GoProcessManager] Error running pre-stop hook: {hook_err}")

            if self.process and self.process.poll() is None:
                if self.process.stdin:
                    try:
                        self.process.stdin.close()
                    except Exception as _exc:
                        logger.debug("[drivers] Ignored recoverable error: %s", _exc)

                self.process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            logger.warning("[GoProcessManager] Process did not terminate within timeout; killing...")
            if self.process:
                self.process.kill()
        except Exception as e:
            logger.error(f"[GoProcessManager] Error during gateway termination: {e}", exc_info=True)
        finally:
            self.process = None

    def _read_stderr_loop(self) -> None:
        """Reads log lines from the Go gateway's stderr and routes them to Python logger."""
        while self._running and self.process and self.process.stderr:
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                line_str = line.strip()
                if line_str:
                    logger.info(f"[GoGateway] {line_str}")
            except Exception:
                break

        # Subprocess closed stderr; reap process to prevent zombie (<defunct>) processes
        if self.process:
            try:
                self.process.poll()
                self.process.wait(timeout=1.0)
            except Exception as _exc:
                logger.debug("[drivers] Ignored recoverable error: %s", _exc)
