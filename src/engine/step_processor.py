import time
import logging
from typing import Dict, Any, Optional
from collections import defaultdict

from core.enums import Maturity
from core.system_reporter import SystemReporter

class StepProcessor:
    """
    Responsável por gerenciar o ciclo de vida e estado interno de uma
    Simulação/Sessão (Passos). Aciona Extractors, Agentes, e Authorizers.
    """
    def __init__(self, settings, locale_manager, agent_manager, input_preprocessor, 
                 state_extractor, action_supervisor, action_authorizer, 
                 maturity_manager, reward_computer, cycle_manager, pipe_conn):
        self.settings = settings
        self.lm = locale_manager
        
        self.agent_manager = agent_manager
        self.input_preprocessor = input_preprocessor
        self.state_extractor = state_extractor
        self.action_supervisor = action_supervisor
        self.action_authorizer = action_authorizer
        self.maturity_manager = maturity_manager
        self.reward_computer = reward_computer
        self.cycle_manager = cycle_manager
        
        self.pipe_conn = pipe_conn
        
        # Session State Variables
        self.step_counter = 0
        self.start_time_offset: Optional[float] = None
        self.current_phases: Dict[str, Any] = {}
        self.accumulated_metrics = defaultdict(lambda: {'rewards': [], 'entropies': []})
        self.log_step_progress = True

    def reset_state(self):
        """Redefine os contadores para uma nova sessão (ou novo mapa)."""
        self.step_counter = 0
        self.start_time_offset = None
        self.current_phases.clear()
        self.accumulated_metrics.clear()
        self.action_supervisor.reset()
        self.input_preprocessor.reset()

    def set_current_phases(self, phases: dict):
        self.current_phases = phases

    def process_hft_step(self, traffic_data: dict, agents: dict):
        """
        Orchestrates a single simulation step based on Real-Time Traffic Data.
        """
        t_start = time.perf_counter()
        
        # Time Management
        raw_timestamp = traffic_data.get('timestamp', 0)
        if self.start_time_offset is None:
            self.start_time_offset = raw_timestamp
        sim_time = raw_timestamp - self.start_time_offset
        self.step_counter += 1
        
        if self.log_step_progress:
            # FORCE PRINT TO CONSOLE FOR DEBUGGING HFT
            print(f"--- PASSO DE SIMULAÇÃO {self.step_counter} (Tempo: {sim_time:.1f}s) ---")
            SystemReporter.report_step_start(self.lm, self.step_counter, sim_time, "AUTOMATIC")

        actions_to_apply = {}
        edges_data = traffic_data.get('edges', {})
        
        # Structures for UI Feedback
        tls_lanes_state = {}
        maturity_info = {}

        # --- Main Agent Loop ---
        for tl_id, agent in agents.items():
            current_phase_idx = self.current_phases.get(tl_id, 0)
            
            # --- FIX UI DATA ---
            tls_lanes_state[tl_id] = self.state_extractor.get_phase_lane_states(tl_id, current_phase_idx)
            
            # Population Maturity Info
            agent_maturity = self.maturity_manager.agent_maturity.get(tl_id, Maturity.CHILD)
            maturity_info[tl_id] = agent_maturity.name
            
            # 1. Extract State
            state_vector = self.state_extractor.extract_state(traffic_data, tl_id, current_phase_idx)
            if len(state_vector) == 0: continue

            # 2. Prepare Tensor (Delegated to InputPreprocessor)
            state_tensor, state_seq = self.input_preprocessor.prepare_tensor(tl_id, state_vector)
            
            # 3. Agent Inference
            action_idx, action_log_prob, state_val, dist_entropy = agent.choose_action(state_tensor)
            
            action_int = action_idx.item()
            entropy_val = dist_entropy.item() if hasattr(dist_entropy, 'item') else 0.0
            
            # 4. Compute Reward
            reward = self.reward_computer.calculate(tl_id, edges_data)
            
            # 5. Store Experience (Agent internal memory)
            agent.push_memory(state_seq, action_idx, action_log_prob, reward, False, state_val)

            # 6. Metrics & Authorization
            self.accumulated_metrics[tl_id]['rewards'].append(reward)
            self.accumulated_metrics[tl_id]['entropies'].append(entropy_val)
            
            is_auth, reason = self.action_authorizer.is_action_authorized(tl_id, agent_maturity, sim_time)
            
            # 7. Reporting
            action_str = "NEXT_PHASE" if action_int == 0 else "HOLD"
            SystemReporter.report_agent_decision(
                self.lm, tl_id, agent_maturity.name, action_str, is_auth, reason, "NORMAL"
            )

            # 8. Queue Action
            if is_auth:
                actions_to_apply[tl_id] = action_int
                if action_int == 0:
                    self._update_estimated_phase(tl_id, current_phase_idx)

        # --- Execute Actions ---
        if actions_to_apply:
            self.action_supervisor.apply_actions(actions_to_apply, sim_time, self.current_phases)
            
        # --- Lifecycle Check ---
        episode_steps = self.settings.getint('AI_TRAINING', 'episode_max_steps', fallback=100)
        if self.step_counter % episode_steps == 0:
            self.cycle_manager.evaluate_cycle(self.step_counter, agents, self.accumulated_metrics)

        # --- SEND HFT FEEDBACK TO UI ---
        rich_payload = {
            "edges": edges_data,
            "tls_phases": self.current_phases,
            "tls_lanes_state": tls_lanes_state,
            "maturity": maturity_info
        }
        
        # Sends to the WebSocket Server via Pipe
        if self.pipe_conn:
            try:
                self.pipe_conn.send(("hft_rich_update", rich_payload))
            except Exception as e:
                logging.error(f"[TRAINER] Failed to send UI update: {e}")

        t_end = time.perf_counter()
        if self.log_step_progress:
            logging.info(f"[STEP_TIMER] Total: {(t_end - t_start) * 1000:.2f}ms")

    def _update_estimated_phase(self, tl_id, current_phase_idx):
        """Updates internal phase tracking when a switch occurs."""
        green_phases = self.state_extractor.tl_green_phases.get(tl_id, [])
        if not green_phases: return
        
        if current_phase_idx in green_phases:
            try:
                curr = green_phases.index(current_phase_idx)
                nxt = (curr + 1) % len(green_phases)
                self.current_phases[tl_id] = green_phases[nxt]
            except Exception: 
                pass
        else:
            self.current_phases[tl_id] = green_phases[0]
