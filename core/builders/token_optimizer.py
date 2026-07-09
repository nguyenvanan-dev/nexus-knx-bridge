import json
from typing import Dict, Any

class ModelCapabilities:
    context_window: int = 128000
    reserved_system_tokens: int = 2000
    safety_margin: int = 1000

class TokenOptimizer:
    def __init__(self, model_cap: ModelCapabilities = ModelCapabilities()):
        self.model_cap = model_cap

    def _estimate_tokens(self, data: Any) -> int:
        # A very rough approximation (1 token ~ 4 chars in JSON)
        return len(json.dumps(data, ensure_ascii=False)) // 4

    def optimize(self, resolved_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trims context by Priority Drop:
        1. Metadata (not explicitly in resolved_context yet, assume Automations)
        2. Automations
        3. House Memory
        4. User Memory
        5. Summary
        6. Working Memory
        """
        budget = self.model_cap.context_window - self.model_cap.reserved_system_tokens - self.model_cap.safety_margin
        
        # Hard Context is never dropped
        hard_context_tokens = self._estimate_tokens(resolved_context.get("request")) + \
                              self._estimate_tokens(resolved_context.get("device_state"))
        
        available_budget = budget - hard_context_tokens
        
        # In Sprint 10, if we exceed available_budget, we drop whole chunks for simplicity.
        # Future enhancement: finely trim working memory messages or sort user memories.
        
        # Priorities to drop (first item dropped first)
        drop_order = [
            "automations", 
            "house_memory", 
            "user_memory", 
            "summary", 
            "working_memory"
        ]
        
        for key in drop_order:
            if available_budget > 0:
                cost = self._estimate_tokens(resolved_context.get(key, {}))
                available_budget -= cost
            
            if available_budget < 0:
                # We exceeded budget. Drop this key and continue dropping subsequent keys.
                # Actually if available_budget < 0 due to this key, we clear this key.
                if isinstance(resolved_context.get(key), list):
                    resolved_context[key] = []
                elif isinstance(resolved_context.get(key), dict):
                    resolved_context[key] = {}
                else:
                    resolved_context[key] = None
                available_budget += cost # Re-add cost since we dropped it
                
        return resolved_context
