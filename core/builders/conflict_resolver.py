from typing import Dict, Any, Union

class ConflictResolver:
    def resolve(self, 
                current_request: str, 
                working_memory: Union[list, dict],
                device_state: dict,
                summary: dict,
                user_memory: Union[list, dict],
                house_memory: dict,
                automations: list) -> Dict[str, Any]:
        """
        Resolves conflicts between layers based on strict priority:
        Request > Working Memory > Device State > Summary > User Mem > House Mem
        """
        decision_graph = {
            "winner": "Current User Request",
            "losers": [],
            "reason": "Default Strategy: User request wins"
        }
        
        return {
            "decision_graph": decision_graph,
            "resolved_context": {
                "request": current_request,
                "working_memory": working_memory,
                "device_state": device_state,
                "summary": summary,
                "user_memory": user_memory,
                "house_memory": house_memory,
                "automations": automations
            }
        }
