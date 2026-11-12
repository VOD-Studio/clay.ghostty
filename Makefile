PYTHON ?= python3
CONFIG_HOME ?= $(or $(XDG_CONFIG_HOME),$(HOME)/.config)
GHOSTTY_THEMES ?= $(CONFIG_HOME)/ghostty/themes
THEMES := clay-dark clay-light

.PHONY: test preview images install uninstall
test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tests/check.py

preview:
	@scripts/preview.sh

images: $(foreach theme,$(THEMES),assets/$(theme).svg)

assets/%.svg: themes/% scripts/preview.sh scripts/render.py
	@mkdir -p assets
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) scripts/render.py $< $@

install:
	install -d "$(GHOSTTY_THEMES)"
	install -m 644 $(addprefix themes/,$(THEMES)) "$(GHOSTTY_THEMES)/"

uninstall:
	rm -f $(addprefix "$(GHOSTTY_THEMES)"/,$(THEMES))
