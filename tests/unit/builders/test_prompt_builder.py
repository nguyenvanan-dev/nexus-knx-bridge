import pytest
from core.builders.prompt_builder import PromptBuilder

def test_prompt_builder_format():
    builder = PromptBuilder()
    final_context = {
        "working_memory": [{"role": "user", "content": "Bật đèn"}],
        "summary": "User likes warm lights.",
        "user_memory": [{"key": "color", "value": "vàng"}],
        "device_state": {"light_1": {"state": "off"}}
    }
    
    prompt = builder.build(final_context)
    
    assert "Bật đèn" in prompt
    assert "User likes warm lights." in prompt
    assert "vàng" in prompt
    assert "light_1" in prompt
