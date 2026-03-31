# Phase 563: Makefile Build System
# SC2 Bot build, test, and deployment automation

.PHONY: all install test lint format clean run train deploy docker help
.DEFAULT_GOAL := help

# ─────────────────────────────────────────────
# Variables
# ─────────────────────────────────────────────

PYTHON     := python3
PIP        := $(PYTHON) -m pip
PYTEST     := $(PYTHON) -m pytest
RUFF       := ruff
BLACK      := black
MYPY       := mypy

BOT_NAME   := sc2_zerg_bot
VERSION    := 560.0
SRC_DIR    := .
TEST_DIR   := tests
BUILD_DIR  := build
DIST_DIR   := dist
LOG_DIR    := logs
MODEL_DIR  := models

VENV_DIR   := .venv
VENV_BIN   := $(VENV_DIR)/bin
VENV_PY    := $(VENV_BIN)/python
VENV_PIP   := $(VENV_BIN)/pip

# Colors
BOLD  := \033[1m
GREEN := \033[32m
CYAN  := \033[36m
RESET := \033[0m

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────

$(VENV_DIR)/bin/activate: requirements.txt
	@echo "$(CYAN)Creating virtual environment...$(RESET)"
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements.txt
	touch $@

install: $(VENV_DIR)/bin/activate   ## Install dependencies
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

install-dev: install                  ## Install dev dependencies
	$(VENV_PIP) install pytest pytest-asyncio pytest-cov ruff black mypy

# ─────────────────────────────────────────────
# Code quality
# ─────────────────────────────────────────────

lint:                                  ## Run linter (ruff)
	@echo "$(CYAN)Linting...$(RESET)"
	$(VENV_BIN)/ruff check $(SRC_DIR) --exclude $(VENV_DIR)
	@echo "$(GREEN)✓ Lint passed$(RESET)"

format:                                ## Auto-format (black + ruff)
	@echo "$(CYAN)Formatting...$(RESET)"
	$(VENV_BIN)/black $(SRC_DIR) --exclude $(VENV_DIR)
	$(VENV_BIN)/ruff check $(SRC_DIR) --fix --exclude $(VENV_DIR)
	@echo "$(GREEN)✓ Formatted$(RESET)"

typecheck:                             ## Run mypy type checking
	$(VENV_BIN)/mypy $(SRC_DIR) --ignore-missing-imports

# ─────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────

test:                                  ## Run full test suite
	@echo "$(CYAN)Running tests...$(RESET)"
	PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
	$(VENV_BIN)/pytest $(TEST_DIR) \
		-v \
		--tb=short \
		--cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=html:$(BUILD_DIR)/coverage \
		-p no:warnings
	@echo "$(GREEN)✓ Tests complete$(RESET)"

test-fast:                             ## Run tests (no coverage)
	PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
	$(VENV_BIN)/pytest $(TEST_DIR) -x -q --tb=short

test-unit:                             ## Run unit tests only
	$(VENV_BIN)/pytest $(TEST_DIR) -v -m "not integration" --tb=short

test-integration:                      ## Run integration tests only
	$(VENV_BIN)/pytest $(TEST_DIR) -v -m integration --tb=short

# ─────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

build: $(BUILD_DIR) install            ## Build distribution
	@echo "$(CYAN)Building...$(RESET)"
	$(VENV_PY) -m build --outdir $(DIST_DIR)
	@echo "$(GREEN)✓ Built to $(DIST_DIR)$(RESET)"

wheel: install                         ## Build wheel package
	$(VENV_PY) setup.py bdist_wheel --dist-dir $(DIST_DIR)

# ─────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────

train:                                 ## Run RL training pipeline
	@echo "$(CYAN)Starting training...$(RESET)"
	mkdir -p $(MODEL_DIR) $(LOG_DIR)
	$(VENV_PY) ppo_selfplay/train.py \
		--timesteps 100000 \
		--save-path $(MODEL_DIR) \
		--log-dir $(LOG_DIR)

train-quick:                           ## Quick training test (1k steps)
	$(VENV_PY) ppo_selfplay/train.py --timesteps 1000 --save-path /tmp

# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

run:                                   ## Run bot against built-in AI
	$(VENV_PY) main.py --race zerg --difficulty easy

run-ladder:                            ## Run bot on ladder
	$(VENV_PY) main.py --race zerg --ladder

# ─────────────────────────────────────────────
# Docker
# ─────────────────────────────────────────────

docker-build:                          ## Build Docker image
	docker build \
		--build-arg VERSION=$(VERSION) \
		-t $(BOT_NAME):$(VERSION) \
		-t $(BOT_NAME):latest \
		.

docker-run:                            ## Run in Docker
	docker run --rm \
		-v $(PWD)/models:/app/models \
		-v $(PWD)/logs:/app/logs \
		$(BOT_NAME):latest

docker-push:                           ## Push to registry
	docker push $(BOT_NAME):$(VERSION)
	docker push $(BOT_NAME):latest

# ─────────────────────────────────────────────
# Deploy
# ─────────────────────────────────────────────

deploy-staging:                        ## Deploy to staging
	@echo "$(CYAN)Deploying to staging...$(RESET)"
	kubectl apply -f helm_charts/sc2bot/templates/ \
		--namespace staging \
		-l environment=staging
	kubectl rollout status deployment/$(BOT_NAME) -n staging

deploy-prod:                           ## Deploy to production (requires confirm)
	@read -p "Deploy $(BOT_NAME):$(VERSION) to PROD? [y/N] " confirm; \
	[[ "$$confirm" == "y" ]] || (echo "Aborted"; exit 1)
	kubectl apply -f helm_charts/sc2bot/templates/ \
		--namespace production
	kubectl rollout status deployment/$(BOT_NAME) -n production

# ─────────────────────────────────────────────
# Maintenance
# ─────────────────────────────────────────────

clean:                                 ## Clean build artifacts
	rm -rf $(BUILD_DIR) $(DIST_DIR) .pytest_cache __pycache__
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".coverage" -delete
	@echo "$(GREEN)✓ Cleaned$(RESET)"

clean-all: clean                       ## Clean including venv
	rm -rf $(VENV_DIR)

logs-rotate:                           ## Rotate log files
	find $(LOG_DIR) -name "*.log" -size +100M -exec gzip {} \;
	find $(LOG_DIR) -name "*.log.gz" | sort -r | tail -n +11 | xargs rm -f

# ─────────────────────────────────────────────
# CI helpers
# ─────────────────────────────────────────────

ci: install-dev lint typecheck test    ## Full CI pipeline

# ─────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────

help:                                  ## Show this help
	@echo "$(BOLD)Phase 563: Makefile Build System — SC2 Bot$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
