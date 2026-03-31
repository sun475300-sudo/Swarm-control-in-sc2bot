"""
Phase 434: Ollama - Local LLM SC2 Strategy Advisor
Run open-source LLMs locally via Ollama for offline SC2 strategy analysis.
"""

import httpx
import asyncio
import json
from dataclasses import dataclass
from typing import AsyncGenerator, Optional


OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3"
STRATEGY_MODEL = "mistral"


# ── Game state prompt builder ─────────────────────────────────────────────────

@dataclass
class SC2GameContext:
    race: str
    opponent_race: str
    game_time: float
    supply_used: int
    supply_cap: int
    minerals: int
    gas: int
    army_supply: int
    map_name: str = "Unknown"

    def build_strategy_prompt(self) -> str:
        return (
            f"You are an expert StarCraft 2 coach. Analyze this game state and provide "
            f"a concise tactical recommendation (2-3 sentences).\n\n"
            f"Matchup: {self.race} vs {self.opponent_race} on {self.map_name}\n"
            f"Time: {self.game_time:.0f}s | Supply: {self.supply_used}/{self.supply_cap}\n"
            f"Resources: {self.minerals} minerals / {self.gas} gas\n"
            f"Army supply: {self.army_supply}\n\n"
            f"Recommendation:"
        )

    def build_build_order_prompt(self) -> str:
        return (
            f"Give a 5-step build order for {self.race} vs {self.opponent_race} "
            f"in the opening phase. Format each step as: [supply] [action]"
        )


# ── Async Ollama client ───────────────────────────────────────────────────────

class OllamaClient:
    """Async HTTP client for the Ollama local LLM API."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url

    async def list_models(self) -> list[str]:
        """List all models available in the local Ollama instance."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]

    async def generate_stream(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 256,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the Ollama /api/generate endpoint."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9,
            },
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        yield chunk.get("response", "")
                        if chunk.get("done", False):
                            break

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
    ) -> str:
        """Generate a complete response (non-streaming)."""
        chunks = []
        async for token in self.generate_stream(prompt, model=model, temperature=temperature):
            chunks.append(token)
        return "".join(chunks)

    async def chat(
        self,
        messages: list[dict],
        model: str = DEFAULT_MODEL,
    ) -> str:
        """Chat-style generation via /api/chat endpoint."""
        payload = {"model": model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]


# ── SC2-specific advisor ──────────────────────────────────────────────────────

class SC2LocalAdvisor:
    """Local SC2 strategy advisor powered by Ollama."""

    def __init__(self, strategy_model: str = STRATEGY_MODEL):
        self.client = OllamaClient()
        self.model = strategy_model

    async def get_real_time_advice(self, ctx: SC2GameContext) -> AsyncGenerator[str, None]:
        """Stream real-time advice token by token during a live game."""
        prompt = ctx.build_strategy_prompt()
        async for token in self.client.generate_stream(prompt, model=self.model):
            yield token

    async def get_build_order(self, ctx: SC2GameContext) -> str:
        """Get a suggested build order for the given matchup."""
        return await self.client.generate(
            ctx.build_build_order_prompt(),
            model=self.model,
            temperature=0.3,  # Low temp for deterministic build orders
        )

    async def analyze_threat(self, description: str) -> str:
        """Analyze a described threat using chat API."""
        return await self.client.chat(
            messages=[
                {"role": "system", "content": "You are an SC2 threat analysis expert."},
                {"role": "user", "content": f"Threat description: {description}\nAssess and recommend counter:"},
            ],
            model=self.model,
        )


# ── Demo runner ───────────────────────────────────────────────────────────────

async def demo_sc2_ollama():
    """Demo the SC2 local LLM advisor."""
    advisor = SC2LocalAdvisor(strategy_model=STRATEGY_MODEL)
    ctx = SC2GameContext(
        race="Zerg",
        opponent_race="Terran",
        game_time=360.0,
        supply_used=90,
        supply_cap=110,
        minerals=200,
        gas=50,
        army_supply=30,
        map_name="Berlingrad",
    )

    print(f"[Ollama] Using model: {advisor.model}")
    print(f"[Ollama] Prompt:\n{ctx.build_strategy_prompt()}\n")
    print("[Ollama] Streaming response (requires running Ollama instance):")

    try:
        async for token in advisor.get_real_time_advice(ctx):
            print(token, end="", flush=True)
        print()
    except httpx.ConnectError:
        print("[Ollama] Not running locally - start with: ollama serve")


if __name__ == "__main__":
    asyncio.run(demo_sc2_ollama())

# Phase 434: Ollama registered
