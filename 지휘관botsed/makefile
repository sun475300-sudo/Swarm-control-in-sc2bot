# Wicked Zerg - Battle Simulation Makefile
# Phase 156: Makefile

.PHONY: all build test clean install run

SC2_DIR := /opt/starcraft2
BOT_DIR := /opt/wicked-zerg
PYTHON := python3
PIP := pip3

all: build test

build:
	@echo "Building Wicked Zerg Bot..."
	cd $(BOT_DIR) && $(PYTHON) setup.py build

test:
	@echo "Running tests..."
	cd $(BOT_DIR) && $(PYTHON) -m pytest tests/ -v

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

install:
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

run:
	@echo "Starting bot..."
	$(PYTHON) $(BOT_DIR)/bot.py

deploy:
	@echo "Deploying to server..."
	ansible-playbook -i ansible/inventory.yml ansible/deploy.yml

docker-build:
	docker build -t wicked-zerg:latest .

docker-run:
	docker run -d --name sc2-bot wicked-zerg:latest
