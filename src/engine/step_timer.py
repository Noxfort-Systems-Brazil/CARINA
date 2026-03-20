import time
import logging

class StepTimer:
    """
    Responsável por catalogar a duração precisa de cada microlaço (nanosegundos)
    e publicar o log formatado para análise de performance do Episódio (PPO, Guardian, Net).
    """

    def __init__(self, log_step_progress: bool, freq: int):
        self.log_step_progress = log_step_progress
        self.freq = freq
        
        self.t_total_start = 0.0
        self.t_decision_start = 0.0
        self.t_decision_end = 0.0
        self.t_auth_start = 0.0
        self.t_auth_end = 0.0
        self.t_analysis_pre_start = 0.0
        self.t_analysis_pre_end = 0.0
        self.t_guardian_send_start = 0.0
        self.t_guardian_send_end = 0.0
        self.t_guardian_recv_start = 0.0
        self.t_guardian_recv_end = 0.0
        self.t_env_step_start = 0.0
        self.t_env_step_end = 0.0
        self.t_analysis_post_start = 0.0
        self.t_analysis_post_end = 0.0
        self.t_learning_start = 0.0
        self.t_learning_end = 0.0

    def mark_total_start(self): self.t_total_start = time.perf_counter()
    def mark_analysis_pre_start(self): self.t_analysis_pre_start = time.perf_counter()
    def mark_analysis_pre_end(self): self.t_analysis_pre_end = time.perf_counter()
    def mark_decision_start(self): self.t_decision_start = time.perf_counter()
    def mark_decision_end(self): self.t_decision_end = time.perf_counter()
    def mark_auth_start(self): self.t_auth_start = time.perf_counter()
    def mark_auth_end(self): self.t_auth_end = time.perf_counter()
    def mark_guardian_send_start(self): self.t_guardian_send_start = time.perf_counter()
    def mark_guardian_send_end(self): self.t_guardian_send_end = time.perf_counter()
    def mark_guardian_recv_start(self): self.t_guardian_recv_start = time.perf_counter()
    def mark_guardian_recv_end(self): self.t_guardian_recv_end = time.perf_counter()
    def mark_env_step_start(self): self.t_env_step_start = time.perf_counter()
    def mark_env_step_end(self): self.t_env_step_end = time.perf_counter()
    def mark_analysis_post_start(self): self.t_analysis_post_start = time.perf_counter()
    def mark_analysis_post_end(self): self.t_analysis_post_end = time.perf_counter()
    def mark_learning_start(self): self.t_learning_start = time.perf_counter()
    def mark_learning_end(self): self.t_learning_end = time.perf_counter()

    def log_if_needed(self, step_count: int):
        if not self.log_step_progress:
            return

        if step_count == 1 or step_count % self.freq == 0:
            t_total_end = time.perf_counter()
            
            total_ms = (t_total_end - self.t_total_start) * 1000
            decision_ms = (self.t_decision_end - self.t_decision_start) * 1000
            auth_ms = (self.t_auth_end - self.t_auth_start) * 1000
            analysis_pre_ms = (self.t_analysis_pre_end - self.t_analysis_pre_start) * 1000
            guardian_send_ms = (self.t_guardian_send_end - self.t_guardian_send_start) * 1000
            guardian_recv_ms = (self.t_guardian_recv_end - self.t_guardian_recv_start) * 1000
            env_step_ms = (self.t_env_step_end - self.t_env_step_start) * 1000
            analysis_post_ms = (self.t_analysis_post_end - self.t_analysis_post_start) * 1000
            learning_ms = (self.t_learning_end - self.t_learning_start) * 1000
            
            log_message = (
                f"[STEP_TIMER] Total: {total_ms:.2f}ms | "
                f"PPO_Decision: {(decision_ms + auth_ms):.2f}ms | "
                f"Analysis_PreStep: {analysis_pre_ms:.2f}ms | "
                f"Guardian_SendState: {guardian_send_ms:.2f}ms | "
                f"Guardian_RecvSignal: {guardian_recv_ms:.2f}ms | "
                f"Environment_Step: {env_step_ms:.2f}ms | "
                f"Analysis_PostStep: {analysis_post_ms:.2f}ms | "
                f"PPO_Learning: {learning_ms:.2f}ms"
            )
            logging.info(log_message)
