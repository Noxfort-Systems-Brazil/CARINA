import torch
from typing import TYPE_CHECKING, Tuple, Any

if TYPE_CHECKING:
    from agents.local_agent import LocalAgent

class InferenceEngine:
    """
    Handles the tensor translation and Neural Network interface for LocalAgents.
    """

    def predict(self, agent: 'LocalAgent', state_sequence: list) -> Tuple[int, Any, Any, Any, Any]:
        """
        Converts sequence to tensor, infers action, and returns components for PPO training.
        Returns: (suggested_action_int, action_tensor, log_prob, state_value, entropy)
        """
        state_sequence_tensor = torch.tensor([state_sequence], dtype=torch.float32).to(agent.device)
        
        # 0 = CHANGE PHASE, 1 = KEEP PHASE
        action_tensor, log_prob, state_val, dist_entropy = agent.choose_action(state_sequence_tensor)
        suggested_action = action_tensor.item()
        
        return suggested_action, action_tensor, log_prob, state_val, dist_entropy
