with open("core/action_executor.py", "r") as f:
    code = f.read()

import re
code = re.sub(
    r'def __init__\([\s\S]*?\):',
    '''def __init__(
        self,
        pipeline: "CommandPipeline",
        state_manager: "StateManager",
        evaluator: "RuleEvaluator",
        event_bus: "EventBus",
        scene_fn=None,
    ):''',
    code,
    count=1
)

code = re.sub(r'self\._pipeline = command_pipeline', 'self._pipeline = pipeline', code)

with open("core/action_executor.py", "w") as f:
    f.write(code)
