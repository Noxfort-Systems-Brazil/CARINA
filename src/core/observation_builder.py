from typing import Dict, List

class ObservationBuilder:
    """
    Constructs the final observation array for the Neural Network.
    Glues together Local State, Neighbor Messages, Strategic (GAT) Vectors, and Overrides.
    """

    def __init__(self, message_size: int, n_observations: int):
        self.message_size = message_size
        self.n_observations = n_observations

    def gather_messages(self, current_states: Dict[str, list], get_green_phases_func) -> Dict[str, List[float]]:
        messages = {}
        for tl_id, local_state in current_states.items():
            if not local_state or not isinstance(local_state, list):
                messages[tl_id] = [0.0] * self.message_size
                continue

            try:
                green_phases_indices = get_green_phases_func(tl_id)

                if green_phases_indices:
                    num_green_phases = len(green_phases_indices)
                    if len(local_state) >= num_green_phases:
                        phase_part = local_state[-num_green_phases:]
                        occupancy_part = local_state[:-num_green_phases]
                        
                        current_phase_one_hot_idx = -1
                        if 1 in phase_part:
                             try:
                                 current_phase_one_hot_idx = phase_part.index(1)
                             except ValueError:
                                 pass 

                        congestion_index = sum(occupancy_part)
                        messages[tl_id] = [float(current_phase_one_hot_idx), float(congestion_index)]

                        if self.message_size > 2:
                            messages[tl_id].extend([0.0] * (self.message_size - 2))
                        messages[tl_id] = messages[tl_id][:self.message_size]
                    else:
                        messages[tl_id] = [0.0] * self.message_size
                else:
                    messages[tl_id] = [0.0] * self.message_size

            except Exception:
                messages[tl_id] = [0.0] * self.message_size

        return messages

    def build_state(self, tl_id: str, local_state: list, messages: dict, neighborhoods: dict, 
                    gat_vector: list, override_state: str, is_manual_mode: bool) -> List[float]:
        
        neighbor_messages = []
        for neighbor_id in neighborhoods.get(tl_id, []):
            message = messages.get(neighbor_id, [0.0] * self.message_size)
            neighbor_messages.extend(message)

        is_alert = 1.0 if override_state == "ALERT" else 0.0
        is_off = 1.0 if override_state == "OFF" else 0.0
        
        if is_manual_mode:
             override_flags = [0.0, 0.0]
        else:
             override_flags = [is_alert, is_off]

        max_local_obs_size = self.n_observations - len(neighbor_messages) - len(gat_vector) - len(override_flags)
        padded_local_state = list(local_state) # Copy to avoid mutating original
        
        if len(padded_local_state) < max_local_obs_size:
            padded_local_state.extend([0.0] * (max_local_obs_size - len(padded_local_state)))
        elif len(padded_local_state) > max_local_obs_size:
            padded_local_state = padded_local_state[:max_local_obs_size]

        augmented_state = padded_local_state + neighbor_messages + gat_vector + override_flags
        
        if len(augmented_state) != self.n_observations:
            diff = self.n_observations - len(augmented_state)
            if diff > 0: augmented_state.extend([0.0] * diff)
            else: augmented_state = augmented_state[:self.n_observations]
            
        return augmented_state
