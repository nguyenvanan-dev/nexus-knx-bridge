from core.builders.intent_extractor import IntentExtractor

def test_intent_extractor_implicit_dark():
    extractor = IntentExtractor()
    intent = extractor.extract("trong phòng khách tối quá")
    
    assert intent.intent_type == "device_control"
    assert intent.room == "phòng khách"
    assert intent.device_type == "light"
    assert intent.action == "increase"
    assert intent.value == "brightness"

def test_intent_extractor_implicit_hot():
    extractor = IntentExtractor()
    intent = extractor.extract("phòng ngủ dạo này nóng quá")
    
    assert intent.intent_type == "device_control"
    assert intent.room == "phòng ngủ"
    assert intent.device_type == "ac"
    assert intent.action == "decrease"
    assert intent.value == "temperature"

def test_intent_extractor_explicit():
    extractor = IntentExtractor()
    intent = extractor.extract("bật đèn phòng khách")
    
    assert intent.intent_type == "device_control"
    assert intent.room == "phòng khách"
    assert intent.device_type == "light"
    assert intent.action == "on"
