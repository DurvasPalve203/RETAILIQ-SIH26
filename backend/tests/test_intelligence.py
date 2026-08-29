import time
from backend.app.intelligence.depletion_predictor import DepletionPredictor
from backend.app.intelligence.merchandising_insights import MerchandisingInsightsEngine
from backend.app.intelligence.rule_engine import AlertRuleEngine

def test_depletion_prediction():
    predictor = DepletionPredictor()
    now = time.time()
    
    # Simulate declining occupancy points
    for i in range(10):
        t = now - (10 - i) * 60.0
        score = 0.9 - (i * 0.07)
        predictor.record_occupancy_point("zone-test", score, t)

    pred = predictor.predict_eta("zone-test", 0.27, "SKU-TEST")
    assert pred is not None
    assert "eta_minutes" in pred
    assert pred["eta_minutes"] > 0

def test_merchandising_insights():
    engine = MerchandisingInsightsEngine()
    insights = engine.generate_insights()
    assert isinstance(insights, list)
    if insights:
        first = insights[0]
        assert "classification" in first
        assert "action_recommendation" in first

def test_rule_engine():
    rule_engine = AlertRuleEngine()
    stockouts = [{"zone_id": "zone-1", "severity": "high", "ts_start": time.time() - 300}]
    predictions = [{"zone_id": "zone-2", "eta_minutes": 12.0, "confidence": 0.9}]
    
    alerts = rule_engine.process_and_rank_alerts(stockouts, predictions, is_camera_occluded=False)
    assert len(alerts) == 2
    # Highest priority first
    assert alerts[0]["priority_score"] >= alerts[1]["priority_score"]

if __name__ == "__main__":
    test_depletion_prediction()
    test_merchandising_insights()
    test_rule_engine()
    print("Intelligence engine tests passed!")
