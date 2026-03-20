from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.guardian_agent import GuardianAgent
    from engine.environment import SumoEnvironment

class SafetyAuditor:
    """
    Applies Neuro-Symbolic vetoes via the Guardian Agent.
    """

    def __init__(self, guardian_agent: 'GuardianAgent'):
        self.guardian = guardian_agent

    def audit(self, suggested_action: int, tl_id: str, augmented_state: list, environment: 'SumoEnvironment') -> tuple:
        """
        Audits a 'CHANGE PHASE' request using the Guardian logic.
        Returns: (final_action, was_vetoed)
        """
        if suggested_action != 0:
            return suggested_action, False

        extractor = environment.state_extractor
        context = {
            'current_phase_duration': extractor.get_phase_duration(tl_id),
            'next_phase_has_flow': extractor.check_flow_on_next_phase(tl_id)
        }
        
        # 0 (VETO/KEEP) or 1 (ALLOW/CHANGE)
        guardian_decision = self.guardian.select_action(augmented_state, context)
        
        if guardian_decision == 0:
            # Overrides to KEEP (1)
            return 1, True
            
        return suggested_action, False
