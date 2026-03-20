import logging
from multiprocessing import Queue
from queue import Empty, Full
from typing import Union

class GuardianCommunicator:
    """
    Abstrai o envio de pacotes de estado e leitura de sinais de veto
    do Guardião (Safety Checks da UI).
    """

    def __init__(self, guardian_state_queue: Union[Queue, None], guardian_signal_queue: Union[Queue, None]):
        self.state_queue = guardian_state_queue
        self.signal_queue = guardian_signal_queue

    def send_state(self, current_states_dict: dict, done: bool, mode: str = 'training'):
        if self.state_queue:
            try:
                state_package = (current_states_dict, {}, done, mode)
                self.state_queue.put_nowait(state_package)
            except Full:
                logging.warning("[EpisodeRunner] Fila do Guardião (estado) cheia.")
            except Exception as e:
                logging.error(f"[EpisodeRunner] Erro ao enviar estado para fila do Guardião: {e}")

    def receive_vetos(self) -> dict:
        vetos_recebidos = {}
        if self.signal_queue:
            try:
                while True:
                    veto = self.signal_queue.get_nowait()
                    if 'target_tl' in veto:
                        vetos_recebidos[veto['target_tl']] = veto
            except Empty:
                pass
            except Exception as e:
                logging.error(f"[EpisodeRunner] Erro ao receber sinal da fila do Guardião: {e}")
        return vetos_recebidos
