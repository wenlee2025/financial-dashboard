# Financial Dashboard (財經儀表板) Agent Guide

## Quick Commands
- **Run tests**: `pytest` (suite of 49+ unit tests, ~6s).
- **Run pipeline (local test)**: `python main.py --mode full --no-push`.
- **Modes**: `--mode full` (TW+US), `--mode tw_post` (15:30 TW), `--mode us_morning` (06:30 US).

## Navigation Pointers
- **Domain Model**: [CONTEXT.md](file:///d:/WenKuo/專案/財經儀表板/CONTEXT.md) for official terminology, zero-NaN rules, dual-source cross-validation.
- **Architectural Decisions**: [docs/adr/](file:///d:/WenKuo/專案/財經儀表板/docs/adr/) for ADR-0001 through ADR-0013.
- **Pipeline Coordinator**: [src/pipeline.py](file:///d:/WenKuo/專案/財經儀表板/src/pipeline.py) orchestrating market ingestion, analytics, and HTML/JSON generation.
- **Market Ingestion**: [src/data_sources/tw_market.py](file:///d:/WenKuo/專案/財經儀表板/src/data_sources/tw_market.py) (TWSE/TPEx parallel fetch), [src/data_sources/us_market.py](file:///d:/WenKuo/專案/財經儀表板/src/data_sources/us_market.py), [src/data_sources/scanner.py](file:///d:/WenKuo/專案/財經儀表板/src/data_sources/scanner.py).
- **Analytics & Decision Engine**: [src/analytics/market_intelligence.py](file:///d:/WenKuo/專案/財經儀表板/src/analytics/market_intelligence.py) (AI/rules dual engine), [src/analytics/equity_evaluator.py](file:///d:/WenKuo/專案/財經儀表板/src/analytics/equity_evaluator.py).
- **HTML & JSON Generator**: [src/generators/html_dashboard.py](file:///d:/WenKuo/專案/財經儀表板/src/generators/html_dashboard.py) generates `docs/index.html` and `docs/data/*.json`.

## Operational Constraints
- **Zero-NaN Rule**: Any new UI/reporting fields must handle missing/unopened market values gracefully (`"-"` or `"暫無報價"`).
- **Windows Encoding**: Default console is CP950. Avoid raw emoji prints in CLI stdout without utf-8 stream wrapping.
- **Tool & Diff Economy**: Generated HTML/JSON files in `docs/` produce large diffs (+10k lines); always inspect via `git diff --stat`.
- **Git Safety**: Never push with `--force`. Automated updates on GitHub Pages run via `.github/workflows/daily_report.yml`.
