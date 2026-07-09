from core.builders.predictive_automation import PredictiveAutomationBuilder

def test_predictive_automation_triggered():
    builder = PredictiveAutomationBuilder()
    user_memory = {
        "habits": {
            "22:00": {"action": "bật đèn ngủ", "streak": 7}
        }
    }
    time_str = "2026-07-09 22:05:00"
    
    suggestions = builder.build(user_memory, time_str)
    assert len(suggestions) == 1
    assert "bật đèn ngủ" in suggestions[0]
    assert "Automation" in suggestions[0]

def test_predictive_automation_not_enough_streak():
    builder = PredictiveAutomationBuilder()
    user_memory = {
        "habits": {
            "22:00": {"action": "bật đèn ngủ", "streak": 5}
        }
    }
    time_str = "2026-07-09 22:05:00"
    
    suggestions = builder.build(user_memory, time_str)
    assert len(suggestions) == 0

def test_predictive_automation_wrong_time():
    builder = PredictiveAutomationBuilder()
    user_memory = {
        "habits": {
            "22:00": {"action": "bật đèn ngủ", "streak": 7}
        }
    }
    time_str = "2026-07-09 10:05:00"
    
    suggestions = builder.build(user_memory, time_str)
    assert len(suggestions) == 0
