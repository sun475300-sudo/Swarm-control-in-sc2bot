import os

env_path = r"d:\Swarm-contol-in-sc2bot\.env.jarvis"
try:
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    anthropic_key = None
    claude_key_exists = False

    for line in lines:
        if line.strip().startswith("ANTHROPIC_API_KEY="):
            anthropic_key = line.strip().split("=", 1)[1]
        if line.strip().startswith("CLAUDE_API_KEY="):
            claude_key_exists = True

    if anthropic_key and not claude_key_exists:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\n# Auto-copied from ANTHROPIC_API_KEY\nCLAUDE_API_KEY={anthropic_key}\n")
        print("✅ CLAUDE_API_KEY added to .env.jarvis")
    elif claude_key_exists:
        print("ℹ️ CLAUDE_API_KEY already exists")
    else:
        print("⚠️ ANTHROPIC_API_KEY not found in .env.jarvis")

except Exception as e:
    print(f"❌ Error: {e}")
