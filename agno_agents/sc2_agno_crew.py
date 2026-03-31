"""
Phase 438: Agno (formerly phidata) - SC2 AI Agent
Knowledge-augmented agent with persistent memory for SC2 strategy.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.file import FileTools
from agno.knowledge.text import TextKnowledgeBase
from agno.vectordb.chroma import ChromaDb
from agno.storage.agent.sqlite import SqlAgentStorage
from agno.embedder.openai import OpenAIEmbedder
from pydantic import BaseModel
from pathlib import Path


# ── Knowledge base content ────────────────────────────────────────────────────

SC2_STRATEGY_DOCS = [
    """
    Zerg vs Terran (ZvT) Strategy Guide:
    Opening options:
    - Hatch First: 17 Hatch, 17 Pool. Economic opening, safe vs bio.
    - Pool First: 12 Pool. Aggressive, good vs greedy Terrans.
    Key timings: Roach Warren at 3:30, Lair at 5:00 for Roach-Ravager timing.
    Late game: Transition to Hive for Brood Lords or Ultralisk.
    Counter bio: Banelings are essential. Use Lurkers for siege defense.
    """,
    """
    Zerg vs Protoss (ZvP) Strategy Guide:
    Opening: Standard is 17 Hatch, 17 Pool. Watch for 2-gate aggression.
    Midgame: Roach-Hydra-Ravager vs gateway armies.
    Dealing with Colossus: Corruptors are the answer. Transition air.
    Dealing with Skytoss: Hydra-Corruptor or mass Vipers with Abduct.
    Key tech paths: Lair → Infestation Pit for Vipers is almost always correct.
    """,
    """
    Zerg Build Order - Roach-Ravager All-in (ZvP):
    9 - Overlord
    16 - Hatchery at natural
    17 - Spawning Pool
    18 - Extractor x2
    17 - Overlord
    Queen (x2), Zergling speed ASAP
    Roach Warren at 30 supply
    Ravager Morph when 3 Roaches ready
    Attack at 6:00-6:30 with 8-12 Roach-Ravager
    Win condition: Bile + Roach overwhelm before Protoss defensive units
    """,
    """
    General SC2 Macro Principles:
    - Never float minerals: always spend on workers, units, or buildings
    - Supply cap: Never get supply blocked; build Overlords proactively
    - Worker production: Constant drone/SCV/probe production until late game
    - Scouting: Scout at supply 9-13 to identify opponent strategy
    - Creep spread: Zerg queens should spread creep every 30 seconds
    """,
]


# ── Setup knowledge base ──────────────────────────────────────────────────────

def build_knowledge_base(persist_dir: str = "agno_agents/kb") -> TextKnowledgeBase:
    """Build SC2 strategy knowledge base with vector search."""
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    return TextKnowledgeBase(
        path="agno_agents/docs/",
        vector_db=ChromaDb(
            collection="sc2_strategy",
            path=persist_dir,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
    )


# ── Agent storage ─────────────────────────────────────────────────────────────

def build_storage(db_path: str = "agno_agents/sc2_agent.db") -> SqlAgentStorage:
    """Persistent SQLite storage for agent conversation history."""
    return SqlAgentStorage(
        table_name="sc2_agent_sessions",
        db_file=db_path,
    )


# ── SC2 Agno Agent ────────────────────────────────────────────────────────────

def create_sc2_agent(
    use_knowledge: bool = True,
    use_memory: bool = True,
    session_id: str = "sc2_session_001",
) -> Agent:
    """Create an Agno agent with SC2 strategy knowledge and persistent memory."""
    knowledge = build_knowledge_base() if use_knowledge else None
    storage = build_storage() if use_memory else None

    return Agent(
        name="SC2 Strategy Coach",
        model=OpenAIChat(id="gpt-4o-mini"),
        description=(
            "An expert StarCraft 2 strategy coach with deep knowledge of Zerg, "
            "Terran, and Protoss mechanics. Provides tactical advice, build orders, "
            "and game analysis."
        ),
        instructions=[
            "Always reference specific supply counts in build order advice.",
            "When asked about threats, assess urgency on a scale of 1-10.",
            "Provide 2-3 actionable steps for any strategic question.",
            "Remember previous game discussions to track player improvement.",
        ],
        knowledge=knowledge,
        storage=storage,
        session_id=session_id,
        tools=[FileTools()],
        show_tool_calls=True,
        markdown=True,
        add_history_to_messages=True,
        num_history_responses=5,
    )


# ── Convenience functions ─────────────────────────────────────────────────────

def ask_strategy(agent: Agent, question: str, stream: bool = False) -> str:
    """Ask the SC2 agent a strategy question."""
    if stream:
        full_response = []
        for chunk in agent.run(question, stream=True):
            if hasattr(chunk, "content") and chunk.content:
                full_response.append(chunk.content)
                print(chunk.content, end="", flush=True)
        print()
        return "".join(full_response)
    else:
        response = agent.run(question)
        return response.content


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[Agno] Creating SC2 Strategy Agent...")
    print("  Model: gpt-4o-mini")
    print("  Knowledge: SC2 strategy guide (ChromaDB vectors)")
    print("  Memory: SqlAgentStorage (SQLite persistent history)")
    print("  Tools: FileTools")

    sample_questions = [
        "How do I beat Terran bio as Zerg?",
        "What's the best opening build order for ZvP?",
        "My opponent has mass Colossus - what should I build?",
    ]

    print("\n[Sample questions this agent can answer:]")
    for q in sample_questions:
        print(f"  - {q}")

# Phase 438: Agno registered
