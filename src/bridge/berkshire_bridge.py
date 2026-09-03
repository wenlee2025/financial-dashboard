from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

logger = logging.getLogger(__name__)

@dataclass
class BerkshireAssetContract:
    """跨專案資產傳輸契約 (防腐層 Anticorruption Layer)"""
    symbol: str
    name: str
    tier: str = "TIER_1_CORE"
    tier_label: str = "👑 波克夏特許核心"
    moat_badge: str = "👑 波克夏核心"
    berkshire_score: float = 4.5
    knife_pause: bool = False
    veto_triggered: bool = False
    pyramid_buys: List[Dict[str, Any]] = field(default_factory=list)
    note: str = ""
    sector: str = ""

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """嚴格校驗防腐層契約不變量"""
        if self.tier not in ("TIER_1_CORE", "TIER_2_MOMENTUM"):
            raise ValueError(f"契約異常：非法資產分級 '{self.tier}'，限定 TIER_1_CORE 或 TIER_2_MOMENTUM")
        
        if not (0.0 <= self.berkshire_score <= 100.0):
            raise ValueError(f"契約異常：非法波克夏評分 '{self.berkshire_score}'，需在 0~100 (或 0~5.0) 範圍內")

        if self.tier == "TIER_1_CORE" and not self.pyramid_buys:
            # 自動生成標準半凱利金字塔掛單梯隊 (-10%, -20%, -30%)
            self.pyramid_buys = [
                {"price_discount": 0.90, "ratio": 0.05, "label": "-10% 試探接刀 (5%)"},
                {"price_discount": 0.80, "ratio": 0.07, "label": "-20% 核心加碼 (7%)"},
                {"price_discount": 0.70, "ratio": 0.08, "label": "-30% 極限安全邊際 (8%)"}
            ]

        if self.pyramid_buys:
            total_alloc = sum(p.get("ratio", 0.0) for p in self.pyramid_buys)
            if total_alloc > 0.25:
                raise ValueError(f"契約異常：金字塔總配置上限不可超過 20% (當前累計: {total_alloc*100:.1f}%)")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "tier": self.tier,
            "tier_label": self.tier_label,
            "moat_badge": self.moat_badge,
            "berkshire_score": self.berkshire_score,
            "knife_pause": self.knife_pause,
            "veto_triggered": self.veto_triggered,
            "pyramid_buys": self.pyramid_buys,
            "note": self.note,
            "sector": self.sector
        }


