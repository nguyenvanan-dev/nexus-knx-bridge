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
        return len(json.dumps(data, ensure_ascii=False)) // 4

    def optimize(self, resolved_context: Dict[str, Any]) -> Dict[str, Any]:
        budget = self.model_cap.context_window - self.model_cap.reserved_system_tokens - self.model_cap.safety_margin
        
        hard_context_tokens = self._estimate_tokens(resolved_context.get("request")) + \
                              self._estimate_tokens(resolved_context.get("device_state"))
        
        available_budget = budget - hard_context_tokens
        
        drop_order = [
            "automations", 
            "house_memory", 
            "user_memory", 
            "summary", 
            "working_memory"
        ]
        
        for key in drop_order:
            cost = self._estimate_tokens(resolved_context.get(key, {}))
            if available_budget > 0:
                available_budget -= cost
            
            if available_budget < 0:
                if isinstance(resolved_context.get(key), list):
                    resolved_context[key] = []
                elif isinstance(resolved_context.get(key), dict):
                    resolved_context[key] = {}
                else:
                    resolved_context[key] = None
                available_budget += cost
                
        return resolved_context
