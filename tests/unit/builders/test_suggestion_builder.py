import pytest
from core.builders.suggestion_builder import SuggestionBuilder

def test_suggestion_builder_weather():
    builder = SuggestionBuilder()
    house_memory = {"weather": {"condition": "Trời đang mưa to"}}
    device_state = {}
    time_str = "2026-07-09 14:00:00"
    
    suggestions = builder.build(house_memory, device_state, time_str)
    assert len(suggestions) == 1
    assert "đóng toàn bộ cửa sổ" in suggestions[0]

def test_suggestion_builder_time_lights_on():
    builder = SuggestionBuilder()
    house_memory = {}
    device_state = {"light_1": {"state": "on"}}
    time_str = "2026-07-09 23:00:00" # 23:00 is >= 22
    
    suggestions = builder.build(house_memory, device_state, time_str)
    assert len(suggestions) == 1
    assert "tắt bớt đèn" in suggestions[0]

def test_suggestion_builder_time_lights_off():
    builder = SuggestionBuilder()
    house_memory = {}
    device_state = {"light_1": {"state": "off"}}
    time_str = "2026-07-09 23:00:00"
    
    suggestions = builder.build(house_memory, device_state, time_str)
    assert len(suggestions) == 0

def test_suggestion_builder_daytime():
    builder = SuggestionBuilder()
    house_memory = {}
    device_state = {"light_1": {"state": "on"}}
    time_str = "2026-07-09 10:00:00" # Daytime
    
    suggestions = builder.build(house_memory, device_state, time_str)
    assert len(suggestions) == 0
