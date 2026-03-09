.PHONY: backtest live

test:
	venv/bin/python main_backtest.py

live:
	venv/bin/python -m live.runner --strategy $(or $(STRATEGY),双均线策略)
