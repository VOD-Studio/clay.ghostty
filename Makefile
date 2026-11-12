PYTHON ?= python3

.PHONY: test
test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tests/check.py
