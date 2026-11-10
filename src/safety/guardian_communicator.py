# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from multiprocessing import Queue
from queue import Empty, Full
from typing import Union


class GuardianCommunicator:
    """
    Abstracts dispatching state packets and reading veto signals
    from the Guardian (UI Safety Checks).
    """

    def __init__(self, guardian_state_queue: Union[Queue, None], guardian_signal_queue: Union[Queue, None]):
        self.state_queue = guardian_state_queue
        self.signal_queue = guardian_signal_queue

    def send_state(self, current_states_dict: dict, done: bool, mode: str = "training"):
        if self.state_queue:
            try:
                state_package = (current_states_dict, {}, done, mode)
                self.state_queue.put_nowait(state_package)
            except Full:
                logging.warning("[EpisodeRunner] Guardian queue (state) is full.")
            except Exception as e:
                logging.error(f"[EpisodeRunner] Error sending state to Guardian queue: {e}", exc_info=True)

    def receive_vetos(self) -> dict:
        latest_veto_map = {}
        if self.signal_queue:
            try:
                while True:
                    signal = self.signal_queue.get_nowait()
                    if "type" in signal and signal["type"] == "veto_map":
                        latest_veto_map = signal["map"]
            except Empty:
                pass
            except Exception as e:
                logging.error(f"[EpisodeRunner] Erro ao receber sinal da fila do Guardião: {e}", exc_info=True)
        return latest_veto_map
