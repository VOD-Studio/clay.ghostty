PYTHON ?= python3

.PHONY: test preview
test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tests/check.py

preview:
	@scripts/preview.sh
