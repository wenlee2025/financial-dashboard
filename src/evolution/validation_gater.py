"""
Validation Gater (走動回測閘門與自動回滾機制)
依據 WikiSkill 論文 Section 3.2.4 規範，
對候選策略進行多體制驗證，勝率/夏普改善則採納並更新最佳門檻 R_best，
退化則立即回滾代碼配置，但 Wiki 知識庫永不回滾。
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime


class ValidationGater:
    """驗證閘門與回滾防護器"""

    def __init__(
        self,
        rules_path: str = "config/rules.json",
        impact_tracker_path: str = "market_wiki/skill_impact.md",
        initial_r_best: float = 70.0
    ):
        self.rules_path = Path(rules_path)
        self.impact_tracker_path = Path(impact_tracker_path)
        self.r_best = initial_r_best

    def evaluate_and_gate(
        self,
        candidate_rules: Dict[str, Any],
        candidate_val_score: float,
        proposal_id: str,
        proposal_note: str,
        eval_date: str = ""
    ) -> Tuple[bool, str]:
        """
        評判候選規則。
        若 candidate_val_score >= r_best 則接受並寫入 rules_path；
        否則拒絕並觸發回滾 (Rollback)。
        """
        if not eval_date:
            eval_date = datetime.now().strftime("%Y-%m-%d")

        is_accepted = candidate_val_score >= self.r_best
        status_label = "**Accepted**" if is_accepted else "**Rejected** (Rollback)"

        if is_accepted:
            self.r_best = candidate_val_score
            # 寫入正式設定
            with open(self.rules_path, "w", encoding="utf-8") as f:
                json.dump(candidate_rules, f, ensure_ascii=False, indent=2)
            msg = f"✅ 提案 {proposal_id} 驗證通過 ({candidate_val_score:.1f}% >= 門檻 {self.r_best:.1f}%)，正式合入！"
        else:
            # 拒絕並保持既有 rules.json 不變 (Rollback)
            msg = f"🛡️ 提案 {proposal_id} 表現退化 ({candidate_val_score:.1f}% < 門檻 {self.r_best:.1f}%)，觸發安全回滾！"

        # 紀錄至 market_wiki/skill_impact.md (Wiki 永不回滾)
        self._record_to_tracker(
            proposal_id=proposal_id,
            proposal_date=eval_date,
            target="config/rules.json",
            score=candidate_val_score,
            r_best=self.r_best,
            status=status_label,
            note=proposal_note
        )

        return is_accepted, msg

    def _record_to_tracker(
        self,
        proposal_id: str,
        proposal_date: str,
        target: str,
        score: float,
        r_best: float,
        status: str,
        note: str
    ):
        """格式化記錄追加至 skill_impact.md"""
        row = f"| **{proposal_id}** | {proposal_date} | `{target}` | {score:.1f}% | {r_best:.1f}% | {status} | {note} |\n"
        try:
            with open(self.impact_tracker_path, "a", encoding="utf-8") as f:
                f.write(row)
        except Exception:
            pass
