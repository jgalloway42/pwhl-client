.PHONY: install format lint test build clean check

install:
	pip install -e ".[dev]"

format:
	black --target-version py312 src/ tests/

lint:
	black --check --target-version py312 src/ tests/
	pylint --disable=R,C src/

test:
	pytest tests/

check: format lint test

build:
	python -m build

clean:
	rm -rf dist/ *.egg-info src/*.egg-info __pycache__
