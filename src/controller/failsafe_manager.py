import logging
from multiprocessing.connection import Connection
from typing import Optional, Any

class FailsafeManager:
    """
    Responsável por gerenciar o estado global de operação da CARINA (AUTOMATIC, WATCHDOG, MANUAL).
    Acompanha o Watchdog e aciona o modo de segurança ('Failsafe') caso a IA seja desligada ou sofra timeout.
    """
    def __init__(self, ai_pipe_conn: Connection, monitor_client: Optional[Any] = None):
        self.current_operation_mode = "AUTOMATIC"
        self.failsafe_active = False
        
        self.ai_pipe_conn = ai_pipe_conn
        self.monitor_client = monitor_client

    def trigger_failsafe(self):
        """
        Forces the system into Fail-Safe (Watchdog) mode.
        Should be called when external Watchdog process detects silence.
        """
        if not self.failsafe_active:
            logging.critical("[CentralController] 🚨 ENTERING WATCHDOG MODE (Fixed-Time Fallback). AI Paused.")
            self.failsafe_active = True
            self.current_operation_mode = "WATCHDOG"
            
            # Report Critical Incident to External Monitor
            if self.monitor_client:
                try:
                    self.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="CRITICAL",
                        message="Watchdog timeout triggered. Synapse silence detected. Switching to Fixed-Time fallback."
                    )
                except Exception as e:
                    logging.error(f"Error reporting failsafe incident: {e}")

    def attempt_recovery(self) -> bool:
        """
        Tenta recuperar o sistema do modo Watchdog.
        Retorna `True` se a recuperação ocorreu nesta chamada.
        """
        if self.failsafe_active:
            logging.info("[CentralController] ✅ SYNAPSE SIGNAL RESTORED. Resuming AI Neural Network.")
            self.failsafe_active = False
            self.current_operation_mode = "AUTOMATIC"
            
            if self.monitor_client:
                try:
                    self.monitor_client.report_incident(
                        category="SOFTWARE",
                        level="INFO",
                        message="Synapse signal restored. Watchdog mode disabled, resuming AI Neural Network."
                    )
                except Exception as e:
                    logging.error(f"Error reporting recovery incident: {e}")
                
            try:
                self.ai_pipe_conn.send(('system', 'wakeup', (), {}))
            except Exception as e:
                logging.error(f"Error sending wakeup signal: {e}")
            
            return True
        return False
