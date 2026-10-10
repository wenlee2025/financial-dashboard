# Financial Dashboard (財經儀表板) Agent Guide

## Quick Commands
- **Run tests**: `pytest` (suite of 58+ unit tests, ~5s).
- **Run pipeline (local test)**: `python main.py --mode full --no-push`.
- **Modes**: `--mode full` (TW+US), `--mode tw_post` (15:30 TW), `--mode us_morning` (06:30 US).

## Navigation Pointers
- **Domain Model**: [CONTEXT.md](file:///d:/WenKuo/專案/財經儀表板/CONTEXT.md) for official terminology, zero-NaN rules, dual-source cross-validation.
- **Coding Standards**: [CODING_STANDARDS.md](file:///d:/WenKuo/專案/財經儀表板/CODING_STANDARDS.md) for anti-hallucination, position limits, and deep-module rules.
- **Architectural Decisions**: [docs/adr/](file:///d:/WenKuo/專案/財經儀表板/docs/adr/) for ADR-0001 through ADR-0015 (ADR-0014 Deliberation & Radar, ADR-0015 Mobile-First iPhone 16 Pro).
- **Pipeline Coordinator**: [src/pipeline.py](file:///d:/WenKuo/專案/財經儀表板/src/pipeline.py) orchestrating market ingestion, analytics, and HTML/JSON generation.
- **Market Ingestion**: [src/data_sources/tw_market.py](file:///d:/WenKuo/專案/財經儀表板/src/data_sources/tw_market.py) (TWSE/TPEx parallel fetch), [src/data_sources/us_market.py](file:///d:/WenKuo/專案/財經儀表板/src/data_sources/us_market.py), [src/data_sources/scanner.py](file:///d:/WenKuo/專案/財經儀表板/src/data_sources/scanner.py).
- **Analytics & Decision Engine**: [src/analytics/market_intelligence.py](file:///d:/WenKuo/專案/財經儀表板/src/analytics/market_intelligence.py) (AI/rules dual engine), [src/analytics/equity_evaluator.py](file:///d:/WenKuo/專案/財經儀表板/src/analytics/equity_evaluator.py).
- **Radar Metrics Engine**: [src/analytics/radar_metrics.py](file:///d:/WenKuo/專案/財經儀表板/src/analytics/radar_metrics.py) (6D multi-stock radar metrics, dimension normalization & Zero-NaN data models).
- **Portfolio Risk Governor**: [src/analytics/portfolio_governor.py](file:///d:/WenKuo/專案/財經儀表板/src/analytics/portfolio_governor.py) (portfolio governor state machine, Berkshire 4-master thesis drift audit, allocation guardrails).
- **Deliberation Engine**: [src/analytics/deliberation_engine.py](file:///d:/WenKuo/專案/財經儀表板/src/analytics/deliberation_engine.py) (multi-agent structured debate between fundamental/technical/macro & risk committee veto adjudication).
- **Backtest Simulator**: [src/analytics/backtest_engine.py](file:///d:/WenKuo/專案/財經儀表板/src/analytics/backtest_engine.py) (regime-adaptive walk-forward backtest simulator & MDD/Sharpe/win-rate evaluator).
- **HTML & JSON Generator**: [src/generators/html_dashboard.py](file:///d:/WenKuo/專案/財經儀表板/src/generators/html_dashboard.py) generates `docs/index.html` and `docs/data/*.json`.

## Operational Constraints
- **Zero-NaN Rule**: Any new UI/reporting fields must handle missing/unopened market values gracefully (`"-"` or `"暫無報價"`).
- **Windows Encoding & Shell Gotchas**: Default console is CP950 (avoid raw emoji prints without utf-8 stream wrapping). In pwsh one-liners, avoid unescaped `$` (e.g. `$nan`) which expands to empty strings.
- **Tool & Diff Economy**: Generated HTML/JSON files in `docs/` produce large diffs (+10k lines); always inspect via `git diff --stat`.
- **Git Safety**: Never push with `--force`. Automated updates on GitHub Pages run via `.github/workflows/daily_report.yml`.
