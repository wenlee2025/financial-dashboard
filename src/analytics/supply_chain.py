import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class SupplyChainMapper:
    """美台產業鏈圖譜、上下游角色與板塊分類器"""

    # 產業板塊定義
    SECTORS = {
        "all": {"name": "全部標的", "badge": "🌐 全部"},
        "focus": {"name": "主力強勢焦點", "badge": "🔥 主力焦點"},
        "ai_server": {"name": "AI 伺服器與散熱", "badge": "🤖 AI 伺服器/散熱"},
        "semiconductor": {"name": "半導體與IC設計", "badge": "⚡ 半導體/IC設計"},
        "pcb_substrate": {"name": "PCB與載板", "badge": "📦 PCB與載板"},
        "us_tech": {"name": "美股科技巨頭", "badge": "🇺🇸 美股科技巨頭"}
    }

    # 標的詳細產業鏈角色與關聯美股母鏈
    STOCK_METADATA = {
        # 美股科技巨頭
        "NVDA": {"sector": "us_tech", "role": "全球 AI 運算霸主 (GPU)", "related_us": ["MSFT", "GOOGL"], "chain": "AI 算力核心母鏈"},
        "TSM": {"sector": "us_tech", "role": "全球先進製程晶圓代工龍頭 ADR", "related_us": ["NVDA", "AAPL"], "chain": "先進製程母鏈"},
        "AAPL": {"sector": "us_tech", "role": "消費電子與 Apple Silicon 龍頭", "related_us": ["TSM"], "chain": "蘋果供應鏈母鏈"},
        "MSFT": {"sector": "us_tech", "role": "全球雲端 CSP 與 AI 軟體龍頭", "related_us": ["NVDA"], "chain": "雲端 AI 資本支出母鏈"},
        "PLTR": {"sector": "us_tech", "role": "企業級 AI 數據分析與國防智能", "related_us": ["MSFT"], "chain": "AI 應用生態鏈"},
        "META": {"sector": "us_tech", "role": "社群平台與開源 AI 運算中心", "related_us": ["NVDA"], "chain": "客製化 ASIC 晶片母鏈"},
        "AVGO": {"sector": "us_tech", "role": "網通高階晶片與客製化 ASIC 霸主", "related_us": ["GOOGL", "META"], "chain": "客製化晶片母鏈"},
        "GOOGL": {"sector": "us_tech", "role": "搜尋與 TPU 雲端架構巨頭", "related_us": ["AVGO"], "chain": "自研 TPU 算力母鏈"},
        "AMD": {"sector": "us_tech", "role": "資料中心 CPU/GPU 雙核心架構", "related_us": ["TSM"], "chain": "開放算力生態鏈"},

        # 台股：半導體與 IC 設計 / 先進封裝
        "2330": {"sector": "semiconductor", "role": "全球先進製程/CoWoS 代工龍頭", "related_us": ["NVDA", "AAPL"], "chain": "台積電 CoWoS 生態圈"},
        "2454": {"sector": "semiconductor", "role": "手機旗艦 AP 與 AI ASIC 晶片", "related_us": ["NVDA"], "chain": "邊緣 AI 與晶片設計鏈"},
        "2303": {"sector": "semiconductor", "role": "成熟製程晶圓代工與特殊工藝", "related_us": ["TSM"], "chain": "晶圓代工供應鏈"},
        "3711": {"sector": "semiconductor", "role": "全球半導體封裝測試龍頭", "related_us": ["TSM", "NVDA"], "chain": "先進封裝測試鏈"},
        "2449": {"sector": "semiconductor", "role": "高階 AI 晶片測試大廠", "related_us": ["NVDA", "2330"], "chain": "AI 晶片最終測試鏈"},
        "6239": {"sector": "semiconductor", "role": "記憶體與車用晶片封測主力", "related_us": ["NVDA"], "chain": "記憶體封測鏈"},
        "3034": {"sector": "semiconductor", "role": "驅動 IC 與高階影像處理晶片", "related_us": ["AAPL"], "chain": "面板驅動與 ASIC 鏈"},
        "2379": {"sector": "semiconductor", "role": "網通晶片與音訊 Codec 龍頭", "related_us": ["AVGO"], "chain": "網通與電腦周邊鏈"},
        "5274": {"sector": "semiconductor", "role": "伺服器遠端管理晶片 (BMC) 龍頭", "related_us": ["NVDA", "MSFT"], "chain": "AI 伺服器主板控制核心"},
        "6415": {"sector": "semiconductor", "role": "電源管理 IC 與高壓快充技術", "related_us": ["NVDA"], "chain": "電源管理與類比晶片鏈"},
        "6515": {"sector": "semiconductor", "role": "高頻高速測試座與探針卡 (Socket)", "related_us": ["NVDA", "TSM"], "chain": "先進晶片測試治具鏈"},
        "6223": {"sector": "semiconductor", "role": "探針卡主力供應商", "related_us": ["TSM", "2330"], "chain": "晶圓探針卡測試鏈"},
        "7769": {"sector": "semiconductor", "role": "先進封裝測試分選機設備", "related_us": ["TSM", "2330"], "chain": "半導體先進設備鏈"},
        "2360": {"sector": "semiconductor", "role": "半導體量測與光學檢測設備", "related_us": ["TSM"], "chain": "半導體量測設備鏈"},
        "3035": {"sector": "semiconductor", "role": "矽智財 (IP) 與 ASIC 委託設計", "related_us": ["NVDA", "TSM"], "chain": "客製化晶片 IP 鏈"},
        "3443": {"sector": "semiconductor", "role": "客製化晶片 ASIC 設計服務", "related_us": ["MSFT", "META"], "chain": "CSP 自研晶片委託鏈"},
        "2455": {"sector": "semiconductor", "role": "砷化鎵磊晶片與光通訊元件", "related_us": ["AVGO"], "chain": "PA 與光通訊磊晶鏈"},
        "1785": {"sector": "semiconductor", "role": "半導體貴金屬靶材與回收", "related_us": ["TSM"], "chain": "半導體前段特用材料鏈"},

        # 台股：AI 伺服器與散熱 / 機構件
        "2317": {"sector": "ai_server", "role": "全球最大電子代工與 GB200 機櫃組裝", "related_us": ["NVDA", "AAPL"], "chain": "NVDA GB200 機櫃總裝鏈"},
        "2382": {"sector": "ai_server", "role": "AI 伺服器一線 ODM 大廠", "related_us": ["NVDA", "MSFT", "GOOGL"], "chain": "CSP 伺服器系統核心代工"},
        "6669": {"sector": "ai_server", "role": "白牌雲端 AI 伺服器整機直供", "related_us": ["MSFT", "META"], "chain": "Tier-1 CSP AI 機櫃鏈"},
        "2324": {"sector": "ai_server", "role": "筆電與伺服器專業代工製造", "related_us": ["AAPL", "MSFT"], "chain": "電子代工與車用供應鏈"},
        "2308": {"sector": "ai_server", "role": "全球電源供應器與散熱水冷方案龍頭", "related_us": ["NVDA", "MSFT"], "chain": "AI 機櫃電源與液冷解方鏈"},
        "2059": {"sector": "ai_server", "role": "高階伺服器導軌機構件獨家主力", "related_us": ["NVDA", "2382"], "chain": "AI 伺服器重型滑軌鏈"},
        "3017": {"sector": "ai_server", "role": "散熱 3D VC 與水冷板 (Cold Plate) 龍頭", "related_us": ["NVDA", "MSFT"], "chain": "AI 伺服器液冷散熱模組鏈"},
        "3653": {"sector": "ai_server", "role": "均熱片 (Heat Sink) 與晶片扣件主力", "related_us": ["NVDA", "TSM"], "chain": "晶片均熱片特製機構鏈"},
        "3665": {"sector": "ai_server", "role": "高頻高速訊號線與車用/醫療連接線", "related_us": ["NVDA", "TSM"], "chain": "高速傳輸銅纜與連接器鏈"},
        "2376": {"sector": "ai_server", "role": "主機板、顯卡與 AI 伺服器品牌", "related_us": ["NVDA", "AMD"], "chain": "AI 伺服器與邊緣運算鏈"},

        # 台股：PCB、載板與網通
        "2383": {"sector": "pcb_substrate", "role": "高階伺服器銅箔基板 (CCL) 龍頭", "related_us": ["NVDA"], "chain": "M8/M9 高頻高速基板鏈"},
        "6274": {"sector": "pcb_substrate", "role": "極低損耗 CCL 銅箔基板主力", "related_us": ["NVDA"], "chain": "高頻高傳輸 CCL 材料鏈"},
        "6213": {"sector": "pcb_substrate", "role": "高階伺服器多層板 CCL 製造", "related_us": ["NVDA"], "chain": "伺服器 CCL 材料鏈"},
        "3037": {"sector": "pcb_substrate", "role": "ABF 載板與高階 PCB 龍頭", "related_us": ["NVDA", "TSM"], "chain": "AI 晶片 ABF 載板鏈"},
        "3189": {"sector": "pcb_substrate", "role": "高階 IC 載板與記憶體載板主力", "related_us": ["NVDA", "2330"], "chain": "先進封裝載板核心鏈"},
        "4958": {"sector": "pcb_substrate", "role": "全球第一大軟板 (FPC) 與高階載板", "related_us": ["AAPL", "NVDA"], "chain": "蘋果與 AI 多層板鏈"},
        "2313": {"sector": "pcb_substrate", "role": "高階 HDI 板與衛星通訊主板龍頭", "related_us": ["AAPL"], "chain": "衛星通訊與高階 HDI 鏈"},
        "2345": {"sector": "pcb_substrate", "role": "高階交換器 (Switch) 網通設備龍頭", "related_us": ["MSFT", "AVGO"], "chain": "800G 資料中心交換器鏈"},
        "6285": {"sector": "pcb_substrate", "role": "網通車聯網與 Wi-Fi 7 設備大廠", "related_us": ["AVGO"], "chain": "車聯網與企業級網通鏈"},
        "2327": {"sector": "pcb_substrate", "role": "全球被動元件 (MLCC/電阻) 龍頭", "related_us": ["AAPL", "NVDA"], "chain": "車用與工業級被動元件鏈"},
        "2344": {"sector": "pcb_substrate", "role": "記憶體 (NOR Flash / DRAM) 製造", "related_us": ["AAPL"], "chain": "記憶體晶片鏈"},
        "3008": {"sector": "pcb_substrate", "role": "高階光學鏡頭與潛望式鏡頭霸主", "related_us": ["AAPL"], "chain": "手機與車用光學鏡頭鏈"},
    }

    def enrich_stock_metadata(self, stock_item: Dict[str, Any]) -> Dict[str, Any]:
        """為股票項目注入產業鏈角色、所屬板塊與連動母鏈標籤"""
        symbol = str(stock_item.get("symbol", "")).strip().upper()
        meta = self.STOCK_METADATA.get(symbol, {})

        market = stock_item.get("stock_data", {}).get("market", "TW")
        default_sector = "us_tech" if market == "US" else "semiconductor"
        sector_key = meta.get("sector", default_sector)
        sector_info = self.SECTORS.get(sector_key, {"name": "電子零組件", "badge": "電子零組件"})

        role = meta.get("role", "核心供應鏈廠商")
        chain = meta.get("chain", "產業供應鏈")
        related_us = meta.get("related_us", [])

        # 是否為籌碼/多空主力焦點 (評分 >= 70 或 法人大量買超)
        score = stock_item.get("score_info", {}).get("score", 50.0)
        inst = stock_item.get("institutional", {}) or {}
        lots = inst.get("total_lots", 0) or 0
        is_focus = (score >= 70) or (lots >= 1000)

        sector_tags = [sector_key]
        if is_focus:
            sector_tags.append("focus")

        stock_item["supply_chain"] = {
            "sector_key": sector_key,
            "sector_name": sector_info["name"],
            "sector_badge": sector_info["badge"],
            "sector_tags": " ".join(sector_tags),
            "role": role,
            "chain": chain,
            "related_us": related_us,
            "is_focus": is_focus
        }
        return stock_item
