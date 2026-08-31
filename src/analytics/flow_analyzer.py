import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class FlowAnalyzer:
    """主力籌碼動向分析與市場風險警報偵測器"""

    def analyze_market_alerts(
        self,
        stocks_analysis: List[Dict[str, Any]],
        macro_data: Dict[str, Any],
        adr_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        掃描全市場風險與籌碼異常警報
        返回警報列表: [
            {"level": "warning" | "danger" | "info" | "success", "title": "...", "desc": "...", "stock": "2330"}
        ]
        """
        alerts: List[Dict[str, Any]] = []

        # 1. 宏觀情緒極端警報 (Fear & Greed)
        fg_score = macro_data.get("fear_and_greed", {}).get("score", 50.0)
        if fg_score <= 25.0:
            alerts.append({
                "level": "warning",
                "badge": "宏觀警報",
                "title": f"市場進入「極度恐慌」區間 ({fg_score}分)",
                "desc": "投資人恐慌情緒濃厚，通常伴隨非理性殺盤，中長線價值投資者可留意被錯殺之優質標的分批低接機會。",
                "symbol": "MACRO"
            })
        elif fg_score >= 75.0:
            alerts.append({
                "level": "warning",
                "badge": "風險預警",
                "title": f"市場進入「極度貪婪」區間 ({fg_score}分)",
                "desc": "市場情緒過熱，追高風險急遽上升，嚴防主力逢高獲利了結與突發性獲利了結回檔。",
                "symbol": "MACRO"
            })

        # 2. 10Y 美債殖利率異動
        us10y = macro_data.get("macro", {}).get("us10y", {}).get("value", 0.0)
        us10y_pct = macro_data.get("macro", {}).get("us10y", {}).get("pct_change", 0.0)
        if abs(us10y_pct) >= 2.5 and us10y > 0:
            alerts.append({
                "level": "info",
                "badge": "債市波動",
                "title": f"美債 10 年期殖利率單日劇烈變動 ({us10y_pct:+.2f}%)",
                "desc": f"當前殖利率為 {us10y:.3f}%，殖利率急遽波動易引發高估值科技股本益比重新定價與資金板塊輪動。",
                "symbol": "US10Y"
            })

        # 3. ADR 溢價異常警報
        for adr in adr_data:
            prem = adr.get("premium_pct", 0.0)
            if prem >= 10.0:
                alerts.append({
                    "level": "success",
                    "badge": "ADR 溢價",
                    "title": f"{adr.get('adr_symbol')} 對台股溢價達 +{prem:.2f}%",
                    "desc": f"美股 ADR 買盤強勁，換算台幣現價高達 ${adr.get('adr_parity_twd')}，次日開盤容易帶動 {adr.get('tw_symbol')} 現貨跳空補漲。",
                    "symbol": adr.get("tw_symbol")
                })
            elif prem <= -3.0:
                alerts.append({
                    "level": "warning",
                    "badge": "ADR 折價",
                    "title": f"{adr.get('adr_symbol')} 對台股出現罕見折價 ({prem:.2f}%)",
                    "desc": f"外資在美股 ADR 拋售力道較重，注意台股現貨可能面臨套利壓制回調壓力。",
                    "symbol": adr.get("tw_symbol")
                })

        # 4. 個股籌碼異動警報 (土洋對作、爆量滯漲、投信大買)
        for item in stocks_analysis:
            sym = item.get("symbol", "")
            name = item.get("name", sym)
            inst = item.get("institutional") or {}
            stock_d = item.get("stock_data") or {}
            pct = stock_d.get("pct_change", 0.0)
            vol_ratio = stock_d.get("volume_ratio", 1.0)
            foreign = inst.get("foreign_lots", 0)
            trust = inst.get("trust_lots", 0)

            # 土洋對作警報
            if foreign > 1000 and trust < -500:
                alerts.append({
                    "level": "warning",
                    "badge": "土洋對作",
                    "title": f"{name} ({sym}) 出現外資大買、投信大賣",
                    "desc": f"外資買超 {foreign} 張但投信出貨 {abs(trust)} 張，籌碼對峙恐加劇盤中多空拉鋸與巨震。",
                    "symbol": sym
                })
            elif foreign < -1000 and trust > 500:
                alerts.append({
                    "level": "info",
                    "badge": "投信護盤",
                    "title": f"{name} ({sym}) 外資調節，投信強勢承接",
                    "desc": f"外資賣超 {abs(foreign)} 張，但本土投信積極加碼 {trust} 張，展現法人認養企圖心。",
                    "symbol": sym
                })

            # 爆量滯漲警報
            if vol_ratio > 2.0 and abs(pct) < 0.8:
                alerts.append({
                    "level": "warning",
                    "badge": "爆量滯漲",
                    "title": f"{name} ({sym}) 爆出 {vol_ratio:.1f} 倍大量但股價停滯",
                    "desc": f"成交量暴增但股價僅變動 {pct:+.2f}%，顯示高檔換手頻繁或主力暗中派發籌碼，宜提高警覺。",
                    "symbol": sym
                })

            # 均線破線下殺警報
            score_info = item.get("score_info", {})
            if score_info.get("score", 50) <= 25:
                alerts.append({
                    "level": "danger",
                    "badge": "破線警報",
                    "title": f"{name} ({sym}) 技術與籌碼全面轉弱 (多空評分 {score_info.get('score')} 分)",
                    "desc": f"股價跌破關鍵支撐，量能轉為空方主導，建議切實執行停損或避險策略。",
                    "symbol": sym
                })

        return alerts