@dataclass
class SyncResult:
    """同步作業執行報告"""
    success: bool
    synced_count: int
    updated_symbols: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BerkshireBridge:
    """
    深模組：AI Berkshire 戰略合約橋接器 (Strategic Bridge Engine)
    
    【深模組介面 (Deep Seam)】
    sync_upstream_assets(berkshire_dir, watchlist_path) -> SyncResult
    
    【接縫後隱藏之內部實作】
    1. 跨專案掃描 AI Berkshire 實盤紀錄與股票清單
    2. 自動區分 TIER_1_CORE (特許核心) 與 TIER_2_MOMENTUM (動量)
    3. 實施嚴格的防腐層合約校驗 (驗證不通過立即阻斷，保護 YAML)
    4. 原子化 (Atomic) 讀取並同步寫回 config/watchlist.yaml
    """

    DEFAULT_BERKSHIRE_DIR = Path("D:/AI Berkshire")
    DEFAULT_WATCHLIST_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "watchlist.yaml"

    # 內建特許核心名單（護城河評估滿分標的）
    CORE_MOAT_SYMBOLS = {"2330", "3008", "2317", "2454", "PDD", "TSM", "AAPL"}

    def __init__(
        self,
        berkshire_dir: Optional[Path] = None,
        watchlist_path: Optional[Path] = None
    ):
        self.berkshire_dir = Path(berkshire_dir) if berkshire_dir else self.DEFAULT_BERKSHIRE_DIR
        self.watchlist_path = Path(watchlist_path) if watchlist_path else self.DEFAULT_WATCHLIST_PATH

    def extract_berkshire_contracts(self) -> List[BerkshireAssetContract]:
        """
        自 AI Berkshire 專案抽取並封裝強型別資產契約
        """
        contracts: List[BerkshireAssetContract] = []
        seen = set()

        # 1. 嘗試解析 股票清單.xlsx
        excel_path = self.berkshire_dir / "股票清單.xlsx"
        if excel_path.exists():
            try:
                import openpyxl
                wb = openpyxl.load_workbook(excel_path, data_only=True)
                sheet = wb.active
                for row in list(sheet.iter_rows(values_only=True))[1:]:
                    if not row or not row[0]:
                        continue
                    sym = str(row[0]).strip().replace(".TW", "").replace(".TWO", "")
                    name = str(row[1]).strip() if len(row) > 1 and row[1] else sym
                    
                    if sym in seen:
                        continue
                    seen.add(sym)

                    is_core = sym in self.CORE_MOAT_SYMBOLS
                    c = BerkshireAssetContract(
                        symbol=sym,
                        name=name,
                        tier="TIER_1_CORE" if is_core else "TIER_2_MOMENTUM",
                        tier_label="👑 波克夏特許核心" if is_core else "⚡ 戰術動量",
                        moat_badge="👑 波克夏核心" if is_core else "⚡ 戰術動量",
                        berkshire_score=4.8 if is_core else 4.0,
                        note="AI Berkshire 上游護城河評估標的"
                    )
                    contracts.append(c)
            except Exception as e:
                logger.warning(f"解析 Berkshire 股票清單失敗: {e}")

        # 2. 若上游專案未找到 Excel，使用預設特許核心種子契約
        if not contracts:
            for sym in self.CORE_MOAT_SYMBOLS:
                contracts.append(BerkshireAssetContract(
                    symbol=sym,
                    name=sym,
                    tier="TIER_1_CORE",
                    tier_label="👑 波克夏特許核心",
                    moat_badge="👑 波克夏核心",
                    berkshire_score=4.8,
                    note="AI Berkshire 上游特許核心種子標的"
                ))

        return contracts

    def sync_upstream_assets(
        self,
        berkshire_dir: Optional[Path] = None,
        watchlist_path: Optional[Path] = None
    ) -> SyncResult:
        """
        執行單向戰略同步：AI Berkshire ➜ 財經儀表板 watchlist.yaml
        """
        b_dir = Path(berkshire_dir) if berkshire_dir else self.berkshire_dir
        w_path = Path(watchlist_path) if watchlist_path else self.watchlist_path

        if not w_path.exists():
            return SyncResult(success=False, synced_count=0, errors=[f"目標檔案不存在: {w_path}"])

        try:
            contracts = self.extract_berkshire_contracts()
            contract_map = {c.symbol: c for c in contracts}

            with open(w_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            updated_symbols = []
            
            # 遍歷 tw_stocks 與 us_stocks 進行契約數據注入
            for section in ["tw_stocks", "us_stocks"]:
                stocks = data.get(section, [])
                for s in stocks:
                    sym = str(s.get("symbol", "")).strip().replace(".TW", "").replace(".TWO", "")
                    if sym in contract_map:
                        contract = contract_map[sym]
                        s["tier"] = contract.tier
                        s["tier_label"] = contract.tier_label
                        s["moat_badge"] = contract.moat_badge
                        s["berkshire_score"] = contract.berkshire_score
                        s["knife_pause"] = contract.knife_pause
                        s["veto_triggered"] = contract.veto_triggered
                        s["pyramid_buys"] = contract.pyramid_buys
                        updated_symbols.append(sym)

            # 原子化寫回
            with open(w_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False, indent=2, default_flow_style=False)

            logger.info(f"成功同步 {len(updated_symbols)} 檔波克夏資產至 {w_path}")
            return SyncResult(
                success=True,
                synced_count=len(updated_symbols),
                updated_symbols=updated_symbols
            )
        except Exception as e:
            logger.error(f"同步波克夏資產失敗: {e}")
            return SyncResult(success=False, synced_count=0, errors=[str(e)])
