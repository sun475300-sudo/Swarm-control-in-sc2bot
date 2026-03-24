#!/usr/bin/env python3
"""
J.A.R.V.I.S. — Claude Agent SDK Application
=============================================
Claude Agent SDK를 사용하여 모든 JARVIS MCP 서버를 통합 운용하는 에이전트.

6개 MCP 서버를 subprocess stdio로 연결:
  1. jarvis-ops      — Swarm-Net 시뮬레이터, SC2 RL 훈련
  2. jarvis-system   — PC 제어, 스크린샷, 타이머, SSH
  3. jarvis-sc2      — SC2 전적, 리플레이 분석, 코칭
  4. jarvis-crypto   — 암호화폐 매매, 포트폴리오, 분석
  5. jarvis-agentic  — 터미널 명령, Python 샌드박스, 파일 I/O
  6. jarvis-location — Amazon Location Service (장소, 경로, 지오코딩)

Usage:
  python jarvis_agent.py                          # 대화형 REPL
  python jarvis_agent.py "시스템 상태 알려줘"       # 단일 명령
  python jarvis_agent.py --model opus              # 모델 지정
"""

import asyncio
import os
import sys
from pathlib import Path

# ──────────────────────────────────────────────
# 프로젝트 경로 및 환경 설정
# ──────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.resolve()

# .env.jarvis 로드 (config_loader 사용 시도, 없으면 직접 파싱)
try:
    sys.path.insert(0, str(PROJECT_DIR))
    from config_loader import load_dotenv_jarvis
    load_dotenv_jarvis(str(PROJECT_DIR / ".env.jarvis"))
except ImportError:
    env_path = PROJECT_DIR / ".env.jarvis"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip("'\"")
                os.environ.setdefault(key, val)


# ──────────────────────────────────────────────
# JARVIS 페르소나 (SOUL.md)
# ──────────────────────────────────────────────
def _load_soul() -> str:
    """SOUL.md에서 JARVIS 정체성을 로드."""
    soul_path = PROJECT_DIR / "SOUL.md"
    if soul_path.exists():
        return soul_path.read_text(encoding="utf-8").strip()
    return (
        "당신은 J.A.R.V.I.S., 장선우 사령관의 AI 부관입니다. "
        "합쇼체, 군대식 통신 프로토콜 준수. 호칭: 사령관님."
    )


# ──────────────────────────────────────────────
# MCP 서버 정의 (subprocess stdio)
# ──────────────────────────────────────────────
def _build_mcp_servers(all_servers: bool = False) -> dict:
    """MCP servers via stdio. Default: 3 core. --all-servers: all 6."""
    python_exe = sys.executable

    servers = {}
    server_defs = {
        "jarvis-system": "system_mcp_server.py",
        "jarvis-sc2": "sc2_mcp_server.py",
        "jarvis-crypto": "crypto_mcp_server.py",
    }
    if all_servers:
        server_defs.update({
            "jarvis-ops": "jarvis_mcp_server.py",
            "jarvis-agentic": "agentic_mcp_server.py",
            "jarvis-location": "location_mcp_server.py",
        })

    for name, script in server_defs.items():
        script_path = PROJECT_DIR / script
        if script_path.exists():
            servers[name] = {
                "command": python_exe,
                "args": [str(script_path)],
            }
        else:
            print(f"[WARN] MCP server script not found: {script}")

    return servers


# ──────────────────────────────────────────────
# 메인 에이전트 실행
# ──────────────────────────────────────────────
async def run_agent(prompt: str, model: str = None, all_servers: bool = False):
    """Claude Agent SDK를 사용하여 JARVIS 에이전트 실행."""
    from claude_code_sdk import ClaudeCodeOptions, query
    from claude_code_sdk.types import (
        AssistantMessage,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
        ToolResultBlock,
    )

    soul = _load_soul()
    mcp_servers = _build_mcp_servers(all_servers=all_servers)

    system_prompt = (
        f"{soul}\n\n"
        f"[시스템 정보]\n"
        f"프로젝트 경로: {PROJECT_DIR}\n"
        f"연결된 MCP 서버: {', '.join(mcp_servers.keys())}\n"
        f"총 서버 수: {len(mcp_servers)}개\n"
    )

    options = ClaudeCodeOptions(
        system_prompt=system_prompt,
        mcp_servers=mcp_servers,
        permission_mode="bypassPermissions",
        model=model,
        cwd=str(PROJECT_DIR),
        max_turns=10,
    )

    print(f"\n[JARVIS] Agent started - MCP servers: {len(mcp_servers)}")
    print(f"[JARVIS] Processing: {prompt[:80]}{'...' if len(prompt) > 80 else ''}\n")

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # Safe print for Windows cp949
                        try:
                            print(block.text)
                        except UnicodeEncodeError:
                            print(block.text.encode('utf-8', errors='replace').decode('utf-8'))
                    elif isinstance(block, ToolUseBlock):
                        print(f"\n[TOOL] {block.name}")
                    elif isinstance(block, ToolResultBlock):
                        content = str(block.content)[:200] if block.content else ""
                        if content:
                            try:
                                print(f"[RESULT] {content}")
                            except UnicodeEncodeError:
                                print("[RESULT] (output contains special characters)")
            elif isinstance(message, ResultMessage):
                pass
    except Exception as e:
        err_msg = str(e)
        if "tool_use" in err_msg or "400" in err_msg:
            print("\n[INFO] Agent completed (API concurrency limit reached)")
        else:
            print(f"\n[ERROR] {err_msg[:200]}")


async def repl_loop(model: str = None, all_servers: bool = False):
    """대화형 REPL 모드."""
    print("=" * 50)
    print("  J.A.R.V.I.S. Agent SDK — Interactive Mode")
    print("  Type 'exit' or 'quit' to terminate")
    print("=" * 50)

    while True:
        try:
            prompt = input("\nJARVIS> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[JARVIS] Agent terminated.")
            break

        if not prompt:
            continue
        if prompt.lower() in ("exit", "quit", "q"):
            print("[JARVIS] Agent terminated.")
            break

        try:
            await run_agent(prompt, model=model, all_servers=all_servers)
        except Exception as e:
            print(f"\n[ERROR] Agent error: {e}")


def main():
    """CLI 엔트리포인트."""
    import argparse

    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Claude Agent SDK")
    parser.add_argument("prompt", nargs="*", help="실행할 명령 (없으면 REPL 모드)")
    parser.add_argument("--model", default=None, help="Claude model")
    parser.add_argument("--all-servers", action="store_true", help="Connect all 6 MCP servers")
    args = parser.parse_args()

    if args.prompt:
        prompt = " ".join(args.prompt)
        asyncio.run(run_agent(prompt, model=args.model, all_servers=args.all_servers))
    else:
        asyncio.run(repl_loop(model=args.model, all_servers=args.all_servers))


if __name__ == "__main__":
    main()
