# Wicked Zerg - Docker Container
# Phase 161: Dockerfile

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wine \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SC2_PATH=/usr/games/starcraft ii
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "bot.py"]
