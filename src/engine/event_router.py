import time
import logging
from multiprocessing.connection import Connection
from typing import Any

from manager.agent_manager import AgentManager
from engine.step_processor import StepProcessor

class EventRouter:
    """
    Orquestra o laço infinito de eventos WebSocket / Pipe, consumindo dados até chegar
    uma mensagem válida e roteando para o passo interno de Simulação (StepProcessor)
    ou de Mapa (Trainer root).
    """
    def __init__(self, pipe_conn: Connection, trainer_instance: Any, agent_manager: AgentManager, step_processor: StepProcessor):
        self.pipe_conn = pipe_conn
        self.trainer = trainer_instance
        self.agent_manager = agent_manager
        self.step_processor = step_processor

    def start_continuous_service(self):
        """
        Main Event Loop: Hibernate -> Drain -> Decide.
        """
        logging.info("Trainer entering Active Standby mode (Event-Driven)...")
        last_warn_time = 0
        
        while self.trainer.is_running:
            try:
                # 1. HIBERNATE: Block until data arrives
                if self.pipe_conn.poll(timeout=None):
                    
                    # 2. DRAIN BUFFER (Conflation)
                    try:
                        latest_command = self.pipe_conn.recv()
                    except EOFError:
                        self.trainer.is_running = False
                        break

                    dropped_frames = 0
                    while self.pipe_conn.poll():
                        try:
                            latest_command = self.pipe_conn.recv()
                            dropped_frames += 1
                        except EOFError:
                            self.trainer.is_running = False
                            break
                    
                    if not self.trainer.is_running: break
                    if dropped_frames > 0:
                        logging.debug(f"[SYNC] Drained {dropped_frames} stale frames.")

                    # Unpack Command
                    if not isinstance(latest_command, (list, tuple)) or len(latest_command) < 3:
                        continue

                    try:
                        module, func, args = latest_command[0], latest_command[1], latest_command[2]
                    except IndexError:
                        continue
                    
                    # 3. ROUTE COMMANDS
                    if module == "custom" and func == "hft_step":
                        if not self.trainer.agents:
                            if time.time() - last_warn_time > 5:
                                logging.warning("[HFT] Data received but AGENTS not loaded.")
                                last_warn_time = time.time()
                        else:
                            if not getattr(self, '_ai_started_logged', False):
                                logging.info("--- AI Engine Started Operating (HFT Mode) ---")
                                print("[AI Process] --- AI Engine Started Operating (HFT Mode) ---")
                                self._ai_started_logged = True
                            self.step_processor.process_hft_step(args[0], self.trainer.agents)
                            
                    elif module == "custom" and func == "load_map":
                        self.trainer._load_map(args[0])
                    
                    elif module == "system" and func == "save_checkpoint":
                        # Delegate to AgentManager
                        self.agent_manager.save_system_state(
                            self.trainer.current_map_path, self.trainer.agents, self.trainer.strategist
                        )
                        
                    elif module == "system" and func == "shutdown":
                        self.trainer.is_running = False
                        
            except EOFError:
                self.trainer.is_running = False
            except Exception as e:
                logging.error(f"Event Loop Error: {e}", exc_info=True)
