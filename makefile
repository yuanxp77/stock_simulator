.PHONY: backtest live rebalance advise

FETCH_FLAG := $(if $(CACHE),--no-fetch,)

backtest:
	venv/bin/python -m backtest.main $(FETCH_FLAG)

live:
	venv/bin/python -m live.runner --strategy $(or $(STRATEGY),双均线策略)

rebalance:
	venv/bin/python -m backtest.run_rebalance $(FETCH_FLAG)

advise:
	venv/bin/python tools/rebalance_advisor.py $(ARGS)
