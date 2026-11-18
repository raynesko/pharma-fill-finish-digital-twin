# Thin wrapper over tasks.py (works on Windows via `python tasks.py <task>` when make is absent)
PY ?= python
.PHONY: test lint fix scenarios results app all index
test lint fix scenarios results app all index:
	$(PY) tasks.py $@
