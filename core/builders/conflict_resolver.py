from typing import Dict, Any

class ConflictResolver:
    def resolve(self, 
                current_request: str, 
                working_memory: list,
                device_state: dict,
                summary: dict,
                user_memory: list,
                house_memory: dict,
                automations: list) -> Dict[str, Any]:
        """
        Resolves conflicts between layers based on strict priority:
        Request > Working Memory > Device State > Summary > User Mem > House Mem
        """
        # For Sprint 10, we simply build the decision graph and return the context as-is.
        # In the future, this will explicitly filter out contradictory items.
        decision_graph = {
            "winner": "Current User Request",
            "losers": [],
            "reason": "Default Sprint 10 Strategy: User request wins"
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
