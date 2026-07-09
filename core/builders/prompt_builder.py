import json
from typing import Dict, Any

class PromptBuilder:
    def build(self, final_context: Dict[str, Any]) -> str:
        """
        Pure function: Converts the final optimized context dictionary 
        into the JSON string payload expected by OpenClaw.
        """
        import time
        # Ensure time is injected
        if "time" not in final_context:
            final_context["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
        return json.dumps(final_context, ensure_ascii=False)
