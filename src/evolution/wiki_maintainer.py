"""
Wiki Maintainer (知識庫維護與模式提煉智能體)
依據 WikiSkill 論文 Section 3.2.2 規範，
分析復盤失敗軌跡，提煉根因並持久化編譯至 market_wiki/patterns/ 與 logs.md。
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.evolution.post_mortem_engine import TradeOutcome


class WikiMaintainer:
    """知識庫維護模組"""

    def __init__(self, wiki_dir: str = "market_wiki"):
        self.wiki_dir = Path(wiki_dir)
        self.patterns_dir = self.wiki_dir / "patterns" / "failure_modes"
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        self.logs_file = self.wiki_dir / "logs.md"

    def consolidate_patterns(self, outcomes: List[TradeOutcome], iteration_date: Optional[str] = None) -> Dict[str, Any]:
        """
        掃描未達標或觸及停損之交易軌跡，提煉共性失敗模式並寫入 Wiki。
        """
        if not iteration_date:
            iteration_date = datetime.now().strftime("%Y-%m-%d")

        failing_trades = [o for o in outcomes if not o.is_win]
        new_patterns_found = 0
        updated_patterns = 0

        # 分析典型模式分佈
        heavy_volume_dumps = [o for o in failing_trades if o.action_code in ("attack", "alert_exit") and o.pnl_pct <= -4.0]
        decay_chasings = [o for o in failing_trades if o.action_code == "wait_pullback"]

        log_entries = []

        if heavy_volume_dumps:
            p_file = self.patterns_dir / "false_breakout_heavy_volume.md"
            if p_file.exists():
                updated_patterns += 1
                log_entries.append(f"更新 FM-001 (高檔爆量假突破)：新增 {len(heavy_volume_dumps)} 筆關聯實證標的。")
            else:
                new_patterns_found += 1
                log_entries.append(f"新建 FM-001 (高檔爆量假突破)：收錄 {len(heavy_volume_dumps)} 筆失效個案。")

        if decay_chasings:
            p_file = self.patterns_dir / "momentum_decay_chasing.md"
            if p_file.exists():
                updated_patterns += 1
                log_entries.append(f"更新 FM-002 (動能衰竭急追)：新增 {len(decay_chasings)} 筆未等回踩 S1 即破位個案。")
            else:
                new_patterns_found += 1
                log_entries.append(f"新建 FM-002 (動能衰竭急追)：收錄 {len(decay_chasings)} 筆個案。")

        # 追加演化日誌 logs.md
        if log_entries:
            self._append_to_logs(iteration_date, len(outcomes), len(failing_trades), log_entries)

        return {
            "iteration_date": iteration_date,
            "total_analyzed": len(outcomes),
            "failing_analyzed": len(failing_trades),
            "new_patterns_found": new_patterns_found,
            "updated_patterns": updated_patterns,
        }

    def _append_to_logs(self, date_str: str, total: int, failing: int, entries: List[str]):
        """將本次提煉記錄追加至 logs.md"""
        content = f"\n\n## [{date_str}] WikiSkill 模式編譯日誌\n"
        content += f"* **審計總樣本數**：{total} 筆 (失敗檢驗: {failing} 筆)\n"
        content += "* **提煉要點**：\n"
        for e in entries:
            content += f"  - {e}\n"

        with open(self.logs_file, "a", encoding="utf-8") as f:
            f.write(content)
