"""
Post-Mortem Engine (復盤驗證與點位評判引擎)
依據 WikiSkill (arXiv:2608.27454) 與 ADR 0013 規範，
以交易日 T+5 ~ T+20 週期內「先觸及 TP 目標價」或「先跌破 SL 停損價」評判量化推薦之真實勝率。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import math


@dataclass
class TradeOutcome:
    symbol: str
    name: str
    eval_date: str
    action_code: str
    action_badge: str
    rating_code: str
    entry_price: float
    target_price: float
    stop_loss: float
    status: str  # "HIT_TP", "HIT_SL", "TIMEOUT"
    is_win: bool
    days_held: int
    exit_price: float
    pnl_pct: float
    exit_date: Optional[str] = None
    failure_pattern: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "eval_date": self.eval_date,
            "action_code": self.action_code,
            "action_badge": self.action_badge,
            "rating_code": self.rating_code,
            "entry_price": round(self.entry_price, 2),
            "target_price": round(self.target_price, 2),
            "stop_loss": round(self.stop_loss, 2),
            "status": self.status,
            "is_win": self.is_win,
            "days_held": self.days_held,
            "exit_price": round(self.exit_price, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "exit_date": self.exit_date,
            "failure_pattern": self.failure_pattern,
        }


@dataclass
class PostMortemReport:
    total_evaluations: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_timeouts: int = 0
    overall_win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    archetype_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recent_outcomes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self.total_evaluations,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "total_timeouts": self.total_timeouts,
            "overall_win_rate": round(self.overall_win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "avg_win_pct": round(self.avg_win_pct, 2),
            "avg_loss_pct": round(self.avg_loss_pct, 2),
            "archetype_stats": self.archetype_stats,
            "recent_outcomes": self.recent_outcomes[:50],
        }


class PostMortemEngine:
    """復盤評判核心引擎"""

    def __init__(self, max_holding_days: int = 20):
        self.max_holding_days = max_holding_days

    def evaluate_single_trade(
        self,
        recommendation: Dict[str, Any],
        future_bars: List[Dict[str, Any]]
    ) -> Optional[TradeOutcome]:
        """
        評估單筆歷史推薦在後續日 K 線中的觸及結果。
        future_bars 依序為 T+1, T+2, ... 日 K 資料（包含 date, open, high, low, close）。
        """
        symbol = recommendation.get("symbol", "")
        name = recommendation.get("name", "")
        eval_date = recommendation.get("date", "")
        
        # 取得點位資訊
        price_levels = recommendation.get("price_levels", {})
        entry_price = float(price_levels.get("entry_low") or recommendation.get("price") or 0.0)
        tp = float(price_levels.get("target_price") or 0.0)
        sl = float(price_levels.get("stop_loss") or 0.0)
        
        # 若無有效點位，略過評判
        if entry_price <= 0 or tp <= entry_price or sl >= entry_price or sl <= 0:
            return None

        # 決策矩陣標籤
        dm = recommendation.get("decision_matrix") or {}
        action_code = dm.get("action_code", "unknown")
        action_badge = dm.get("action_badge", "未分類")
        score_info = recommendation.get("score_info") or {}
        rating_code = score_info.get("rating_code", "neutral")

        if not future_bars:
            return None

        status = "TIMEOUT"
        is_win = False
        days_held = 0
        exit_price = future_bars[-1].get("close", entry_price)
        exit_date = future_bars[-1].get("date", "")
        failure_pattern = None

        for idx, bar in enumerate(future_bars[:self.max_holding_days], start=1):
            high = float(bar.get("high", 0.0))
            low = float(bar.get("low", 0.0))
            open_p = float(bar.get("open", 0.0))
            bar_date = bar.get("date", "")

            # 雙觸判斷（同日觸及 TP 與 SL，以離 Open 較近者為準，若保守則視為停損）
            if high >= tp and low <= sl:
                if abs(open_p - tp) < abs(open_p - sl):
                    status = "HIT_TP"
                    is_win = True
                    days_held = idx
                    exit_price = tp
                    exit_date = bar_date
                    break
                else:
                    status = "HIT_SL"
                    is_win = False
                    days_held = idx
                    exit_price = sl
                    exit_date = bar_date
                    failure_pattern = "FM-001: 劇烈震盪雙觸洗盤"
                    break

            # 觸及目標價 (Hit TP)
            if high >= tp:
                status = "HIT_TP"
                is_win = True
                days_held = idx
                exit_price = tp
                exit_date = bar_date
                break

            # 跌破停損價 (Hit SL)
            if low <= sl:
                status = "HIT_SL"
                is_win = False
                days_held = idx
                exit_price = sl
                exit_date = bar_date
                # 歸因失敗模式
                if action_code == "wait_pullback":
                    failure_pattern = "FM-002: 動能衰竭未等回踩 S1 破位"
                elif action_code == "attack":
                    failure_pattern = "FM-001: 假突破出貨反轉"
                else:
                    failure_pattern = "FM-003: 總經或流動性破線"
                break
        else:
            # 滿期超時結算
            days_held = min(len(future_bars), self.max_holding_days)
            exit_price = future_bars[days_held - 1].get("close", entry_price)
            exit_date = future_bars[days_held - 1].get("date", "")
            is_win = (exit_price > entry_price)
            status = "TIMEOUT"

        pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0

        return TradeOutcome(
            symbol=symbol,
            name=name,
            eval_date=eval_date,
            action_code=action_code,
            action_badge=action_badge,
            rating_code=rating_code,
            entry_price=entry_price,
            target_price=tp,
            stop_loss=sl,
            status=status,
            is_win=is_win,
            days_held=days_held,
            exit_price=exit_price,
            pnl_pct=pnl_pct,
            exit_date=exit_date,
            failure_pattern=failure_pattern,
        )

    def aggregate_outcomes(self, outcomes: List[TradeOutcome]) -> PostMortemReport:
        """聚合計算整體勝率、盈虧比與 5 大決策原型分組指標"""
        if not outcomes:
            return PostMortemReport()

        total = len(outcomes)
        wins = [o for o in outcomes if o.is_win]
        losses = [o for o in outcomes if not o.is_win]
        timeouts = [o for o in outcomes if o.status == "TIMEOUT"]

        total_wins = len(wins)
        total_losses = len(losses)
        overall_win_rate = (total_wins / total * 100.0) if total > 0 else 0.0

        avg_win_pct = (sum(w.pnl_pct for w in wins) / total_wins) if total_wins > 0 else 0.0
        avg_loss_pct = (sum(abs(l.pnl_pct) for l in losses) / total_losses) if total_losses > 0 else 0.0
        
        gross_profit = sum(w.pnl_pct for w in wins)
        gross_loss = sum(abs(l.pnl_pct) for l in losses)
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 99.0

        # 分組原型統計
        archetypes = ["attack", "lurk_accumulate", "wait_pullback", "defense", "alert_exit"]
        archetype_names = {
            "attack": "🚀 順勢進攻",
            "lurk_accumulate": "☕ 逢低潛伏",
            "wait_pullback": "⏳ 耐心等待",
            "defense": "🛡️ 嚴禁進場",
            "alert_exit": "🚨 警戒撤退",
        }
        
        arch_stats = {}
        for arch in archetypes:
            arch_trades = [o for o in outcomes if o.action_code == arch]
            arch_total = len(arch_trades)
            if arch_total > 0:
                arch_wins = [o for o in arch_trades if o.is_win]
                arch_wr = (len(arch_wins) / arch_total) * 100.0
                arch_avg_pnl = sum(o.pnl_pct for o in arch_trades) / arch_total
                arch_avg_days = sum(o.days_held for o in arch_trades) / arch_total
                arch_stats[arch] = {
                    "name": archetype_names.get(arch, arch),
                    "total": arch_total,
                    "wins": len(arch_wins),
                    "win_rate": round(arch_wr, 1),
                    "avg_pnl_pct": round(arch_avg_pnl, 2),
                    "avg_days": round(arch_avg_days, 1),
                }
            else:
                arch_stats[arch] = {
                    "name": archetype_names.get(arch, arch),
                    "total": 0,
                    "wins": 0,
                    "win_rate": 0.0,
                    "avg_pnl_pct": 0.0,
                    "avg_days": 0.0,
                }

        # 依日期降序排序最近交易
        recent = sorted([o.to_dict() for o in outcomes], key=lambda x: x["eval_date"], reverse=True)

        return PostMortemReport(
            total_evaluations=total,
            total_wins=total_wins,
            total_losses=total_losses,
            total_timeouts=len(timeouts),
            overall_win_rate=overall_win_rate,
            profit_factor=profit_factor,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            archetype_stats=arch_stats,
            recent_outcomes=recent,
        )
