.PHONY: install build test lint run all

install:
	pip install -e ".[dev]"

build:
	cargo build --release --manifest-path engine/Cargo.toml

lint:
	ruff check src tests scripts
	ruff format --check src tests scripts

test: build
	pytest

run: build
	python -m splitfolio run

all: lint test run
