.PHONY: backtest live

backtest:
	venv/bin/python -m backtest.main

live:
	venv/bin/python -m live.runner --strategy $(or $(STRATEGY),双均线策略)
