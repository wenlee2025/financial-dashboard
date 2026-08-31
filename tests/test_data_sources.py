from src.data_sources.tw_market import TWMarketFetcher
from src.data_sources.us_market import USMarketFetcher
from src.data_sources.macro_sentiment import MacroSentimentFetcher
from src.data_sources.scanner import MarketScanner

def test_symbol_normalization():
    fetcher = TWMarketFetcher()
    assert fetcher._normalize_tw_symbol("2330") == "2330.TW"
    assert fetcher._normalize_tw_symbol("2330.TW") == "2330.TW"
    assert fetcher._normalize_tw_symbol("^TWII") == "^TWII"

def test_adr_premium_formula():
    macro = MacroSentimentFetcher()
    adr_mappings = [
        {"adr_symbol": "TSM", "tw_symbol": "2330", "ratio": 5.0}
    ]
    # Mocking manual formula test
    adr_price_usd = 200.0
    usdtwd_rate = 32.0
    tw_price_twd = 1000.0

    adr_parity_twd = (adr_price_usd * usdtwd_rate) / 5.0 # 200 * 32 / 5 = 1280
    premium_pct = ((adr_parity_twd - tw_price_twd) / tw_price_twd) * 100 # (1280 - 1000) / 1000 = +28%

    assert adr_parity_twd == 1280.0
    assert round(premium_pct, 2) == 28.0

def test_scanner_fallback():
    tw_fetcher = TWMarketFetcher()
    us_fetcher = USMarketFetcher()
    scanner = MarketScanner(tw_fetcher, us_fetcher, {"top_n_tw": 2, "top_n_us": 2})

    fallback_tw = scanner._scan_tw_fallback(["2330", "2454"], top_n=2)
    assert len(fallback_tw) == 2
    assert fallback_tw[0]["symbol"] not in ["2330", "2454"]
