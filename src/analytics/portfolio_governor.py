import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class HoldingRecord:
    """單檔投資組合持倉實體 (Zero-NaN 保證)"""
    symbol: str
    company_name: str
    shares: float
    buy_price: float
    buy_date: str
    tier: str = "TIER_2_MOMENTUM"        # "TIER_1_CORE" (👑 特許核心) vs "TIER_2_MOMENTUM" (⚡ 戰術動量)
    thesis: str = "基本面成長與動量突破"
    stop_loss: float = 0.0
    target_price: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    return_pct: float = 0.0
    alert_status: str = "正常持有"
    drift_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PortfolioAuditResult:
    """投資組合資產治理與四大大師論文漂移審計結論"""
    audit_date: str
    total_cost: float
    total_market_value: float
    unrealized_pnl: float
    overall_return_pct: float
    holdings: List[Dict[str, Any]]
    drift_items: List[Dict[str, Any]]
    hard_drift_count: int
    soft_drift_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class PortfolioGovernor:
    """
    深模組：投資組合資產治理與四大大師 (巴菲特/芒格/段永平/李錄) 論文漂移審計引擎
    
    【核心職責】
    1. 持倉狀態機持久化 (`docs/data/portfolio.json`)
    2. 每日盯市 (Mark-to-Market) 損益重估
    3. 四大大師論文漂移審計 (Thesis Drift Audit)：
       - 破線停損 (動量資產強制出場 vs 特許核心分批低接加碼)
       - 月營收放緩失速 (成長論文破壞)
       - 台指期大盤期貨避險扣減
    """

    def __init__(self, portfolio_path: Optional[Path] = None):
        if portfolio_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.portfolio_path = base_dir / "docs" / "data" / "portfolio.json"
        else:
            self.portfolio_path = Path(portfolio_path)
            
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.portfolio_path.exists():
            return {
                "initial_capital": 1000000.0,
                "cash": 1000000.0,
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "holdings": []
            }
        try:
            with open(self.portfolio_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"讀取投資組合資料失敗: {e}，初始化空結構")
            return {
                "initial_capital": 1000000.0,
                "cash": 1000000.0,
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "holdings": []
            }

    def save(self) -> bool:
        try:
            self.portfolio_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.portfolio_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"儲存投資組合失敗: {e}")
            return False

    def add_or_update_holding(
        self,
        symbol: str,
        company_name: str,
        shares: float,
        buy_price: float,
        buy_date: str,
        tier: str = "TIER_2_MOMENTUM",
        thesis: str = "",
        stop_loss: float = 0.0,
        target_price: float = 0.0
    ) -> HoldingRecord:
        """新增或更新單筆持倉"""
        clean_symbol = str(symbol).strip().upper()
        holdings = self.data.setdefault("holdings", [])
        
        target_holding = None
        for item in holdings:
            if str(item.get("symbol", "")).strip().upper() == clean_symbol:
                target_holding = item
                break

        if target_holding:
            target_holding["company_name"] = company_name
            target_holding["shares"] = float(shares)
            target_holding["buy_price"] = float(buy_price)
            target_holding["buy_date"] = buy_date
            target_holding["tier"] = tier
            target_holding["thesis"] = thesis or target_holding.get("thesis", "")
            target_holding["stop_loss"] = float(stop_loss)
            target_holding["target_price"] = float(target_price)
            rec_dict = target_holding
        else:
            new_item = {
                "symbol": clean_symbol,
                "company_name": company_name,
                "shares": float(shares),
                "buy_price": float(buy_price),
                "buy_date": buy_date,
                "tier": tier,
                "thesis": thesis or "量化動能與基本面佈局",
                "stop_loss": float(stop_loss),
                "target_price": float(target_price),
                "current_price": float(buy_price),
                "market_value": round(float(shares) * float(buy_price), 1),
                "unrealized_pnl": 0.0,
                "return_pct": 0.0,
                "alert_status": "正常持有",
                "drift_reasons": []
            }
            holdings.append(new_item)
            rec_dict = new_item

        self.save()
        return HoldingRecord(**rec_dict)

    def remove_holding(self, symbol: str) -> bool:
        """移除指定持倉"""
        clean_symbol = str(symbol).strip().upper()
        holdings = self.data.get("holdings", [])
        original_len = len(holdings)
        self.data["holdings"] = [h for h in holdings if str(h.get("symbol", "")).strip().upper() != clean_symbol]
        if len(self.data["holdings"]) < original_len:
            self.save()
            return True
        return False

    def audit_and_rebalance(
        self,
        analyzed_stocks: List[Dict[str, Any]],
        macro_sentiment: Optional[Dict[str, Any]] = None,
        audit_date: Optional[str] = None
    ) -> PortfolioAuditResult:
        """
        執行全投資組合盯市重估與論文漂移審計 (Thesis Drift Audit)
        """
        now_str = audit_date or datetime.now().strftime("%Y-%m-%d")
        self.data["last_updated"] = now_str
        
        # 建立股票代碼快速索引 (支援 2330 與 2330.TW)
        stock_map: Dict[str, Dict[str, Any]] = {}
        for s in analyzed_stocks:
            sym = str(s.get("symbol", "")).strip().upper()
            stock_map[sym] = s
            if "." in sym:
                stock_map[sym.split(".")[0]] = s

        total_cost = 0.0
        total_market_value = 0.0
        drift_items: List[Dict[str, Any]] = []
        hard_drift_count = 0
        soft_drift_count = 0
        
        # 獲取總經大盤期貨資料
        foreign_net_oi = -10000
        if macro_sentiment:
            tx = macro_sentiment.get("tx_futures", {})
            foreign_net_oi = int(tx.get("foreign_net_oi", -10000) or -10000)

        for item in self.data.get("holdings", []):
            sym = str(item.get("symbol", "")).strip().upper()
            shares = float(item.get("shares", 0.0) or 0.0)
            buy_price = float(item.get("buy_price", 0.0) or 0.0)
            cost = shares * buy_price
            total_cost += cost

            matched = stock_map.get(sym)
            if matched:
                s_data = matched.get("stock_data", {})
                curr_price = float(s_data.get("price", 0.0) or buy_price)
                rev_yoy = float(s_data.get("rev_yoy", 0.0) or 0.0)
                tier = str(matched.get("tier") or item.get("tier", "TIER_2_MOMENTUM"))
            else:
                curr_price = float(item.get("current_price", buy_price) or buy_price)
                rev_yoy = 0.0
                tier = str(item.get("tier", "TIER_2_MOMENTUM"))

            item["current_price"] = curr_price
            m_val = round(shares * curr_price, 1)
            item["market_value"] = m_val
            total_market_value += m_val

            pnl = round(m_val - cost, 1)
            item["unrealized_pnl"] = pnl
            ret_pct = round((pnl / cost) * 100.0, 2) if cost > 0 else 0.0
            item["return_pct"] = ret_pct
            item["tier"] = tier

            # ==========================================
            # 四大大師論文漂移審計 (Thesis Drift Audit)
            # ==========================================
            drift_reasons: List[str] = []
            stop_loss = float(item.get("stop_loss", 0.0) or 0.0)
            
            # 1. 破線停損審查
            if stop_loss > 0 and curr_price < stop_loss:
                if tier == "TIER_1_CORE":
                    # 👑 波克夏特許核心豁免短線停損，啟動金字塔補倉檢驗
                    drift_reasons.append(f"👑 核心資產回測至防守位階 ({curr_price:.1f} < 停損線 {stop_loss:.1f})，啟動金字塔分批加碼評估")
                    soft_drift_count += 1
                else:
                    # ⚡ 戰術動量資產觸發強制 Hard Drift
                    drift_reasons.append(f"🚨 跌破停損防守價 ({curr_price:.1f} < {stop_loss:.1f})，觸發動量出清警戒")
                    hard_drift_count += 1

            # 2. 營收失速審查
            if rev_yoy < -5.0:
                drift_reasons.append(f"⚠️ 最新月營收年減放緩 ({rev_yoy:.1f}%)，成長論文面臨考驗")
                soft_drift_count += 1

            # 3. 外資期貨大盤空單壓盤審查
            if foreign_net_oi < -35000 and tier == "TIER_1_CORE":
                drift_reasons.append(f"⚠️ 外資台指期空單超過 35,000 口，權值核心資產承受期貨結算壓盤")
                soft_drift_count += 1

            item["drift_reasons"] = drift_reasons
            if any("🚨" in r for r in drift_reasons):
                item["alert_status"] = "🚨 嚴重破位"
            elif drift_reasons:
                item["alert_status"] = "⚠️ 論文警示"
            else:
                item["alert_status"] = "✅ 正常持有"

            if drift_reasons:
                drift_items.append({
                    "symbol": sym,
                    "company_name": item.get("company_name", sym),
                    "tier": tier,
                    "return_pct": ret_pct,
                    "reasons": drift_reasons
                })

        overall_pnl = round(total_market_value - total_cost, 1)
        overall_ret = round((overall_pnl / total_cost) * 100.0, 2) if total_cost > 0 else 0.0

        self.save()

        return PortfolioAuditResult(
            audit_date=now_str,
            total_cost=round(total_cost, 1),
            total_market_value=round(total_market_value, 1),
            unrealized_pnl=overall_pnl,
            overall_return_pct=overall_ret,
            holdings=self.data.get("holdings", []),
            drift_items=drift_items,
            hard_drift_count=hard_drift_count,
            soft_drift_count=soft_drift_count
        )
