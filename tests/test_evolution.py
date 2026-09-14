"""
Unit tests for WikiSkill Evolution Subsystem:
- PostMortemEngine
- WikiMaintainer
- ValidationGater
- HistoricalBootstrapper
"""

import pytest
import json
from pathlib import Path
from src.evolution.post_mortem_engine import PostMortemEngine, TradeOutcome, PostMortemReport
from src.evolution.wiki_maintainer import WikiMaintainer
from src.evolution.validation_gater import ValidationGater
from src.evolution.historical_bootstrapper import HistoricalBootstrapper


def test_post_mortem_engine_hit_tp_success():
    """驗證 T+N 日內先觸及 TP 目標價之評判為 Pass/Win"""
    engine = PostMortemEngine(max_holding_days=10)

    rec = {
        "symbol": "2330",
        "name": "台積電",
        "date": "2026-09-01",
        "price_levels": {
            "entry_low": 1000.0,
            "target_price": 1080.0,
            "stop_loss": 960.0,
        },
        "decision_matrix": {
            "action_code": "attack",
            "action_badge": "🚀 順勢進攻",
        },
        "score_info": {
            "rating_code": "strong_bull"
        }
    }

    # T+1 震盪，T+2 盤中衝過 1085 觸及 TP
    future_bars = [
        {"date": "2026-09-02", "open": 1005.0, "high": 1020.0, "low": 995.0, "close": 1015.0},
        {"date": "2026-09-03", "open": 1020.0, "high": 1085.0, "low": 1010.0, "close": 1070.0},
    ]

    outcome = engine.evaluate_single_trade(rec, future_bars)
    assert outcome is not None
    assert outcome.status == "HIT_TP"
    assert outcome.is_win is True
    assert outcome.days_held == 2
    assert outcome.exit_price == 1080.0
    assert outcome.pnl_pct == 8.0


def test_post_mortem_engine_hit_sl_failure():
    """驗證 T+N 日內先跌破 SL 停損價之評判為 Fail/Loss"""
    engine = PostMortemEngine(max_holding_days=10)

    rec = {
        "symbol": "3653",
        "name": "健策",
        "date": "2026-09-01",
        "price_levels": {
            "entry_low": 1100.0,
            "target_price": 1220.0,
            "stop_loss": 1050.0,
        },
        "decision_matrix": {
            "action_code": "wait_pullback",
            "action_badge": "⏳ 耐心等待",
        },
        "score_info": {
            "rating_code": "strong_bull"
        }
    }

    # T+1 急殺跌破 1045 觸及 SL
    future_bars = [
        {"date": "2026-09-02", "open": 1090.0, "high": 1105.0, "low": 1045.0, "close": 1055.0},
    ]

    outcome = engine.evaluate_single_trade(rec, future_bars)
    assert outcome is not None
    assert outcome.status == "HIT_SL"
    assert outcome.is_win is False
    assert outcome.days_held == 1
    assert outcome.exit_price == 1050.0
    assert outcome.pnl_pct < 0
    assert "FM-002" in (outcome.failure_pattern or "")


def test_post_mortem_engine_aggregate_metrics():
    """驗證聚合勝率、盈虧比與分組原型統計"""
    engine = PostMortemEngine()

    outcomes = [
        TradeOutcome("2330", "台積電", "2026-09-01", "attack", "🚀 順勢進攻", "strong_bull", 1000.0, 1080.0, 960.0, "HIT_TP", True, 3, 1080.0, 8.0),
        TradeOutcome("2454", "聯發科", "2026-09-01", "attack", "🚀 順勢進攻", "strong_bull", 1200.0, 1320.0, 1140.0, "HIT_TP", True, 5, 1320.0, 10.0),
        TradeOutcome("3653", "健策", "2026-09-01", "wait_pullback", "⏳ 耐心等待", "strong_bull", 1100.0, 1220.0, 1050.0, "HIT_SL", False, 2, 1050.0, -4.55),
    ]

    rep = engine.aggregate_outcomes(outcomes)
    assert rep.total_evaluations == 3
    assert rep.total_wins == 2
    assert rep.total_losses == 1
    assert rep.overall_win_rate == pytest.approx(66.67, 0.1)
    assert rep.profit_factor > 1.0
    assert "attack" in rep.archetype_stats
    assert rep.archetype_stats["attack"]["win_rate"] == 100.0
    assert rep.archetype_stats["wait_pullback"]["win_rate"] == 0.0


def test_validation_gater_acceptance_and_rollback(tmp_path):
    """驗證驗證閘門機制：得分高於門檻則採納，退化則回滾代碼 (Wiki 永不刪除)"""
    rules_file = tmp_path / "rules.json"
    tracker_file = tmp_path / "skill_impact.md"

    base_rules = {"scoring_weights": {"tech_weight": 0.4}}
    with open(rules_file, "w", encoding="utf-8") as f:
        json.dump(base_rules, f)

    gater = ValidationGater(
        rules_path=str(rules_file),
        impact_tracker_path=str(tracker_file),
        initial_r_best=70.0
    )

    # 1. 提案改善（75.0% >= 70.0%）-> 採納
    accepted, msg = gater.evaluate_and_gate(
        candidate_rules={"scoring_weights": {"tech_weight": 0.45}},
        candidate_val_score=75.0,
        proposal_id="P-TEST-1",
        proposal_note="優化技術面權重",
        eval_date="2026-09-14"
    )
    assert accepted is True
    assert gater.r_best == 75.0
    with open(rules_file, "r", encoding="utf-8") as f:
        saved = json.load(f)
        assert saved["scoring_weights"]["tech_weight"] == 0.45

    # 2. 提案退化（68.0% < 75.0%）-> 安全回滾
    rejected, r_msg = gater.evaluate_and_gate(
        candidate_rules={"scoring_weights": {"tech_weight": 0.60}},
        candidate_val_score=68.0,
        proposal_id="P-TEST-2",
        proposal_note="過激權重測試",
        eval_date="2026-09-14"
    )
    assert rejected is False
    assert "回滾" in r_msg
    assert gater.r_best == 75.0
    # 規則保持前次 0.45，未被覆寫
    with open(rules_file, "r", encoding="utf-8") as f:
        saved = json.load(f)
        assert saved["scoring_weights"]["tech_weight"] == 0.45

    # 確認 tracker_file 正確記錄兩次提案 (Wiki 永不抹除)
    with open(tracker_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "P-TEST-1" in content
        assert "Accepted" in content
        assert "P-TEST-2" in content
        assert "Rejected" in content


def test_wiki_maintainer_pattern_compilation(tmp_path):
    """驗證 WikiMaintainer 提煉模式並追加 logs.md"""
    wiki_dir = tmp_path / "market_wiki"
    maintainer = WikiMaintainer(wiki_dir=str(wiki_dir))

    outcomes = [
        TradeOutcome("3653", "健策", "2026-09-01", "wait_pullback", "⏳ 耐心等待", "strong_bull", 1100.0, 1220.0, 1050.0, "HIT_SL", False, 2, 1050.0, -4.55),
    ]

    res = maintainer.consolidate_patterns(outcomes, iteration_date="2026-09-14")
    assert res["total_analyzed"] == 1
    assert res["failing_analyzed"] == 1
    assert maintainer.logs_file.exists()

    with open(maintainer.logs_file, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "WikiSkill 模式編譯日誌" in log_content
        assert "FM-002" in log_content
